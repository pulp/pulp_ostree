"""Constants for Pulp Ostree plugin tests."""
from urllib.parse import urljoin

from pulp_smash.constants import PULP_FIXTURES_BASE_URL
from pulp_smash.pulp3.constants import (
    BASE_DISTRIBUTION_PATH,
    BASE_REMOTE_PATH,
    BASE_REPO_PATH,
    BASE_CONTENT_PATH,
)

OSTREE_COMMITS_NAME = "ostree.commit"
OSTREE_OBJECTS_NAME = "ostree.object"
OSTREE_REFS_NAME = "ostree.refs"
OSTREE_CONFIGS_NAME = "ostree.configs"
OSTREE_SUMMARIES_NAME = "ostree.summaries"

OSTREE_COMMIT_PATH = urljoin(BASE_CONTENT_PATH, "ostree/commits/")
OSTREE_REFSHEAD_PATH = urljoin(BASE_CONTENT_PATH, "ostree/refs/")
OSTREE_OBJECTS_PATH = urljoin(BASE_CONTENT_PATH, "ostree/objects/")
OSTREE_CONFIG_PATH = urljoin(BASE_CONTENT_PATH, "ostree/configs/")
OSTREE_SUMMARY_PATH = urljoin(BASE_CONTENT_PATH, "ostree/summaries/")

OSTREE_REMOTE_PATH = urljoin(BASE_REMOTE_PATH, "ostree/ostree/")

OSTREE_REPO_PATH = urljoin(BASE_REPO_PATH, "ostree/ostree/")

OSTREE_DISTRIBUTION_PATH = urljoin(BASE_DISTRIBUTION_PATH, "ostree/ostree/")

OSTREE_FIXTURE_URL = urljoin(PULP_FIXTURES_BASE_URL, "ostree/small/")
"""The URL to a ostree repository."""
