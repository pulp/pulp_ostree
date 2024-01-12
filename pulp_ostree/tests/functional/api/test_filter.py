import pytest

from pulp_ostree.tests.functional.constants import OSTREE_FIXTURE_URL


@pytest.fixture
def synced_repo(
    ostree_repositories_api_client, ostree_repository_factory, ostree_remote_factory, monitor_task
):
    """
    Fixture that syncs a Remote ostree Repository,
    waits until the sync task completes and returns the
    created repository object.
    """
    repo = ostree_repository_factory()
    remote = ostree_remote_factory(url=OSTREE_FIXTURE_URL, policy="immediate")
    result = ostree_repositories_api_client.sync(repo.pulp_href, {"remote": remote.pulp_href})
    monitor_task(result.task)
    return ostree_repositories_api_client.read(repo.pulp_href)


@pytest.mark.parallel
def test_filter_refs(
    ostree_content_refs_api_client,
    ostree_content_commits_api_client,
    synced_repo,
):
    """Check if refs can be filtered by their names and related commits' checksums."""
    # check by name
    refs_stable = ostree_content_refs_api_client.list(
        repository_version_added=synced_repo.latest_version_href, name="stable"
    ).to_dict()

    assert refs_stable["count"] == 1, refs_stable
    assert refs_stable["results"][0]["name"] == "stable", refs_stable

    # check by commit
    commit = ostree_content_commits_api_client.read(refs_stable["results"][0]["commit"])
    refs_commit_checksum = ostree_content_refs_api_client.list(
        repository_version_added=synced_repo.latest_version_href, checksum=commit.checksum
    ).to_dict()

    assert refs_commit_checksum["count"] == 1, refs_commit_checksum
    assert refs_commit_checksum["results"][0]["checksum"] == commit.checksum, refs_commit_checksum


@pytest.mark.parallel
def test_filter_commits(
    ostree_content_refs_api_client,
    ostree_content_commits_api_client,
    synced_repo,
):
    """Check if commits can be filtered by their checksums."""
    refs_rawhide = ostree_content_refs_api_client.list(
        repository_version_added=synced_repo.latest_version_href, name="rawhide"
    ).to_dict()
    ref_rawhide = refs_rawhide["results"][0]

    commits_rawhide = ostree_content_commits_api_client.list(
        repository_version_added=synced_repo.latest_version_href,
        checksum=ref_rawhide["checksum"],
    ).to_dict()
    assert commits_rawhide["count"] == 1, commits_rawhide

    commit_rawhide = commits_rawhide["results"][0]
    assert commit_rawhide["checksum"] == ref_rawhide["checksum"], commit_rawhide
    assert commit_rawhide["pulp_href"] == ref_rawhide["commit"], commit_rawhide
