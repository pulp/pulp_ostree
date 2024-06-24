import pytest
import requests
import os
import shutil
import subprocess
import uuid

from requests.exceptions import HTTPError
from requests.auth import HTTPBasicAuth
from urllib.parse import urljoin

from pulpcore.client.pulp_ostree import (
    OstreeImportAll,
    OstreeImportCommitsToRef,
)

from pulp_ostree.tests.functional.utils import (
    init_local_repo_with_remote,
    validate_repo_integrity,
)


def test_simple_tarball_import(
    pulpcore_bindings,
    gen_object_with_cleanup,
    monitor_task,
    ostree_distributions_api_client,
    ostree_distribution_factory,
    ostree_repository_factory,
    ostree_repositories_api_client,
    ostree_repositories_versions_api_client,
    tmp_path,
):
    """Import a repository consisting of three commit, publish it, and pull it from Pulp."""
    os.chdir(tmp_path)
    repo_name1 = str(uuid.uuid4())
    repo_name2 = str(uuid.uuid4())
    sample_dir = tmp_path / str(uuid.uuid4())
    sample_file1 = sample_dir / str(uuid.uuid4())
    sample_file2 = sample_dir / str(uuid.uuid4())

    # 1. create a first file
    sample_dir.mkdir()
    sample_file1.touch()

    # 2. initialize a local OSTree repository and commit the created file
    subprocess.run(["ostree", f"--repo={repo_name1}", "init", "--mode=archive"])
    subprocess.run(["ostree", f"--repo={repo_name1}", "commit", "--branch=foo", f"{sample_dir}/"])

    # 3. commit a second file
    sample_file2.touch()
    subprocess.run(["ostree", f"--repo={repo_name1}", "commit", "--branch=foo", f"{sample_dir}/"])

    # 4. create a second branch
    subprocess.run(["ostree", f"--repo={repo_name1}", "commit", "--branch=bar", f"{sample_dir}/"])

    # 5. create a tarball of the repository
    subprocess.run(["tar", "-cvf", f"{repo_name1}.tar", f"{repo_name1}/"])

    # 6. create an artifact from the tarball
    artifact = gen_object_with_cleanup(pulpcore_bindings.ArtifactsApi, f"{repo_name1}.tar")

    # 7. commit the tarball to a Pulp repository
    repo = ostree_repository_factory()
    commit_data = OstreeImportAll(artifact.pulp_href, repo_name1)
    response = ostree_repositories_api_client.import_all(repo.pulp_href, commit_data)
    repo_version = monitor_task(response.task).created_resources[0]

    # 8. check the number of created commits, branches (refs), and objects
    repository_version = ostree_repositories_versions_api_client.read(repo_version)
    added_content = repository_version.content_summary.added
    assert added_content["ostree.config"]["count"] == 1
    assert added_content["ostree.refs"]["count"] == 2
    assert added_content["ostree.commit"]["count"] == 3
    assert added_content["ostree.object"]["count"] == 4

    # 9. publish the parsed tarball
    distribution = ostree_distribution_factory(repository=repo.pulp_href)
    ostree_repo_path = ostree_distributions_api_client.read(distribution.pulp_href).base_url

    # 10. initialize a second local OSTree repository and pull the content from Pulp
    remote_name = init_local_repo_with_remote(repo_name2, ostree_repo_path)
    validate_repo_integrity(repo_name2, f"{remote_name}:foo")


@pytest.mark.parallel
@pytest.mark.parametrize("number_of_commits", [1, 5])
def test_single_import_commit(single_ref_import, number_of_commits):
    """Append a new child commit to an existing repository and pull it from Pulp."""
    single_ref_import(number_of_commits)


