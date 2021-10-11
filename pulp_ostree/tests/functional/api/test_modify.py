import shutil
import unittest

from urllib.parse import urlparse, urljoin

from requests.exceptions import HTTPError

from pulp_smash import config, api
from pulp_smash.pulp3.bindings import delete_orphans, monitor_task
from pulp_smash.pulp3.utils import get_content, gen_distribution, gen_repo, modify_repo

from pulpcore.client.pulp_ostree import (
    DistributionsOstreeApi,
    OstreeOstreeDistribution,
    ContentCommitsApi,
    ContentConfigsApi,
    ContentObjectsApi,
    ContentRefsApi,
    RepositorySyncURL,
    RemotesOstreeApi,
    RepositoriesOstreeApi,
    RepositoriesOstreeVersionsApi,
)

from pulp_ostree.tests.functional.utils import (
    gen_ostree_client,
    gen_ostree_remote,
    init_local_repo_with_remote,
    validate_repo_integrity,
)
from pulp_ostree.tests.functional.constants import (
    OSTREE_COMMITS_NAME,
    OSTREE_CONFIGS_NAME,
    OSTREE_OBJECTS_NAME,
    OSTREE_REFS_NAME,
    OSTREE_SUMMARIES_NAME,
)


class ModifyRepositoryTestCase(unittest.TestCase):
    """A test case that verifies the repository modifications scenario."""

    @classmethod
    def setUpClass(cls):
        """Initialize class-wide variables."""
        cls.cfg = config.get_config()
        cls.registry_name = urlparse(cls.cfg.get_base_url()).netloc
        cls.client = api.Client(cls.cfg, api.json_handler)

        client_api = gen_ostree_client()
        cls.repositories_api = RepositoriesOstreeApi(client_api)
        cls.versions_api = RepositoriesOstreeVersionsApi(client_api)
        cls.distributions_api = DistributionsOstreeApi(client_api)
        cls.commits_api = ContentCommitsApi(client_api)
        cls.configs_api = ContentConfigsApi(client_api)
        cls.objs_api = ContentObjectsApi(client_api)
        cls.remotes_api = RemotesOstreeApi(client_api)
        cls.refs_api = ContentRefsApi(client_api)

    @classmethod
    def tearDownClass(cls):
        """Clean orphaned content after finishing the tests."""
        delete_orphans()

    def setUp(self):
        """Clean orphaned content before each test and initialize a new repository."""
        delete_orphans()

        self.repo1 = self.repositories_api.create(gen_repo())
        self.addCleanup(self.repositories_api.delete, self.repo1.pulp_href)

        body = gen_ostree_remote(depth=0, policy="immediate")
        self.remote = self.remotes_api.create(body)
        self.addCleanup(self.remotes_api.delete, self.remote.pulp_href)

        repository_sync_data = RepositorySyncURL(remote=self.remote.pulp_href)
        response = self.repositories_api.sync(self.repo1.pulp_href, repository_sync_data)
        repo_version_href = monitor_task(response.task).created_resources[0]

        self.repo_version1 = self.versions_api.read(repo_version_href)

    def test_add_ref_and_commit(self):
        """Copy one commit and one ref from the existing repository."""
        created_refs = self.refs_api.list(repository_version_added=self.repo_version1.pulp_href)
        ref = self.refs_api.read(created_refs.to_dict()["results"][0]["pulp_href"])
        latest_commit = self.commits_api.read(ref.commit)

        configs = self.configs_api.list(repository_version_added=self.repo_version1.pulp_href)
        cfg = self.configs_api.read(configs.to_dict()["results"][0]["pulp_href"])

        content_to_modify = [ref.to_dict(), latest_commit.to_dict(), cfg.to_dict()]

        self.repo2 = self.repositories_api.create(gen_repo())
        self.addCleanup(self.repositories_api.delete, self.repo2.pulp_href)
        modify_repo(self.cfg, self.repo2.to_dict(), add_units=content_to_modify)

        self.repo2 = self.repositories_api.read(self.repo2.pulp_href)
        self.assertEqual(self.repo2.latest_version_href, f"{self.repo2.pulp_href}versions/1/")

        distribution_data = OstreeOstreeDistribution(
            **gen_distribution(repository=self.repo2.pulp_href)
        )
        response = self.distributions_api.create(distribution_data)
        distribution = monitor_task(response.task).created_resources[0]
        self.addCleanup(self.distributions_api.delete, distribution)

        ostree_repo_path = urljoin(
            self.distributions_api.read(distribution).base_url, self.remote.name
        )

        remote_name = init_local_repo_with_remote(self.remote.name, ostree_repo_path)
        self.addCleanup(shutil.rmtree, self.remote.name)
        validate_repo_integrity(
            self.remote.name,
            f"{remote_name}:{ref.name}",
            commits_to_check={latest_commit.checksum},
            depth=0,
        )

    def test_add_refs_commits(self):
        """Copy multiple refs and commits at once."""
        created_refs = self.refs_api.list(repository_version_added=self.repo_version1.pulp_href)
        ref1 = self.refs_api.read(created_refs.to_dict()["results"][0]["pulp_href"])
        latest_commit = self.commits_api.read(ref1.commit)

        ref2 = self.refs_api.read(created_refs.to_dict()["results"][1]["pulp_href"])
        another_ref_commit = self.commits_api.read(ref2.commit)

        configs = self.configs_api.list(repository_version_added=self.repo_version1.pulp_href)
        cfg = self.configs_api.read(configs.to_dict()["results"][0]["pulp_href"])

        content_to_modify = [ref1.to_dict(), another_ref_commit.to_dict(), cfg.to_dict()]

        self.repo2 = self.repositories_api.create(gen_repo())
        self.addCleanup(self.repositories_api.delete, self.repo2.pulp_href)
        modify_repo(self.cfg, self.repo2.to_dict(), add_units=content_to_modify)

        self.repo2 = self.repositories_api.read(self.repo2.pulp_href)
        self.assertEqual(self.repo2.latest_version_href, f"{self.repo2.pulp_href}versions/1/")

        repository_version = self.versions_api.read(self.repo2.latest_version_href)
        added_content = repository_version.content_summary.added
        self.assertEqual(added_content["ostree.refs"]["count"], 1)
        self.assertEqual(added_content["ostree.commit"]["count"], 2)
        self.assertEqual(added_content["ostree.object"]["count"], 3)

        distribution_data = OstreeOstreeDistribution(
            **gen_distribution(repository=self.repo2.pulp_href)
        )
        response = self.distributions_api.create(distribution_data)
        distribution = monitor_task(response.task).created_resources[0]
        self.addCleanup(self.distributions_api.delete, distribution)

        ostree_repo_path = urljoin(
            self.distributions_api.read(distribution).base_url, self.remote.name
        )

        remote_name = init_local_repo_with_remote(self.remote.name, ostree_repo_path)
        self.addCleanup(shutil.rmtree, self.remote.name)
        validate_repo_integrity(
            self.remote.name,
            f"{remote_name}:{ref1.name}",
            commits_to_check={latest_commit.checksum},
            depth=0,
        )

    def test_copy_whole_repository(self):
        """Initialize a new repository from the existing repository."""
        self.repo2 = self.repositories_api.create(gen_repo())
        self.addCleanup(self.repositories_api.delete, self.repo2.pulp_href)

        modify_repo(self.cfg, self.repo2.to_dict(), base_version=self.repo_version1.pulp_href)

        self.repo2 = self.repositories_api.read(self.repo2.pulp_href)
        self.assertEqual(self.repo2.latest_version_href, f"{self.repo2.pulp_href}versions/1/")

        self.repo1 = self.repositories_api.read(self.repo1.pulp_href)
        repo1_content = normalize_content(get_content(self.repo1.to_dict()))
        repo2_content = normalize_content(get_content(self.repo2.to_dict()))

        self.assertEqual(repo1_content, repo2_content, repo2_content)

    def test_remove_ref_and_commit(self):
        """Remove one ref and one commit at once."""
        created_refs = self.refs_api.list(repository_version_added=self.repo_version1.pulp_href)
        ref = self.refs_api.read(created_refs.to_dict()["results"][0]["pulp_href"])
        latest_commit = self.commits_api.read(ref.commit)

        second_ref = self.refs_api.read(created_refs.to_dict()["results"][1]["pulp_href"])
        second_commit = self.commits_api.read(second_ref.commit)

        content_to_modify = [ref.to_dict(), latest_commit.to_dict()]

        modify_repo(self.cfg, self.repo1.to_dict(), remove_units=content_to_modify)

        self.repo1 = self.repositories_api.read(self.repo1.pulp_href)
        self.assertEqual(self.repo1.latest_version_href, f"{self.repo1.pulp_href}versions/2/")

        repository_version = self.versions_api.read(self.repo1.latest_version_href)
        removed_content = repository_version.content_summary.removed

        self.assertEqual(removed_content["ostree.refs"]["count"], 1)
        self.assertEqual(removed_content["ostree.commit"]["count"], 1)
        # the objects are referenced by a different commit; so, they should not be removed
        if "ostree.object" in removed_content:
            self.fail("The created repository version should not contain ostree objects.")

        removed_refs = self.refs_api.list(repository_version_removed=self.repo1.latest_version_href)
        removed_ref = self.refs_api.read(removed_refs.to_dict()["results"][0]["pulp_href"])
        self.assertEqual(ref, removed_ref)

        removed_commits = self.commits_api.list(
            repository_version_removed=self.repo1.latest_version_href
        )
        removed_commit = self.commits_api.read(removed_commits.to_dict()["results"][0]["pulp_href"])
        self.assertEqual(latest_commit, removed_commit)

        # now, remove the second commit and check whether the referenced objects were removed too
        modify_repo(self.cfg, self.repo1.to_dict(), remove_units=[second_commit.to_dict()])

        self.repo1 = self.repositories_api.read(self.repo1.pulp_href)
        self.assertEqual(self.repo1.latest_version_href, f"{self.repo1.pulp_href}versions/3/")

        repository_version = self.versions_api.read(self.repo1.latest_version_href)
        removed_content = repository_version.content_summary.removed
        self.assertEqual(removed_content["ostree.commit"]["count"], 1)
        self.assertEqual(removed_content["ostree.object"]["count"], 3)

    def test_add_remove_obj(self):
        """Try to modify an object (e.g., dirtree, dirmeta, ...) in the existing repository."""
        created_objs = self.objs_api.list(repository_version_added=self.repo_version1.pulp_href)
        obj = created_objs.to_dict()["results"][0]

        with self.assertRaises(HTTPError):
            modify_repo(self.cfg, self.repo1.to_dict(), add_units=[obj])

        with self.assertRaises(HTTPError):
            modify_repo(self.cfg, self.repo1.to_dict(), remove_units=[obj])


def normalize_content(repo_content):
    """Make the repository content to be ready for comparison purposes."""
    repo_commits = sorted(
        [remove_created_key(item) for item in repo_content[OSTREE_COMMITS_NAME]],
        key=lambda item: item["pulp_href"],
    )
    repo_objects = sorted(
        [remove_created_key(item) for item in repo_content[OSTREE_OBJECTS_NAME]],
        key=lambda item: item["pulp_href"],
    )
    repo_refs = sorted(
        [remove_created_key(item) for item in repo_content[OSTREE_REFS_NAME]],
        key=lambda item: item["pulp_href"],
    )
    repo_configs = sorted(
        [remove_created_key(item) for item in repo_content[OSTREE_CONFIGS_NAME]],
        key=lambda item: item["pulp_href"],
    )
    repo_summaries = sorted(
        [remove_created_key(item) for item in repo_content[OSTREE_SUMMARIES_NAME]],
        key=lambda item: item["pulp_href"],
    )
    return repo_commits + repo_objects + repo_refs + repo_configs + repo_summaries


def remove_created_key(dic):
    """Remove the key `created` from the passed dictionary."""
    return {k: v for k, v in dic.items() if k != "created"}
