import os
import requests
import shutil
import subprocess
import unittest

from pathlib import Path
from urllib.parse import urljoin

from pulp_smash import config, api
from pulp_smash.pulp3.bindings import delete_orphans, monitor_task
from pulp_smash.pulp3.utils import gen_repo, gen_distribution, utils

from pulpcore.client.pulp_ostree import (
    DistributionsOstreeApi,
    OstreeOstreeRepository,
    OstreeOstreeDistribution,
    OstreeRepoImport,
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
        commit_data = OstreeRepoImport(artifact["pulp_href"], repo_name1)
        response = self.repositories_api.import_commits(repo.pulp_href, commit_data)
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

        ostree_repo_path = urljoin(self.distributions_api.read(distribution).base_url, repo_name1)

        # 10. initialize a second local OSTree repository and pull the content from Pulp
        remote_name = init_local_repo_with_remote(repo_name2, ostree_repo_path)
        self.addCleanup(shutil.rmtree, Path(repo_name2))
        validate_repo_integrity(repo_name2, f"{remote_name}:foo")

    def test_single_ref_import(self):
        """Import a new child commit, publish it, and pull it from Pulp."""
        self.repo_name1 = utils.uuid4()
        self.repo_name2 = utils.uuid4()
        sample_dir1 = Path(utils.uuid4())
        sample_dir2 = Path(utils.uuid4())
        sample_file1 = sample_dir1 / Path(utils.uuid4())
        sample_file2 = sample_dir2 / Path(utils.uuid4())

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
            commit_checksum1 = ref.read().strip()

        # 3. create a tarball from the first repository
        subprocess.run(["tar", "-cvf", f"{self.repo_name1}1.tar", f"{self.repo_name1}/"])
        self.addCleanup(os.unlink, f"{self.repo_name1}1.tar")
        self.commit_repo1_artifact = gen_artifact(f"{self.repo_name1}1.tar")

        shutil.rmtree(self.repo_name1)

        # 4. create a second file
        sample_dir2.mkdir()
        self.addCleanup(shutil.rmtree, sample_dir2)
        sample_file2.touch()

        # 5. initialize a second OSTree repository and commit the created file
        subprocess.run(["ostree", f"--repo={self.repo_name1}", "init", "--mode=archive"])
        subprocess.run(
            [
                "ostree",
                f"--repo={self.repo_name1}",
                "commit",
                "--branch=foo",
                f"{sample_dir2}/",
                f"--parent={commit_checksum1}",
            ]
        )

        with open(f"{self.repo_name1}/refs/heads/foo", "r") as ref:
            commit_checksum2 = ref.read().strip()

        # 6. create a tarball from the second repository
        subprocess.run(["tar", "-cvf", f"{self.repo_name1}2.tar", f"{self.repo_name1}/"])
        self.addCleanup(os.unlink, f"{self.repo_name1}2.tar")
        self.commit_repo2_artifact = gen_artifact(f"{self.repo_name1}2.tar")

        shutil.rmtree(self.repo_name1)

        # 7. import the first repository
        repo = self.repositories_api.create(OstreeOstreeRepository(**gen_repo()))
        self.addCleanup(self.repositories_api.delete, repo.pulp_href)
        commit_data = OstreeRepoImport(self.commit_repo1_artifact["pulp_href"], self.repo_name1)
        response = self.repositories_api.import_commits(repo.pulp_href, commit_data)
        repo_version = monitor_task(response.task).created_resources[0]

        repository_version = self.versions_api.read(repo_version)
        added_content = repository_version.content_summary.added
        self.assertEqual(added_content["ostree.config"]["count"], 1)
        self.assertEqual(added_content["ostree.refs"]["count"], 1)
        self.assertEqual(added_content["ostree.commit"]["count"], 1)
        self.assertEqual(added_content["ostree.object"]["count"], 3)

        # 8. import data from the second repository
        created_commits = self.commits_api.list(repository_version_added=repo_version)
        parent_commit = created_commits.to_dict()["results"][0]

        add_data = OstreeRepoImport(
            self.commit_repo2_artifact["pulp_href"],
            self.repo_name1,
            "foo",
            parent_commit["checksum"],
        )
        response = self.repositories_api.import_commits(repo.pulp_href, add_data)
        repo_version = monitor_task(response.task).created_resources[0]

        repository_version = self.versions_api.read(repo_version)
        added_content = repository_version.content_summary.added
        self.assertEqual(added_content["ostree.refs"]["count"], 1)
        self.assertEqual(added_content["ostree.commit"]["count"], 1)
        # when an OSTree repository contains a committed empty file and we are committing another
        # empty file, only a dirtree object is updated since only the parent directory has changed
        self.assertEqual(added_content["ostree.object"]["count"], 1)

        removed_content = repository_version.content_summary.removed
        # the old ref should be removed from the repository
        self.assertEqual(removed_content["ostree.refs"]["count"], 1)

        # 9. verify the latest commit's fields (the checksum and reference to the parent commit)
        created_refs = self.refs_api.list(repository_version_added=repo_version)
        latest_commit_href = created_refs.to_dict()["results"][0]["commit"]
        latest_commit = self.commits_api.read(latest_commit_href)
        self.assertEqual(latest_commit.parent_commit, parent_commit["pulp_href"])
        self.assertNotEqual(latest_commit.checksum, parent_commit["checksum"])

        # 10. publish the parsed commits
        distribution_data = OstreeOstreeDistribution(**gen_distribution(repository=repo.pulp_href))
        response = self.distributions_api.create(distribution_data)
        distribution = monitor_task(response.task).created_resources[0]
        self.addCleanup(self.distributions_api.delete, distribution)

        ostree_repo_path = urljoin(
            self.distributions_api.read(distribution).base_url, self.repo_name1
        )

        # 11. initialize a local OSTree repository and pull the content from Pulp
        remote_name = init_local_repo_with_remote(self.repo_name2, ostree_repo_path)
        self.addCleanup(shutil.rmtree, Path(self.repo_name2))
        commits_to_check = {commit_checksum1, commit_checksum2}
        validate_repo_integrity(self.repo_name2, f"{remote_name}:foo", commits_to_check)

    def test_version_removal(self):
        """Test the repository version removal functionality by removing two adjacent versions."""
        self.test_single_ref_import()

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
