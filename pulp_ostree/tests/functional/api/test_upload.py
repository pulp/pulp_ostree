import os
import shutil
import subprocess
import unittest

from pathlib import Path
from urllib.parse import urlparse, urljoin

from pulp_smash import api, config
from pulp_smash.pulp3.bindings import delete_orphans, monitor_task
from pulp_smash.pulp3.utils import gen_repo, gen_distribution, utils

from pulpcore.client.pulp_ostree import (
    DistributionsOstreeApi,
    OstreeOstreeRepository,
    OstreeOstreeDistribution,
    OstreeRepoUpload,
    RepositoriesOstreeApi,
    RepositoriesOstreeVersionsApi,
)

from pulp_ostree.tests.functional.utils import gen_ostree_client, gen_artifact


class UploadCommitTestCase(unittest.TestCase):
    """A test case that verifies the uploading scenario."""

    @classmethod
    def setUpClass(cls):
        """Initialize class-wide variables."""
        cls.cfg = config.get_config()
        cls.registry_name = urlparse(cls.cfg.get_base_url()).netloc

        cls.client = api.Client(cls.cfg, api.code_handler)
        client_api = gen_ostree_client()
        cls.repositories_api = RepositoriesOstreeApi(client_api)
        cls.versions_api = RepositoriesOstreeVersionsApi(client_api)
        cls.distributions_api = DistributionsOstreeApi(client_api)

        cls.teardown_cleanups = []

        delete_orphans()

    @classmethod
    def tearDownClass(cls):
        """Clean the class-wide variables."""
        for cleanup_function, args in reversed(cls.teardown_cleanups):
            cleanup_function(args)

    def test_simple_tarball_upload(self):
        """Upload a repository consisting of three commit, publish it, and pull it from Pulp."""
        repo_name1 = utils.uuid4()
        repo_name2 = utils.uuid4()
        sample_dir = Path(utils.uuid4())
        sample_file1 = sample_dir / Path(utils.uuid4())
        sample_file2 = sample_dir / Path(utils.uuid4())

        # 1. create a first file
        sample_dir.mkdir()
        self.teardown_cleanups.append((shutil.rmtree, sample_dir))
        sample_file1.touch()

        # 2. initialize a local OSTree repository and commit the created file
        subprocess.run(["ostree", f"--repo={repo_name1}", "init", "--mode=archive"])
        self.teardown_cleanups.append((shutil.rmtree, Path(repo_name1)))
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
        self.teardown_cleanups.append((os.unlink, f"{repo_name1}.tar"))

        # 6. create an artifact from the tarball
        artifact = gen_artifact(f"{repo_name1}.tar")

        # 7. commit the tarball to a Pulp repository
        repo = self.repositories_api.create(OstreeOstreeRepository(**gen_repo()))
        self.teardown_cleanups.append((self.repositories_api.delete, repo.pulp_href))
        commit_data = OstreeRepoUpload(artifact["pulp_href"], repo_name1)
        response = self.repositories_api.commit(repo.pulp_href, commit_data)
        repo_version = monitor_task(response.task).created_resources[0]

        # 8. check the number of created commits, branches, and objects
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
        self.teardown_cleanups.append((self.distributions_api.delete, distribution))

        ostree_repo_path = urljoin(self.distributions_api.read(distribution).base_url, repo_name1)

        # 10. initialize a second local OSTree repository
        subprocess.run(["ostree", f"--repo={repo_name2}", "init", "--mode=archive"])
        self.teardown_cleanups.append((shutil.rmtree, Path(repo_name2)))
        subprocess.run(
            ["ostree", f"--repo={repo_name2}", "remote", "add", "pulpos", ostree_repo_path]
        )

        subprocess.run(
            [
                "ostree",
                "config",
                f"--repo={repo_name2}",
                "set",
                'remote "pulpos".gpg-verify',
                "false",
            ]
        )

        self.validate_repo_integrity(repo_name2, "pulpos:foo")

    def validate_repo_integrity(self, repo_name, mirror):
        """Test the validity of the Pulp OSTree repository by pulling it to the local repository."""
        try:
            subprocess.check_output(["ostree", f"--repo={repo_name}", "pull", "--mirror", mirror])
        except subprocess.CalledProcessError as exc:
            self.fail(exc.output)

        try:
            subprocess.check_output(["ostree", "fsck", f"--repo={repo_name}"])
        except subprocess.CalledProcessError as exc:
            self.fail(exc.output)
