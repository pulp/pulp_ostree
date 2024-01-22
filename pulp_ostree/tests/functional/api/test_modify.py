import pytest

from pulp_ostree.tests.functional.utils import (
    init_local_repo_with_remote,
    validate_repo_integrity,
)


@pytest.fixture
def normalize_content(
    ostree_content_commits_api_client,
    ostree_content_configs_api_client,
    ostree_content_objects_api_client,
    ostree_content_refs_api_client,
    ostree_content_summaries_api_client,
):
    """Make the repository content to be ready for comparison purposes."""

    def _normalize_content(repo):
        commits = sorted(
            ostree_content_commits_api_client.list(repository_version=repo).results,
            key=lambda item: item.pulp_href,
        )
        configs = sorted(
            ostree_content_configs_api_client.list(repository_version=repo).results,
            key=lambda item: item.pulp_href,
        )
        objects = sorted(
            ostree_content_objects_api_client.list(repository_version=repo).results,
            key=lambda item: item.pulp_href,
        )
        refs = sorted(
            ostree_content_refs_api_client.list(repository_version=repo).results,
            key=lambda item: item.pulp_href,
        )
        summaries = sorted(
            ostree_content_summaries_api_client.list(repository_version=repo).results,
            key=lambda item: item.pulp_href,
        )
        return commits + configs + objects + refs + summaries

    return _normalize_content


@pytest.mark.parallel
def test_add_ref_and_commit(
    monitor_task,
    ostree_content_commits_api_client,
    ostree_content_configs_api_client,
    ostree_content_refs_api_client,
    ostree_distribution_factory,
    ostree_distributions_api_client,
    ostree_repositories_api_client,
    ostree_repository_factory,
    synced_repo_version,
    tmp_path,
):
    """Copy one commit and one ref from the existing repository."""
    repo_version1, remote, _ = synced_repo_version
    created_refs = ostree_content_refs_api_client.list(
        repository_version_added=repo_version1.pulp_href
    )
    ref = ostree_content_refs_api_client.read(created_refs.to_dict()["results"][0]["pulp_href"])
    latest_commit = ostree_content_commits_api_client.read(ref.commit)

    configs = ostree_content_configs_api_client.list(
        repository_version_added=repo_version1.pulp_href
    )
    cfg = ostree_content_configs_api_client.read(configs.to_dict()["results"][0]["pulp_href"])

    repo2 = ostree_repository_factory()
    response = ostree_repositories_api_client.modify(
        ostree_ostree_repository_href=repo2.pulp_href,
        repository_add_remove_content={
            "add_content_units": [ref.pulp_href, latest_commit.pulp_href, cfg.pulp_href]
        },
    )
    monitor_task(response.task)
    repo2 = ostree_repositories_api_client.read(repo2.pulp_href)
    assert repo2.latest_version_href == f"{repo2.pulp_href}versions/1/"

    distribution = ostree_distribution_factory(repository=repo2.pulp_href)
    ostree_repo_path = ostree_distributions_api_client.read(distribution.pulp_href).base_url
    remote_name = init_local_repo_with_remote(tmp_path / remote.name, ostree_repo_path)
    validate_repo_integrity(
        tmp_path / remote.name,
        f"{remote_name}:{ref.name}",
        commits_to_check={latest_commit.checksum},
        depth=0,
    )


@pytest.mark.parallel
def test_add_refs_commits(
    monitor_task,
    ostree_content_commits_api_client,
    ostree_content_configs_api_client,
    ostree_content_refs_api_client,
    ostree_distribution_factory,
    ostree_distributions_api_client,
    ostree_repositories_api_client,
    ostree_repositories_versions_api_client,
    ostree_repository_factory,
    synced_repo_version,
    tmp_path,
):
    """Copy multiple refs and commits at once."""
    repo_version1, remote, _ = synced_repo_version
    created_refs = ostree_content_refs_api_client.list(
        repository_version_added=repo_version1.pulp_href
    )
    ref1 = ostree_content_refs_api_client.read(created_refs.to_dict()["results"][0]["pulp_href"])
    latest_commit = ostree_content_commits_api_client.read(ref1.commit)

    ref2 = ostree_content_refs_api_client.read(created_refs.to_dict()["results"][1]["pulp_href"])
    another_ref_commit = ostree_content_commits_api_client.read(ref2.commit)

    configs = ostree_content_configs_api_client.list(
        repository_version_added=repo_version1.pulp_href
    )
    cfg = ostree_content_configs_api_client.read(configs.to_dict()["results"][0]["pulp_href"])

    repo2 = ostree_repository_factory()
    response = ostree_repositories_api_client.modify(
        ostree_ostree_repository_href=repo2.pulp_href,
        repository_add_remove_content={
            "add_content_units": [ref1.pulp_href, another_ref_commit.pulp_href, cfg.pulp_href]
        },
    )

    monitor_task(response.task)

    repo2 = ostree_repositories_api_client.read(repo2.pulp_href)
    assert repo2.latest_version_href == f"{repo2.pulp_href}versions/1/"

    repository_version = ostree_repositories_versions_api_client.read(repo2.latest_version_href)
    added_content = repository_version.content_summary.added
    assert added_content["ostree.refs"]["count"] == 1
    assert added_content["ostree.commit"]["count"] == 2
    assert added_content["ostree.object"]["count"] == 3

    distribution = ostree_distribution_factory(repository=repo2.pulp_href)
    ostree_repo_path = ostree_distributions_api_client.read(distribution.pulp_href).base_url

    remote_name = init_local_repo_with_remote(tmp_path / remote.name, ostree_repo_path)
    validate_repo_integrity(
        tmp_path / remote.name,
        f"{remote_name}:{ref1.name}",
        commits_to_check={latest_commit.checksum},
        depth=0,
    )


