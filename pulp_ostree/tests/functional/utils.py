"""Utilities for tests for the ostree plugin."""

import subprocess
from uuid import uuid4


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
