import pytest
import uuid

from pulp_ostree.tests.functional.constants import OSTREE_FIXTURE_URL
from pulpcore.client.pulp_ostree import (
    ApiClient,
    ContentCommitsApi,
    ContentConfigsApi,
    ContentObjectsApi,
    ContentRefsApi,
    ContentSummariesApi,
    DistributionsOstreeApi,
    RepositoriesOstreeApi,
    RemotesOstreeApi,
    RepositoriesOstreeVersionsApi,
)

# Api Bindings fixtures


@pytest.fixture(scope="session")
def ostree_client(_api_client_set, bindings_cfg):
    """Fixture to provide a client to Pulp API"""
    api_client = ApiClient(bindings_cfg)
    _api_client_set.add(api_client)
    yield api_client
    _api_client_set.remove(api_client)


@pytest.fixture(scope="session")
def ostree_content_refs_api_client(ostree_client):
    """Fixture that returns an instance of ContentRefsApi"""
    return ContentRefsApi(ostree_client)


@pytest.fixture(scope="session")
def ostree_content_commits_api_client(ostree_client):
    """Fixture that returns an instance of ContentCommitsApi"""
    return ContentCommitsApi(ostree_client)


@pytest.fixture(scope="session")
def ostree_content_configs_api_client(ostree_client):
    """Fixture that returns an instance of ContentConfigsApi"""
    return ContentConfigsApi(ostree_client)


@pytest.fixture(scope="session")
def ostree_content_objects_api_client(ostree_client):
    """Fixture that returns an instance of ContentObjectsApi"""
    return ContentObjectsApi(ostree_client)


@pytest.fixture(scope="session")
def ostree_content_summaries_api_client(ostree_client):
    """Fixture that returns an instance of ContentSummariesApi"""
    return ContentSummariesApi(ostree_client)


@pytest.fixture(scope="session")
def ostree_repositories_api_client(ostree_client):
    """Fixture that returns an instance of RepositoriesOstreeApi"""
    return RepositoriesOstreeApi(ostree_client)


@pytest.fixture(scope="session")
def ostree_repositories_versions_api_client(ostree_client):
    """Fixture that returns an instance of RepositoriesOstreeVersionsApi"""
    return RepositoriesOstreeVersionsApi(ostree_client)


@pytest.fixture(scope="session")
def ostree_remotes_api_client(ostree_client):
    """Fixture that returns an instance of RemotesOstreeApi"""
    return RemotesOstreeApi(ostree_client)


@pytest.fixture(scope="session")
def ostree_distributions_api_client(ostree_client):
    """Fixture that returns an instance of DistributionsOstreeApi"""
    return DistributionsOstreeApi(ostree_client)


# Factory fixtures


@pytest.fixture(scope="class")
def ostree_repository_factory(ostree_repositories_api_client, gen_object_with_cleanup):
    """A factory to generate an ostree Repository with auto-deletion after the test run."""

    def _ostree_repository_factory(**kwargs):
        data = {"name": str(uuid.uuid4())}
        data.update(kwargs)
        return gen_object_with_cleanup(ostree_repositories_api_client, data)

    return _ostree_repository_factory


@pytest.fixture(scope="class")
def ostree_remote_factory(ostree_remotes_api_client, gen_object_with_cleanup):
    """A factory to generate an ostree Remote with auto-deletion after the test run."""

    def _ostree_remote_factory(*, url=OSTREE_FIXTURE_URL, policy="immediate", **kwargs):
        data = {"url": url, "policy": policy, "name": str(uuid.uuid4())}
        data.update(kwargs)
        return gen_object_with_cleanup(ostree_remotes_api_client, data)

    return _ostree_remote_factory


@pytest.fixture(scope="class")
def ostree_distribution_factory(ostree_distributions_api_client, gen_object_with_cleanup):
    """A factory to generate an ostree Distribution with auto-deletion after the test run."""

    def _ostree_distribution_factory(**body):
        data = {"base_path": str(uuid.uuid4()), "name": str(uuid.uuid4())}
        data.update(body)
        return gen_object_with_cleanup(ostree_distributions_api_client, data)

    return _ostree_distribution_factory


# Utils


@pytest.fixture(scope="class")
def sync_repo_version(
    ostree_repositories_api_client,
    ostree_repositories_versions_api_client,
    ostree_repository_factory,
    ostree_remote_factory,
    monitor_task,
):
    """
    Fixture that syncs a Remote ostree Repository,
    waits until the sync task completes and returns the
    created repository version object.
    """

    def _sync_repo_version(repo=None, remote=None, policy="immediate"):
        if repo is None:
            repo = ostree_repository_factory()
        if remote is None:
            remote = ostree_remote_factory(url=OSTREE_FIXTURE_URL, policy=policy, depth=0)
        result = ostree_repositories_api_client.sync(repo.pulp_href, {"remote": remote.pulp_href})
        monitor_task_result = monitor_task(result.task)
        repo = ostree_repositories_api_client.read(repo.pulp_href)
        if len(monitor_task_result.created_resources) > 0:
            repo_version_href = monitor_task_result.created_resources[0]
        else:
            repo_version_href = repo.latest_version_href
        return ostree_repositories_versions_api_client.read(repo_version_href), remote, repo

    return _sync_repo_version