@pytest.mark.parallel
def test_copy_whole_repository(
    monitor_task,
    normalize_content,
    ostree_repositories_api_client,
    ostree_repository_factory,
    synced_repo_version,
):
    """Initialize a new repository from the existing repository."""
    repo_version1, _, repo1 = synced_repo_version
    repo2 = ostree_repository_factory()
    response = ostree_repositories_api_client.modify(
        ostree_ostree_repository_href=repo2.pulp_href,
        repository_add_remove_content={"base_version": repo_version1.pulp_href},
    )
    monitor_task(response.task)

    repo2 = ostree_repositories_api_client.read(repo2.pulp_href)
    assert repo2.latest_version_href == f"{repo2.pulp_href}versions/1/"

    repo1_content = normalize_content(repo1.latest_version_href)
    repo2_content = normalize_content(repo2.latest_version_href)

    assert repo1_content == repo2_content, repo2_content


@pytest.mark.parallel
def test_remove_ref_and_commit(
    monitor_task,
    ostree_content_commits_api_client,
    ostree_content_refs_api_client,
    ostree_repositories_api_client,
    ostree_repositories_versions_api_client,
    synced_repo_version,
):
    """Remove one ref and one commit at once."""
    repo_version1, _, repo1 = synced_repo_version
    created_refs = ostree_content_refs_api_client.list(
        repository_version_added=repo_version1.pulp_href
    )
    ref = ostree_content_refs_api_client.read(created_refs.to_dict()["results"][0]["pulp_href"])
    latest_commit = ostree_content_commits_api_client.read(ref.commit)

    second_ref = ostree_content_refs_api_client.read(
        created_refs.to_dict()["results"][1]["pulp_href"]
    )
    second_commit = ostree_content_commits_api_client.read(second_ref.commit)

    response = ostree_repositories_api_client.modify(
        ostree_ostree_repository_href=repo1.pulp_href,
        repository_add_remove_content={
            "remove_content_units": [ref.pulp_href, latest_commit.pulp_href]
        },
    )
    monitor_task(response.task)

    repo1 = ostree_repositories_api_client.read(repo1.pulp_href)
    assert repo1.latest_version_href == f"{repo1.pulp_href}versions/2/"

    repository_version = ostree_repositories_versions_api_client.read(repo1.latest_version_href)
    removed_content = repository_version.content_summary.removed

    assert removed_content["ostree.refs"]["count"] == 1
    assert removed_content["ostree.commit"]["count"] == 1
    # the objects are referenced by a different commit; so, they should not be removed
    if "ostree.object" in removed_content:
        assert False, "The created repository version should not contain ostree objects."

    removed_refs = ostree_content_refs_api_client.list(
        repository_version_removed=repo1.latest_version_href
    )
    removed_ref = ostree_content_refs_api_client.read(
        removed_refs.to_dict()["results"][0]["pulp_href"]
    )
    assert ref == removed_ref

    removed_commits = ostree_content_commits_api_client.list(
        repository_version_removed=repo1.latest_version_href
    )
    removed_commit = ostree_content_commits_api_client.read(
        removed_commits.to_dict()["results"][0]["pulp_href"]
    )
    assert latest_commit == removed_commit

    # now, remove the second commit and check whether the referenced objects were removed too
    response = ostree_repositories_api_client.modify(
        ostree_ostree_repository_href=repo1.pulp_href,
        repository_add_remove_content={"remove_content_units": [second_commit.pulp_href]},
    )
    monitor_task(response.task)

    repo1 = ostree_repositories_api_client.read(repo1.pulp_href)
    assert repo1.latest_version_href == f"{repo1.pulp_href}versions/3/"

    repository_version = ostree_repositories_versions_api_client.read(repo1.latest_version_href)
    removed_content = repository_version.content_summary.removed
    assert removed_content["ostree.commit"]["count"] == 1
    assert removed_content["ostree.object"]["count"] == 3


@pytest.mark.parallel
def test_add_remove_obj(
    monitor_task,
    ostree_content_objects_api_client,
    ostree_repositories_api_client,
    synced_repo_version,
):
    """Try to modify an object (e.g., dirtree, dirmeta, ...) in the existing repository."""
    repo_version1, _, repo1 = synced_repo_version
    created_objs = ostree_content_objects_api_client.list(
        repository_version_added=repo_version1.pulp_href
    )
    obj = created_objs.to_dict()["results"][0]

    version1 = repo1.latest_version_href

    # objects should be ignored by the machinery
    response = ostree_repositories_api_client.modify(
        ostree_ostree_repository_href=repo1.pulp_href,
        repository_add_remove_content={"add_content_units": [obj["pulp_href"]]},
    )
    monitor_task(response.task)
    repo1 = ostree_repositories_api_client.read(repo1.pulp_href)
    version2 = repo1.latest_version_href
    assert version1 == version2

    response = ostree_repositories_api_client.modify(
        ostree_ostree_repository_href=repo1.pulp_href,
        repository_add_remove_content={"remove_content_units": [obj["pulp_href"]]},
    )
    monitor_task(response.task)
    repo1 = ostree_repositories_api_client.read(repo1.pulp_href)
    version2 = repo1.latest_version_href
    assert version1 == version2
