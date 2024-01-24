import pytest

from pulp_ostree.tests.functional.utils import (
    init_local_repo_with_remote,
    validate_repo_integrity,
)


@pytest.fixture
def sync(
    ostree_distribution_factory,
    ostree_distributions_api_client,
    sync_repo_version,
    tmp_path,
):
    """Synchronize content from a remote repository and check validity of a Pulp repository."""

    def _sync(
        policy,
    ):
        # 1. synchronize content from the remote
        repo_version, remote, repo = sync_repo_version(policy=policy)
        added_content = repo_version.content_summary.added

        # 2. validate newly added content
        assert added_content["ostree.config"]["count"] == 1
        assert added_content["ostree.refs"]["count"] == 2
        assert added_content["ostree.commit"]["count"] == 2
        assert added_content["ostree.object"]["count"] == 3
        assert added_content["ostree.summary"]["count"] == 1

        # 3. synchronize from the same remote once again
        previous_version_href = repo_version.pulp_href
        _, remote, repo = sync_repo_version(remote=remote, repo=repo, policy=policy)

        assert previous_version_href == repo.latest_version_href

        # 4. publish the synced content
        distribution = ostree_distribution_factory(repository=repo.pulp_href)
        ostree_repo_path = ostree_distributions_api_client.read(distribution.pulp_href).base_url

        # 5. initialize a local OSTree repository and pull the content from Pulp
        remote_name = init_local_repo_with_remote(tmp_path / remote.name, ostree_repo_path)
        validate_repo_integrity(tmp_path / remote.name, f"{remote_name}:rawhide")
        validate_repo_integrity(tmp_path / remote.name, f"{remote_name}:stable")

    return _sync


@pytest.mark.parallel
def test_on_demand_sync(sync):
    """Test on_demand synchronization."""
    sync("on_demand")


@pytest.mark.parallel
def test_immediate_sync(sync):
    """Test immediate synchronization."""
    sync("immediate")


@pytest.mark.parallel
def test_filter_rawhide_ref_sync(
    ostree_content_refs_api_client,
    ostree_remote_factory,
    ostree_repository_factory,
    sync_repo_version,
):
    """Synchronize content from a remote repository considering only a specific ref."""
    repo = ostree_repository_factory()
    remote = ostree_remote_factory(depth=0, include_refs=["rawhide"], exclude_refs=["stable"])
    assert remote.include_refs == ["rawhide"]
    assert remote.exclude_refs == ["stable"]

    repo_version, _, _ = sync_repo_version(repo=repo, remote=remote)
    refs = ostree_content_refs_api_client.list(
        repository_version_added=repo_version.pulp_href
    ).results
    assert len(refs) == 1
    assert refs[0].name == "rawhide"


@pytest.mark.parallel
def test_exclude_all_refs_sync(ostree_remote_factory, ostree_repository_factory, sync_repo_version):
    """Synchronize content from a remote repository when a user excludes all refs."""
    repo = ostree_repository_factory()
    remote = ostree_remote_factory(depth=0, exclude_refs=["*"])

    assert remote.include_refs is None
    assert remote.exclude_refs == ["*"]

    repository_version, _, _ = sync_repo_version(repo=repo, remote=remote)
    added_content = repository_version.content_summary.added

    assert added_content["ostree.config"]["count"] == 1
    assert added_content["ostree.summary"]["count"] == 1

    with pytest.raises(KeyError):
        added_content["ostree.refs"]
    with pytest.raises(KeyError):
        added_content["ostree.commit"]
    with pytest.raises(KeyError):
        added_content["ostree.object"]
