"""Utilities for tests for the ostree plugin."""
import subprocess

from functools import partial
from unittest import SkipTest

from pulp_smash import config, selectors
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


def init_local_repo(repo_name, remote_url):
    """Initialize a local OSTree repository by leveraging the ostree utility."""
    repo_opt = f"--repo={repo_name}"

    subprocess.run(["ostree", repo_opt, "init", "--mode=archive"])
    subprocess.run(["ostree", repo_opt, "remote", "add", "pulpos", remote_url])

    subprocess.run(["ostree", "config", repo_opt, "set", 'remote "pulpos".gpg-verify', "false"])


def validate_repo_integrity(repo_name, mirror):
    """Test the validity of the Pulp OSTree repository by pulling it to the local repository."""
    try:
        subprocess.check_output(["ostree", f"--repo={repo_name}", "pull", "--mirror", mirror])
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(exc.output)

    try:
        subprocess.check_output(["ostree", "fsck", f"--repo={repo_name}"])
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(exc.output)