@pytest.fixture
def single_ref_import(
    pulpcore_bindings,
    gen_object_with_cleanup,
    http_get,
    monitor_task,
    ostree_content_commits_api_client,
    ostree_distributions_api_client,
    ostree_distribution_factory,
    ostree_repositories_api_client,
    ostree_repository_factory,
    ostree_repositories_versions_api_client,
    tmp_path,
):
    """Import child commits, publish them, and pull them from Pulp."""

    def _single_ref_import(number_of_commits):
        os.chdir(tmp_path)
        repo_name1 = str(uuid.uuid4())
        repo_name2 = str(uuid.uuid4())
        sample_dir1 = tmp_path / str(uuid.uuid4())
        sample_dir2 = tmp_path / str(uuid.uuid4())
        sample_file1 = sample_dir1 / str(uuid.uuid4())

        commits_to_check = []

        # 1. create a first file
        sample_dir1.mkdir()
        sample_file1.touch()

        # 2. initialize a local OSTree repository and commit the created file
        subprocess.check_output(["ostree", f"--repo={repo_name1}", "init", "--mode=archive"])
        subprocess.check_output(
            ["ostree", f"--repo={repo_name1}", "commit", "--branch=foo", f"{sample_dir1}/"]
        )
        with open(f"{repo_name1}/refs/heads/foo", "r") as ref:
            commits_to_check.append(ref.read().strip())

        # 3. create a tarball from the first repository
        subprocess.run(["tar", "-cvf", f"{repo_name1}1.tar", f"{repo_name1}/"])
        commit_repo1_artifact = gen_object_with_cleanup(
            pulpcore_bindings.ArtifactsApi, f"{repo_name1}1.tar"
        )
        shutil.rmtree(repo_name1)

        # 4. initialize a second OSTree repository and commit the created file
        subprocess.check_output(["ostree", f"--repo={repo_name1}", "init", "--mode=archive"])
        sample_dir2.mkdir()

        # 5. create new commits by submitting randomly generated files one by one
        for _ in range(number_of_commits):
            sample_file2 = sample_dir2 / str(uuid.uuid4())
            sample_file2.touch()

            subprocess.check_output(
                [
                    "ostree",
                    f"--repo={repo_name1}",
                    "commit",
                    "--branch=foo",
                    f"{sample_dir2}/",
                    f"--parent={commits_to_check[-1]}",
                ]
            )

            with open(f"{repo_name1}/refs/heads/foo", "r") as ref:
                commits_to_check.append(ref.read().strip())

        # 6. create a tarball from the second repository
        subprocess.run(["tar", "-cvf", f"{repo_name1}2.tar", f"{repo_name1}/"])
        commit_repo2_artifact = gen_object_with_cleanup(
            pulpcore_bindings.ArtifactsApi, f"{repo_name1}2.tar"
        )

        # the latest parent commit is not accessible to this repository since it was removed;
        # therefore, we need to unpack the old repository into the new one to mimic the
        # behaviour that should occur in a real repository when computing static deltas
        subprocess.run(["tar", "-xvf", f"{repo_name1}1.tar", f"{repo_name1}/"])
        subprocess.check_output(
            [
                "ostree",
                f"--repo={repo_name1}",
                "static-delta",
                "generate",
                f"--from={commits_to_check[-2]}",
                f"--to={commits_to_check[-1]}",
            ]
        )

        deltas_paths = []
        for dirpath, _, filenames in os.walk(os.path.join(repo_name1, "deltas/")):
            for filename in filenames:
                full_path = os.path.join(dirpath, filename)
                deltas_paths.append(os.path.relpath(full_path, repo_name1))

        shutil.rmtree(repo_name1)

        # 7. import the first repository
        repo = ostree_repository_factory()
        commit_data = OstreeImportAll(commit_repo1_artifact.pulp_href, repo_name1)
        response = ostree_repositories_api_client.import_all(repo.pulp_href, commit_data)
        repo_version = monitor_task(response.task).created_resources[0]

        repository_version = ostree_repositories_versions_api_client.read(repo_version)
        added_content = repository_version.content_summary.added
        assert added_content["ostree.config"]["count"] == 1
        assert added_content["ostree.refs"]["count"] == 1
        assert added_content["ostree.commit"]["count"] == 1
        assert added_content["ostree.object"]["count"] == 3

        # 8. import data from the second repository
        add_data = OstreeImportCommitsToRef(commit_repo2_artifact.pulp_href, repo_name1, "foo")
        response = ostree_repositories_api_client.import_commits(repo.pulp_href, add_data)
        repo_version = monitor_task(response.task).created_resources[0]

        repository_version = ostree_repositories_versions_api_client.read(repo_version)
        added_content = repository_version.content_summary.added
        assert added_content["ostree.refs"]["count"] == 1
        assert added_content["ostree.commit"]["count"] == number_of_commits
        # when an OSTree repository contains a committed empty file and we are committing another
        # empty file, only a dirtree object is updated since only the parent directory has changed
        assert added_content["ostree.object"]["count"] == number_of_commits

        removed_content = repository_version.content_summary.removed
        # the old ref should be removed from the repository
        assert removed_content["ostree.refs"]["count"] == 1

        # 9. verify commits' associations in backwards order
        for i in range(len(commits_to_check) - 1, 0, -1):
            commit = ostree_content_commits_api_client.list(checksum=commits_to_check[i]).results[0]
            assert commit.parent_commit is not None, commit
            parent_commit = ostree_content_commits_api_client.read(commit.parent_commit)
            assert parent_commit.checksum == commits_to_check[i - 1]

        # 10. publish the parsed commits
        distribution = ostree_distribution_factory(repository=repo.pulp_href)
        ostree_repo_path = ostree_distributions_api_client.read(distribution.pulp_href).base_url

        # 11. initialize a local OSTree repository and pull the content from Pulp
        remote_name = init_local_repo_with_remote(repo_name2, ostree_repo_path)
        validate_repo_integrity(repo_name2, f"{remote_name}:foo", set(commits_to_check))

        # 12. check if static deltas are being published
        for delta_path in deltas_paths:
            response = http_get(urljoin(ostree_repo_path, delta_path))
            assert response

        return repo, distribution

    return _single_ref_import


