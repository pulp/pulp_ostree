import os
import shutil
import tempfile
import unittest

from pulp_smash.pulp3.bindings import delete_orphans, monitor_task
from pulp_smash.pulp3.utils import gen_repo, gen_distribution

from pulp_ostree.tests.functional.utils import (
    gen_ostree_client,
    gen_ostree_remote,
    init_local_repo_with_remote,
    validate_repo_integrity,
)

from pulpcore.client.pulp_ostree import (
    DistributionsOstreeApi,
    OstreeOstreeDistribution,
    RepositoriesOstreeApi,
    RepositoriesOstreeVersionsApi,
    RepositorySyncURL,
    RemotesOstreeApi,
    ContentRefsApi,
)


class BasicSyncTestCase(unittest.TestCase):
    """A test case that verifies the syncing scenario."""

    @classmethod
    def setUpClass(cls):
        """Initialize class-wide variables."""
        client_api = gen_ostree_client()
        cls.repositories_api = RepositoriesOstreeApi(client_api)
        cls.versions_api = RepositoriesOstreeVersionsApi(client_api)
        cls.remotes_api = RemotesOstreeApi(client_api)
        cls.distributions_api = DistributionsOstreeApi(client_api)
        cls.refs_api = ContentRefsApi(client_api)

        cls.original_dir = os.getcwd()
        cls.tmpdir = tempfile.TemporaryDirectory()
        os.chdir(cls.tmpdir.name)

    @classmethod
    def tearDownClass(cls):
        """Clean orphaned content after finishing the tests."""
        delete_orphans()
        os.chdir(cls.original_dir)
        cls.tmpdir.cleanup()

    def setUp(self):
        """Clean orphaned content before each test."""
        delete_orphans()

    def test_on_demand_sync(self):
        """Test on_demand synchronization."""
        self.sync("on_demand")

    def test_immediate_sync(self):
        """Test immediate synchronization."""
        self.sync("immediate")

    def sync(self, policy):
        """Synchronize content from a remote repository and check validity of a Pulp repository."""
        repo = self.repositories_api.create(gen_repo())
        self.addCleanup(self.repositories_api.delete, repo.pulp_href)

        body = gen_ostree_remote(depth=0, policy=policy)
        remote = self.remotes_api.create(body)
        self.addCleanup(self.remotes_api.delete, remote.pulp_href)

        # 1. synchronize content from the remote
        self.assertEqual(repo.latest_version_href, f"{repo.pulp_href}versions/0/")
        repository_sync_data = RepositorySyncURL(remote=remote.pulp_href)
        response = self.repositories_api.sync(repo.pulp_href, repository_sync_data)
        repo_version = monitor_task(response.task).created_resources[0]

        repository_version = self.versions_api.read(repo_version)
        added_content = repository_version.content_summary.added

        # 2. validate newly added content
        self.assertEqual(added_content["ostree.config"]["count"], 1)
        self.assertEqual(added_content["ostree.refs"]["count"], 2)
        self.assertEqual(added_content["ostree.commit"]["count"], 2)
        self.assertEqual(added_content["ostree.object"]["count"], 3)
        self.assertEqual(added_content["ostree.summary"]["count"], 1)

        # 3. synchronize from the same remote once again
        previous_version_href = repo_version
        repository_sync_data = RepositorySyncURL(remote=remote.pulp_href)
        sync_response = self.repositories_api.sync(repo.pulp_href, repository_sync_data)
        monitor_task(sync_response.task)
        repo = self.repositories_api.read(repo.pulp_href)

        self.assertEqual(previous_version_href, repo.latest_version_href)

        # 4. publish the synced content
        distribution_data = OstreeOstreeDistribution(**gen_distribution(repository=repo.pulp_href))
        response = self.distributions_api.create(distribution_data)
        distribution = monitor_task(response.task).created_resources[0]
        self.addCleanup(self.distributions_api.delete, distribution)

        ostree_repo_path = self.distributions_api.read(distribution).base_url

        # 5. initialize a local OSTree repository and pull the content from Pulp
        remote_name = init_local_repo_with_remote(remote.name, ostree_repo_path)
        self.addCleanup(shutil.rmtree, remote.name)
        validate_repo_integrity(remote.name, f"{remote_name}:rawhide")
        validate_repo_integrity(remote.name, f"{remote_name}:stable")

    def test_filter_rawhide_ref_sync(self):
        """Synchronize content from a remote repository considering only a specific ref."""
        repo = self.repositories_api.create(gen_repo())
        self.addCleanup(self.repositories_api.delete, repo.pulp_href)

        body = gen_ostree_remote(depth=0, include_refs=["rawhide"], exclude_refs=["stable"])
        remote = self.remotes_api.create(body)
        self.addCleanup(self.remotes_api.delete, remote.pulp_href)

        self.assertEqual(remote.include_refs, ["rawhide"])
        self.assertEqual(remote.exclude_refs, ["stable"])

        repository_sync_data = RepositorySyncURL(remote=remote.pulp_href)
        response = self.repositories_api.sync(repo.pulp_href, repository_sync_data)
        repo_version = monitor_task(response.task).created_resources[0]

        refs = self.refs_api.list(repository_version_added=repo_version).results
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].name, "rawhide")

    def test_exclude_all_refs_sync(self):
        """Synchronize content from a remote repository when a user excludes all refs."""
        repo = self.repositories_api.create(gen_repo())
        self.addCleanup(self.repositories_api.delete, repo.pulp_href)

        body = gen_ostree_remote(depth=0, exclude_refs=["*"])
        remote = self.remotes_api.create(body)
        self.addCleanup(self.remotes_api.delete, remote.pulp_href)

        self.assertEqual(remote.include_refs, None)
        self.assertEqual(remote.exclude_refs, ["*"])

        repository_sync_data = RepositorySyncURL(remote=remote.pulp_href)
        response = self.repositories_api.sync(repo.pulp_href, repository_sync_data)
        repo_version = monitor_task(response.task).created_resources[0]

        repository_version = self.versions_api.read(repo_version)
        added_content = repository_version.content_summary.added

        self.assertEqual(added_content["ostree.config"]["count"], 1)
        self.assertEqual(added_content["ostree.summary"]["count"], 1)
        self.assertRaises(KeyError, lambda: added_content["ostree.refs"])
        self.assertRaises(KeyError, lambda: added_content["ostree.commit"])
        self.assertRaises(KeyError, lambda: added_content["ostree.object"])
