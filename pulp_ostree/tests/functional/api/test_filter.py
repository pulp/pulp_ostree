import pytest


@pytest.mark.parallel
def test_filter_refs(
    ostree_content_refs_api_client,
    ostree_content_commits_api_client,
    sync_repo_version,
):
    """Check if refs can be filtered by their names and related commits' checksums."""
    # check by name
    _, _, repo = sync_repo_version()
    refs_stable = ostree_content_refs_api_client.list(
        repository_version_added=repo.latest_version_href, name="stable"
    )

    assert refs_stable.count == 1
    assert refs_stable.results[0].name == "stable"

    # check by commit
    commit = ostree_content_commits_api_client.read(refs_stable.results[0].commit)
    refs_commit_checksum = ostree_content_refs_api_client.list(
        repository_version_added=repo.latest_version_href, checksum=commit.checksum
    )

    assert refs_commit_checksum.count == 1
    assert refs_commit_checksum.results[0].checksum == commit.checksum


@pytest.mark.parallel
def test_filter_commits(
    ostree_content_refs_api_client,
    ostree_content_commits_api_client,
    sync_repo_version,
):
    """Check if commits can be filtered by their checksums."""
    _, _, repo = sync_repo_version()
    refs_rawhide = ostree_content_refs_api_client.list(
        repository_version_added=repo.latest_version_href, name="rawhide"
    )
    ref_rawhide = refs_rawhide.results[0]

    commits_rawhide = ostree_content_commits_api_client.list(
        repository_version_added=repo.latest_version_href,
        checksum=ref_rawhide.checksum,
    )
    assert commits_rawhide.count == 1

    commit_rawhide = commits_rawhide.results[0]
    assert commit_rawhide.checksum == ref_rawhide.checksum
    assert commit_rawhide.pulp_href == ref_rawhide.commit
