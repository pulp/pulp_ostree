"""Tests that publish ostree plugin repositories."""
import unittest
from random import choice

from pulp_smash import config
from pulp_smash.pulp3.bindings import monitor_task
from pulp_smash.pulp3.utils import gen_repo, get_content, get_versions, modify_repo

from pulp_ostree.tests.functional.constants import OSTREE_CONTENT_NAME
from pulp_ostree.tests.functional.utils import (
    gen_ostree_client,
    gen_ostree_remote,
)
from pulp_ostree.tests.functional.utils import set_up_module as setUpModule  # noqa:F401

from pulpcore.client.pulp_ostree import (
    PublicationsOstreeApi,
    RepositoriesOstreeApi,
    RepositorySyncURL,
    RemotesOstreeApi,
    OstreeOstreePublication,
)
from pulpcore.client.pulp_ostree.exceptions import ApiException


# Implement sync and publish support before enabling this test.
@unittest.skip("FIXME: plugin writer action required")
class PublishAnyRepoVersionTestCase(unittest.TestCase):
    """Test whether a particular repository version can be published.

    This test targets the following issues:

    * `Pulp #3324 <https://pulp.plan.io/issues/3324>`_
    * `Pulp Smash #897 <https://github.com/pulp/pulp-smash/issues/897>`_
    """

    def test_all(self):
        """Test whether a particular repository version can be published.

        1. Create a repository with at least 2 repository versions.
        2. Create a publication by supplying the latest ``repository_version``.
        3. Assert that the publication ``repository_version`` attribute points
           to the latest repository version.
        4. Create a publication by supplying the non-latest ``repository_version``.
        5. Assert that the publication ``repository_version`` attribute points
           to the supplied repository version.
        6. Assert that an exception is raised when providing two different
           repository versions to be published at same time.
        """
        cfg = config.get_config()
        client = gen_ostree_client()
        repo_api = RepositoriesOstreeApi(client)
        remote_api = RemotesOstreeApi(client)
        publications = PublicationsOstreeApi(client)

        body = gen_ostree_remote()
        remote = remote_api.create(body)
        self.addCleanup(remote_api.delete, remote.pulp_href)

        repo = repo_api.create(gen_repo())
        self.addCleanup(repo_api.delete, repo.pulp_href)

        repository_sync_data = RepositorySyncURL(remote=remote.pulp_href)
        sync_response = repo_api.sync(repo.pulp_href, repository_sync_data)
        monitor_task(sync_response.task)

        # Step 1
        repo = repo_api.read(repo.pulp_href)
        for ostree_content in get_content(repo.to_dict())[OSTREE_CONTENT_NAME]:
            modify_repo(cfg, repo.to_dict(), add_units=[ostree_content])
        version_hrefs = tuple(ver["pulp_href"] for ver in get_versions(repo.to_dict()))
        non_latest = choice(version_hrefs[:-1])

        # Step 2
        publish_data = OstreeOstreePublication(repository=repo.pulp_href)
        publish_response = publications.create(publish_data)
        created_resources = monitor_task(publish_response.task).created_resources
        publication_href = created_resources[0]
        self.addCleanup(publications.delete, publication_href)
        publication = publications.read(publication_href)

        # Step 3
        self.assertEqual(publication.repository_version, version_hrefs[-1])

        # Step 4
        publish_response = publications.create(publish_data)
        created_resources = monitor_task(publish_response.task).created_resources
        publication_href = created_resources[0]
        publication = publications.read(publication_href)

        # Step 5
        self.assertEqual(publication.repository_version, non_latest)

        # Step 6
        with self.assertRaises(ApiException):
            body = {"repository": repo.pulp_href, "repository_version": non_latest}
            publications.create(body)
