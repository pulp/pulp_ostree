"""Utilities for tests for the ostree plugin."""
import subprocess

from functools import partial
from unittest import SkipTest

from pulp_smash import config, selectors
from pulp_smash.utils import uuid4
from pulp_smash.pulp3.utils import (
    gen_remote,
    require_pulp_3,
    require_pulp_plugins,
)

from pulp_ostree.tests.functional.constants import OSTREE_FIXTURE_URL

from pulpcore.client.pulpcore import (
    ApiClient as CoreApiClient,
    ArtifactsApi,
    TasksApi,
)
from pulpcore.client.pulp_ostree import ApiClient as OstreeApiClient


cfg = config.get_config()
configuration = cfg.get_bindings_config()


def set_up_module():
    """Skip tests Pulp 3 isn't under test or if pulp_ostree isn't installed."""
    require_pulp_3(SkipTest)
    require_pulp_plugins({"ostree"}, SkipTest)


def gen_ostree_client():
    """Return an ostree client object."""
    return OstreeApiClient(configuration)


def gen_ostree_remote(url=OSTREE_FIXTURE_URL, **kwargs):
    """Return a semi-random dict for use in creating a ostree Remote."""
    return gen_remote(url, **kwargs)


skip_if = partial(selectors.skip_if, exc=SkipTest)  # pylint:disable=invalid-name
"""The ``@skip_if`` decorator, customized for unittest.

:func:`pulp_smash.selectors.skip_if` is test runner agnostic. This function is
identical, except that ``exc`` has been set to ``unittest.SkipTest``.
"""

core_client = CoreApiClient(configuration)
tasks = TasksApi(core_client)


def gen_artifact(filepath):
    """Create an artifact from the file identified by the filepath."""
    artifact = ArtifactsApi(core_client).create(file=filepath)
    return artifact.to_dict()


def init_local_repo_with_remote(repo_name, remote_url):
    """Initialize a local OSTree repository by leveraging the ostree utility."""
    remote_repo_name = str(uuid4())
    repo_opt = f"--repo={repo_name}"
    subprocess.run(["ostree", repo_opt, "init", "--mode=archive"])
    subprocess.run(
        ["ostree", repo_opt, "remote", "--no-gpg-verify", "add", remote_repo_name, remote_url]
    )
    return remote_repo_name


def validate_repo_integrity(repo_name, remote_branch, commits_to_check=None, depth=-1):
    """Test the validity of the Pulp OSTree repository by pulling it to the local repository."""
    try:
        subprocess.check_output(
            [
                "ostree",
                f"--repo={repo_name}",
                "pull",
                "--mirror",
                remote_branch,
                f"--depth={depth}",
            ],
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(exc.output)

    try:
        subprocess.check_output(["ostree", "fsck", f"--repo={repo_name}"], stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(exc.output)

    if commits_to_check is not None:
        _, ref = remote_branch.split(":")
        output = subprocess.check_output(
            ["ostree", f"--repo={repo_name}", "log", ref], encoding="utf-8"
        )
        commits = {line.split()[1] for line in output.splitlines() if line.startswith("commit")}
        assert commits == commits_to_check
