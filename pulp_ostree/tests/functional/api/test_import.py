import os
import requests
import shutil
import subprocess
import unittest

from pathlib import Path

from pulp_smash import config, api
from pulp_smash.pulp3.bindings import delete_orphans, monitor_task
from pulp_smash.pulp3.utils import gen_repo, gen_distribution, utils

from pulpcore.client.pulp_ostree import (
    DistributionsOstreeApi,
    OstreeOstreeRepository,
    OstreeOstreeDistribution,
    OstreeImportAll,
    OstreeImportCommitsToRef,
    ContentCommitsApi,
    ContentRefsApi,
    RepositoriesOstreeApi,
    RepositoriesOstreeVersionsApi,
)

from pulp_ostree.tests.functional.utils import (
    gen_ostree_client,
    gen_artifact,
    init_local_repo_with_remote,
    validate_repo_integrity,
)


class ImportCommitTestCase(unittest.TestCase):
    """A test case that verifies the importing scenario."""

    @classmethod
    def setUpClass(cls):
        """Initialize class-wide variables."""
        cls.cfg = config.get_config()
        cls.client = api.Client(cls.cfg, api.json_handler)

        client_api = gen_ostree_client()
        cls.repositories_api = RepositoriesOstreeApi(client_api)
        cls.versions_api = RepositoriesOstreeVersionsApi(client_api)
        cls.distributions_api = DistributionsOstreeApi(client_api)
        cls.commits_api = ContentCommitsApi(client_api)
        cls.refs_api = ContentRefsApi(client_api)

    @classmethod
    def tearDownClass(cls):
        """Clean orphaned content after finishing the tests."""
        delete_orphans()

    def setUp(self):
        """Clean orphaned content before each test."""
        delete_orphans()

    def test_simple_tarball_import(self):
        """Import a repository consisting of three commit, publish it, and pull it from Pulp."""
        repo_name1 = utils.uuid4()
        repo_name2 = utils.uuid4()
        sample_dir = Path(utils.uuid4())
        sample_file1 = sample_dir / Path(utils.uuid4())
        sample_file2 = sample_dir / Path(utils.uuid4())

        # 1. create a first file
        sample_dir.mkdir()
        self.addCleanup(shutil.rmtree, sample_dir)
        sample_file1.touch()

        # 2. initialize a local OSTree repository and commit the created file
        subprocess.run(["ostree", f"--repo={repo_name1}", "init", "--mode=archive"])
        self.addCleanup(shutil.rmtree, repo_name1)
        subprocess.run(
            ["ostree", f"--repo={repo_name1}", "commit", "--branch=foo", f"{sample_dir}/"]
        )

        # 3. commit a second file
        sample_file2.touch()
        subprocess.run(
            ["ostree", f"--repo={repo_name1}", "commit", "--branch=foo", f"{sample_dir}/"]
        )

        # 4. create a second branch
        subprocess.run(
            ["ostree", f"--repo={repo_name1}", "commit", "--branch=bar", f"{sample_dir}/"]
        )

        # 5. create a tarball of the repository
        subprocess.run(["tar", "-cvf", f"{repo_name1}.tar", f"{repo_name1}/"])
        self.addCleanup(os.unlink, f"{repo_name1}.tar")

        # 6. create an artifact from the tarball
        artifact = gen_artifact(f"{repo_name1}.tar")

        # 7. commit the tarball to a Pulp repository
        repo = self.repositories_api.create(OstreeOstreeRepository(**gen_repo()))
        self.addCleanup(self.repositories_api.delete, repo.pulp_href)
        commit_data = OstreeImportAll(artifact["pulp_href"], repo_name1)
        response = self.repositories_api.import_all(repo.pulp_href, commit_data)
        repo_version = monitor_task(response.task).created_resources[0]

        # 8. check the number of created commits, branches (refs), and objects
        repository_version = self.versions_api.read(repo_version)
        added_content = repository_version.content_summary.added
        self.assertEqual(added_content["ostree.config"]["count"], 1)
        self.assertEqual(added_content["ostree.refs"]["count"], 2)
        self.assertEqual(added_content["ostree.commit"]["count"], 3)
        self.assertEqual(added_content["ostree.object"]["count"], 4)

        # 9. publish the parsed tarball
        distribution_data = OstreeOstreeDistribution(**gen_distribution(repository=repo.pulp_href))
        response = self.distributions_api.create(distribution_data)
        distribution = monitor_task(response.task).created_resources[0]
        self.addCleanup(self.distributions_api.delete, distribution)

        ostree_repo_path = self.distributions_api.read(distribution).base_url

        # 10. initialize a second local OSTree repository and pull the content from Pulp
        remote_name = init_local_repo_with_remote(repo_name2, ostree_repo_path)
        self.addCleanup(shutil.rmtree, Path(repo_name2))
        validate_repo_integrity(repo_name2, f"{remote_name}:foo")

    def test_single_import_one_commit(self):
        """Append a new child commit to an existing repository and pull it from Pulp."""
        self.single_ref_import(1)

    def test_single_import_more_commits(self):
        """Append a set of commits to an existing repository and pull them from Pulp."""
        self.single_ref_import(5)

    def single_ref_import(self, number_of_commits):
        """Import child commits, publish them, and pull them from Pulp."""
        self.repo_name1 = utils.uuid4()
        self.repo_name2 = utils.uuid4()
        sample_dir1 = Path(utils.uuid4())
        sample_dir2 = Path(utils.uuid4())
        sample_file1 = sample_dir1 / Path(utils.uuid4())

        commits_to_check = []

        # 1. create a first file
        sample_dir1.mkdir()
        self.addCleanup(shutil.rmtree, sample_dir1)
        sample_file1.touch()

        # 2. initialize a local OSTree repository and commit the created file
        subprocess.run(["ostree", f"--repo={self.repo_name1}", "init", "--mode=archive"])
        subprocess.run(
            ["ostree", f"--repo={self.repo_name1}", "commit", "--branch=foo", f"{sample_dir1}/"]
        )
        with open(f"{self.repo_name1}/refs/heads/foo", "r") as ref:
            commits_to_check.append(ref.read().strip())

        # 3. create a tarball from the first repository
        subprocess.run(["tar", "-cvf", f"{self.repo_name1}1.tar", f"{self.repo_name1}/"])
        self.addCleanup(os.unlink, f"{self.repo_name1}1.tar")
        self.commit_repo1_artifact = gen_artifact(f"{self.repo_name1}1.tar")

        shutil.rmtree(self.repo_name1)

        # 4. initialize a second OSTree repository and commit the created file
        subprocess.run(["ostree", f"--repo={self.repo_name1}", "init", "--mode=archive"])

        sample_dir2.mkdir()
        self.addCleanup(shutil.rmtree, sample_dir2)

        # 5. create new commits by submitting randomly generated files one by one
        for _ in range(number_of_commits):
            sample_file2 = sample_dir2 / Path(utils.uuid4())
            sample_file2.touch()

            subprocess.run(
                [
                    "ostree",
                    f"--repo={self.repo_name1}",
                    "commit",
                    "--branch=foo",
                    f"{sample_dir2}/",
                    f"--parent={commits_to_check[-1]}",
                ]
            )

            with open(f"{self.repo_name1}/refs/heads/foo", "r") as ref:
                commits_to_check.append(ref.read().strip())

        # 6. create a tarball from the second repository
        subprocess.run(["tar", "-cvf", f"{self.repo_name1}2.tar", f"{self.repo_name1}/"])
        self.addCleanup(os.unlink, f"{self.repo_name1}2.tar")
        self.commit_repo2_artifact = gen_artifact(f"{self.repo_name1}2.tar")

        shutil.rmtree(self.repo_name1)

        # 7. import the first repository
        repo = self.repositories_api.create(OstreeOstreeRepository(**gen_repo()))
        self.addCleanup(self.repositories_api.delete, repo.pulp_href)
        commit_data = OstreeImportAll(self.commit_repo1_artifact["pulp_href"], self.repo_name1)
        response = self.repositories_api.import_all(repo.pulp_href, commit_data)
        repo_version = monitor_task(response.task).created_resources[0]

        repository_version = self.versions_api.read(repo_version)
        added_content = repository_version.content_summary.added
        self.assertEqual(added_content["ostree.config"]["count"], 1)
        self.assertEqual(added_content["ostree.refs"]["count"], 1)
        self.assertEqual(added_content["ostree.commit"]["count"], 1)
        self.assertEqual(added_content["ostree.object"]["count"], 3)

        # 8. import data from the second repository
        add_data = OstreeImportCommitsToRef(
            self.commit_repo2_artifact["pulp_href"], self.repo_name1, "foo"
        )
        response = self.repositories_api.import_commits(repo.pulp_href, add_data)
        repo_version = monitor_task(response.task).created_resources[0]

        repository_version = self.versions_api.read(repo_version)
        added_content = repository_version.content_summary.added
        self.assertEqual(added_content["ostree.refs"]["count"], 1)
        self.assertEqual(added_content["ostree.commit"]["count"], number_of_commits)
        # when an OSTree repository contains a committed empty file and we are committing another
        # empty file, only a dirtree object is updated since only the parent directory has changed
        self.assertEqual(added_content["ostree.object"]["count"], number_of_commits)

        removed_content = repository_version.content_summary.removed
        # the old ref should be removed from the repository
        self.assertEqual(removed_content["ostree.refs"]["count"], 1)

        # 9. verify commits' associations in backwards order
        for i in range(len(commits_to_check) - 1, 0, -1):
            commit = self.commits_api.list(checksum=commits_to_check[i]).results[0]
            self.assertIsNotNone(commit.parent_commit, commit)
            parent_commit = self.commits_api.read(commit.parent_commit)
            self.assertEqual(parent_commit.checksum, commits_to_check[i - 1])

        # 10. publish the parsed commits
        distribution_data = OstreeOstreeDistribution(**gen_distribution(repository=repo.pulp_href))
        response = self.distributions_api.create(distribution_data)
        distribution = monitor_task(response.task).created_resources[0]
        self.addCleanup(self.distributions_api.delete, distribution)

        ostree_repo_path = self.distributions_api.read(distribution).base_url

        # 11. initialize a local OSTree repository and pull the content from Pulp
        remote_name = init_local_repo_with_remote(self.repo_name2, ostree_repo_path)
        self.addCleanup(shutil.rmtree, Path(self.repo_name2))
        validate_repo_integrity(self.repo_name2, f"{remote_name}:foo", set(commits_to_check))

    def test_version_removal(self):
        """Test the repository version removal functionality by removing two adjacent versions."""
        self.single_ref_import(1)

        repo_href = self.repositories_api.list().to_dict()["results"][0]["pulp_href"]
        repo_version1_href = self.versions_api.read(f"{repo_href}versions/1/").pulp_href
        repo_version2_href = self.versions_api.read(f"{repo_href}versions/2/").pulp_href

        response = self.versions_api.delete(repo_version1_href)
        monitor_task(response.task)
        with self.assertRaises(requests.HTTPError) as exc:
            self.client.get(repo_version1_href)
        self.assertEqual(exc.exception.response.status_code, 404, repo_version2_href)

        response = self.versions_api.delete(repo_version2_href)
        monitor_task(response.task)
        with self.assertRaises(requests.HTTPError) as exc:
            self.client.get(repo_version2_href)
        self.assertEqual(exc.exception.response.status_code, 404, repo_version2_href)
