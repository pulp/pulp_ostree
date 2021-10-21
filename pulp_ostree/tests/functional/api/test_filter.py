import unittest

from urllib.parse import urlparse

from pulp_smash import config
from pulp_smash.pulp3.bindings import delete_orphans, monitor_task
from pulp_smash.pulp3.utils import gen_repo

from pulp_ostree.tests.functional.utils import (
    gen_ostree_client,
    gen_ostree_remote,
)
from pulp_ostree.tests.functional.utils import set_up_module as setUpModule  # noqa:F401

from pulpcore.client.pulp_ostree import (
    ContentCommitsApi,
    ContentRefsApi,
    RepositoriesOstreeApi,
    RepositoriesOstreeVersionsApi,
    RepositorySyncURL,
    RemotesOstreeApi,
)


class ContentFilterTestCase(unittest.TestCase):
    """A test case that verifies the content filtering."""

    @classmethod
    def setUpClass(cls):
        """Initialize class-wide variables."""
        cfg = config.get_config()
        cls.registry_name = urlparse(cfg.get_base_url()).netloc

        client_api = gen_ostree_client()
        cls.repositories_api = RepositoriesOstreeApi(client_api)
        cls.versions_api = RepositoriesOstreeVersionsApi(client_api)
        cls.remotes_api = RemotesOstreeApi(client_api)

        cls.commits_api = ContentCommitsApi(client_api)
        cls.refs_api = ContentRefsApi(client_api)

    @classmethod
    def tearDownClass(cls):
        """Clean orphaned content after finishing the tests."""
        delete_orphans()

    def setUp(self):
        """Clean orphaned content before each test."""
        delete_orphans()

        self.repo = self.repositories_api.create(gen_repo())
        self.addCleanup(self.repositories_api.delete, self.repo.pulp_href)

        body = gen_ostree_remote(depth=0, policy="immediate")
        remote = self.remotes_api.create(body)
        self.addCleanup(self.remotes_api.delete, remote.pulp_href)

        self.assertEqual(self.repo.latest_version_href, f"{self.repo.pulp_href}versions/0/")
        repository_sync_data = RepositorySyncURL(remote=remote.pulp_href)
        response = self.repositories_api.sync(self.repo.pulp_href, repository_sync_data)
        repo_version = monitor_task(response.task).created_resources[0]

        self.repository_version = self.versions_api.read(repo_version)

    def test_filter_refs(self):
        """Check if refs can be filtered by their names and related commits' checksums."""
        refs_stable = self.refs_api.list(
            repository_version_added=self.repository_version.pulp_href, name="stable"
        ).to_dict()

        self.assertEqual(refs_stable["count"], 1, refs_stable)
        self.assertEqual(refs_stable["results"][0]["name"], "stable", refs_stable)

        commit = self.commits_api.read(refs_stable["results"][0]["commit"])

        refs_commit_checksum = self.refs_api.list(
            repository_version_added=self.repository_version.pulp_href, checksum=commit.checksum
        ).to_dict()

        self.assertEqual(refs_commit_checksum["count"], 1, refs_commit_checksum)
        self.assertEqual(
            refs_commit_checksum["results"][0]["checksum"], commit.checksum, refs_commit_checksum
        )

    def test_filter_commits(self):
        """Check if commits can be filtered by their checksums."""
        refs_rawhide = self.refs_api.list(
            repository_version_added=self.repository_version.pulp_href, name="rawhide"
        ).to_dict()
        ref_rawhide = refs_rawhide["results"][0]

        commits_rawhide = self.commits_api.list(
            repository_version_added=self.repository_version.pulp_href,
            checksum=ref_rawhide["checksum"],
        ).to_dict()
        self.assertEqual(commits_rawhide["count"], 1, commits_rawhide)

        commit_rawhide = commits_rawhide["results"][0]
        self.assertEqual(commit_rawhide["checksum"], ref_rawhide["checksum"], commit_rawhide)
        self.assertEqual(commit_rawhide["pulp_href"], ref_rawhide["commit"], commit_rawhide)