@pytest.mark.parallel
def test_version_removal(
    bindings_cfg,
    monitor_task,
    ostree_distributions_api_client,
    ostree_repositories_versions_api_client,
    single_ref_import,
):
    """Test the repository version removal functionality by removing two adjacent versions."""
    repo, distribution = single_ref_import(1)
    monitor_task(ostree_distributions_api_client.delete(distribution.pulp_href).task)

    repo_version1_href = ostree_repositories_versions_api_client.read(
        f"{repo.pulp_href}versions/1/"
    ).pulp_href
    repo_version2_href = ostree_repositories_versions_api_client.read(
        f"{repo.pulp_href}versions/2/"
    ).pulp_href

    response = ostree_repositories_versions_api_client.delete(repo_version1_href)
    monitor_task(response.task)
    with pytest.raises(HTTPError) as exc:
        response = requests.get(
            urljoin(bindings_cfg.host, repo_version1_href),
            auth=HTTPBasicAuth(bindings_cfg.username, bindings_cfg.password),
        )
        response.raise_for_status()
    assert exc.value.response.status_code == 404, repo_version1_href

    response = ostree_repositories_versions_api_client.delete(repo_version2_href)
    monitor_task(response.task)
    with pytest.raises(HTTPError) as exc:
        response = requests.get(
            urljoin(bindings_cfg.host, repo_version2_href),
            auth=HTTPBasicAuth(bindings_cfg.username, bindings_cfg.password),
        )
        response.raise_for_status()
    assert exc.value.response.status_code == 404, repo_version2_href


