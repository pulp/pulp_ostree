import pytest

from pulpcore.client.pulp_ostree.exceptions import ApiException


@pytest.mark.parallel
def test_crud_remotes(gen_user, ostree_remote_factory, ostree_remotes_api_client, monitor_task):
    """Verify if users with different permissions can(not) perform CRUD operations on remotes."""
    user_creator = gen_user(model_roles=["ostree.ostreeremote_creator"])
    user_viewer = gen_user(model_roles=["ostree.ostreeremote_viewer"])
    user_anon = gen_user()

    with user_anon, pytest.raises(ApiException):
        ostree_remote_factory()
    with user_viewer, pytest.raises(ApiException):
        ostree_remote_factory()
    with user_creator:
        remote = ostree_remote_factory()

    with user_anon:
        assert 0 == ostree_remotes_api_client.list(name=remote.name).count
    with user_viewer:
        assert 1 == ostree_remotes_api_client.list(name=remote.name).count
    with user_creator:
        assert 1 == ostree_remotes_api_client.list(name=remote.name).count

    with user_anon, pytest.raises(ApiException):
        ostree_remotes_api_client.read(remote.pulp_href)
    with user_viewer:
        ostree_remotes_api_client.read(remote.pulp_href)
    with user_creator:
        ostree_remotes_api_client.read(remote.pulp_href)

    with user_anon, pytest.raises(ApiException):
        ostree_remotes_api_client.partial_update(remote.pulp_href, {"url": "https://redhat.com"})
    with user_viewer, pytest.raises(ApiException):
        ostree_remotes_api_client.partial_update(remote.pulp_href, {"url": "https://redhat.com"})
    with user_creator:
        ostree_remotes_api_client.partial_update(remote.pulp_href, {"url": "https://redhat.com"})

    with user_anon, pytest.raises(ApiException):
        ostree_remotes_api_client.delete(remote.pulp_href)
    with user_viewer, pytest.raises(ApiException):
        ostree_remotes_api_client.delete(remote.pulp_href)
    with user_creator:
        monitor_task(ostree_remotes_api_client.delete(remote.pulp_href).task)


@pytest.mark.parallel
def test_ref_content_access(gen_user, sync_repo_version, ostree_content_refs_api_client):
    """Verify if users with different access scopes can(not) preview refs."""
    user_creator = gen_user(
        model_roles=["ostree.ostreerepository_creator", "ostree.ostreeremote_creator"]
    )
    user_viewer = gen_user(model_roles=["ostree.ostreerepository_viewer"])
    user_anon = gen_user()

    with user_anon, pytest.raises(ApiException):
        sync_repo_version()
    with user_viewer, pytest.raises(ApiException):
        sync_repo_version()
    with user_creator:
        version, _, repo = sync_repo_version()

    with user_anon:
        assert 0 == ostree_content_refs_api_client.list(repository_version=version).count
    with user_viewer:
        assert 2 == ostree_content_refs_api_client.list(repository_version=version).count
    with user_creator:
        assert 2 == ostree_content_refs_api_client.list(repository_version=version).count

    ref = ostree_content_refs_api_client.list(repository_version=version).results[0]

    with user_anon, pytest.raises(ApiException):
        ostree_content_refs_api_client.read(ref.pulp_href)
    with user_viewer:
        ostree_content_refs_api_client.read(ref.pulp_href)
    with user_creator:
        ostree_content_refs_api_client.read(ref.pulp_href)
