"""Constants for Pulp Ostree plugin tests."""
from urllib.parse import urljoin

from pulp_smash.constants import PULP_FIXTURES_BASE_URL
from pulp_smash.pulp3.constants import (
    BASE_DISTRIBUTION_PATH,
    BASE_PUBLICATION_PATH,
    BASE_REMOTE_PATH,
    BASE_REPO_PATH,
    BASE_CONTENT_PATH,
)

# FIXME: list any download policies supported by your plugin type here.
# If your plugin supports all download policies, you can import this
# from pulp_smash.pulp3.constants instead.
# DOWNLOAD_POLICIES = ["immediate", "streamed", "on_demand"]
DOWNLOAD_POLICIES = ["immediate"]

# FIXME: replace 'unit' with your own content type names, and duplicate as necessary for each type
OSTREE_CONTENT_NAME = "ostree.unit"

# FIXME: replace 'unit' with your own content type names, and duplicate as necessary for each type
OSTREE_CONTENT_PATH = urljoin(BASE_CONTENT_PATH, "ostree/units/")

OSTREE_REMOTE_PATH = urljoin(BASE_REMOTE_PATH, "ostree/ostree/")

OSTREE_REPO_PATH = urljoin(BASE_REPO_PATH, "ostree/ostree/")

OSTREE_PUBLICATION_PATH = urljoin(BASE_PUBLICATION_PATH, "ostree/ostree/")

OSTREE_DISTRIBUTION_PATH = urljoin(BASE_DISTRIBUTION_PATH, "ostree/ostree/")

# FIXME: replace this with your own fixture repository URL and metadata
OSTREE_FIXTURE_URL = urljoin(PULP_FIXTURES_BASE_URL, "ostree/")
"""The URL to a ostree repository."""

# FIXME: replace this with the actual number of content units in your test fixture
OSTREE_FIXTURE_COUNT = 3
"""The number of content units available at :data:`OSTREE_FIXTURE_URL`."""

OSTREE_FIXTURE_SUMMARY = {OSTREE_CONTENT_NAME: OSTREE_FIXTURE_COUNT}
"""The desired content summary after syncing :data:`OSTREE_FIXTURE_URL`."""

# FIXME: replace this with your own fixture repository URL and metadata
OSTREE_INVALID_FIXTURE_URL = urljoin(PULP_FIXTURES_BASE_URL, "ostree-invalid/")
"""The URL to an invalid ostree repository."""

# FIXME: replace this with your own fixture repository URL and metadata
OSTREE_LARGE_FIXTURE_URL = urljoin(PULP_FIXTURES_BASE_URL, "ostree_large/")
"""The URL to a ostree repository containing a large number of content units."""

# FIXME: replace this with the actual number of content units in your test fixture
OSTREE_LARGE_FIXTURE_COUNT = 25
"""The number of content units available at :data:`OSTREE_LARGE_FIXTURE_URL`."""