@pytest.mark.parallel
def test_import_commits_same_ref(
    pulpcore_bindings,
    gen_object_with_cleanup,
    monitor_task,
    ostree_repository_factory,
    ostree_repositories_api_client,
    ostree_repositories_versions_api_client,
    tmp_path,
):
    """Import a repository with import-all, then import single commits with import-commits."""
    os.chdir(tmp_path)
    repo_name = "repo"
    sample_dir = tmp_path / str(uuid.uuid4())
    sample_file1 = sample_dir / str(uuid.uuid4())
    sample_file2 = sample_dir / str(uuid.uuid4())
    branch_name = "foo"

    # 1. create a first file
    sample_dir.mkdir()
    sample_file1.touch()

    # 2. initialize a local OSTree repository and commit the created file
    subprocess.run(["ostree", f"--repo={repo_name}", "init", "--mode=archive"])
    subprocess.run(
        ["ostree", f"--repo={repo_name}", "commit", f"--branch={branch_name}", f"{sample_dir}/"]
    )
    subprocess.run(["tar", "-cvf", f"{repo_name}.tar", f"{repo_name}/"])

    artifact = gen_object_with_cleanup(pulpcore_bindings.ArtifactsApi, f"{repo_name}.tar")
    repo = ostree_repository_factory(name=repo_name)
    commit_data = OstreeImportAll(artifact.pulp_href, repo_name)
    response = ostree_repositories_api_client.import_all(repo.pulp_href, commit_data)
    repo_version = monitor_task(response.task).created_resources[0]

    repository_version = ostree_repositories_versions_api_client.read(repo_version)
    added_content = repository_version.content_summary.added
    assert added_content["ostree.config"]["count"] == 1
    assert added_content["ostree.summary"]["count"] == 1
    assert added_content["ostree.refs"]["count"] == 1
    assert added_content["ostree.commit"]["count"] == 1

    parent_commit = ""
    with open(f"{repo_name}/refs/heads/{branch_name}", "r") as ref:
        parent_commit = ref.read().strip()

    # 3. commit a second file
    sample_file2.touch()
    subprocess.run(
        [
            "ostree",
            f"--repo={repo_name}",
            "commit",
            f"--branch={branch_name}",
            f"{sample_dir}/",
            f"--parent={parent_commit}",
        ]
    )
    subprocess.run(["tar", "-cvf", f"{repo_name}.tar", f"{repo_name}/"])

    artifact = gen_object_with_cleanup(pulpcore_bindings.ArtifactsApi, f"{repo_name}.tar")

    add_data = OstreeImportCommitsToRef(artifact.pulp_href, repo_name, branch_name)
    response = ostree_repositories_api_client.import_commits(repo.pulp_href, add_data)
    repo_version = monitor_task(response.task).created_resources[0]

    repository_version = ostree_repositories_versions_api_client.read(repo_version)
    added_content = repository_version.content_summary.added
    assert added_content["ostree.refs"]["count"] == 1
    assert added_content["ostree.commit"]["count"] == 1
    assert added_content["ostree.content"]["count"] == 2
    assert added_content["ostree.summary"]["count"] == 1


@pytest.mark.parallel
def test_import_all_as_ostree_repo_admin(
    pulpcore_bindings,
    gen_user,
    role_factory,
    gen_object_with_cleanup,
    monitor_task,
    ostree_repository_factory,
    ostree_repositories_api_client,
    ostree_repositories_versions_api_client,
    tmp_path,
):
    """Create a role for ostree admin, then import a repository with import-all."""

    os.chdir(tmp_path)
    repo_name = "repo"
    sample_dir = tmp_path / str(uuid.uuid4())
    sample_file1 = sample_dir / str(uuid.uuid4())
    branch_name = "foo"

    # 1. create a first file
    sample_dir.mkdir()
    sample_file1.touch()

    # 2. initialize a local OSTree repository and commit the created file
    subprocess.run(["ostree", f"--repo={repo_name}", "init", "--mode=archive"])
    subprocess.run(
        ["ostree", f"--repo={repo_name}", "commit", f"--branch={branch_name}", f"{sample_dir}/"]
    )
    subprocess.run(["tar", "-cvf", f"{repo_name}.tar", f"{repo_name}/"])

    user = gen_user(model_roles=["ostree.ostreerepository_creator"])

    with user:
        artifact = gen_object_with_cleanup(pulpcore_bindings.ArtifactsApi, f"{repo_name}.tar")
        repo = ostree_repository_factory(name=repo_name)
        commit_data = OstreeImportAll(artifact.pulp_href, repo_name)
        response = ostree_repositories_api_client.import_all(repo.pulp_href, commit_data)

    repo_version = monitor_task(response.task).created_resources[0]

    repository_version = ostree_repositories_versions_api_client.read(repo_version)
    added_content = repository_version.content_summary.added
    assert added_content["ostree.refs"]["count"] == 1
    assert added_content["ostree.commit"]["count"] == 1
