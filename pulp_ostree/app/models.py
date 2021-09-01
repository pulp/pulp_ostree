from logging import getLogger

from django.db import models

from pulpcore.plugin.models import (
    Content,
    Remote,
    Repository,
    Distribution,
)
from pulpcore.plugin.repo_version_utils import remove_duplicates, validate_duplicate_content

logger = getLogger(__name__)


class OstreeCommit(Content):
    """A content model for an OSTree commit."""

    TYPE = "commit"

    parent_commit = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE)
    checksum = models.CharField(max_length=64, db_index=True)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        unique_together = ("checksum",)


class OstreeRef(Content):
    """A content model for an OSTree head commit."""

    TYPE = "refs"
    repo_key_fields = ("name",)

    commit = models.ForeignKey(
        OstreeCommit, related_name="refs_commit", null=True, on_delete=models.CASCADE
    )
    name = models.CharField(max_length=255, db_index=True)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        unique_together = ("name", "commit")


class OstreeObjectType(models.IntegerChoices):
    """An enum of all possible OSTree repository objects."""

    OSTREE_OBJECT_TYPE_FILE = 1
    OSTREE_OBJECT_TYPE_DIR_TREE = 2
    OSTREE_OBJECT_TYPE_DIR_META = 3
    OSTREE_OBJECT_TYPE_COMMIT = 4
    OSTREE_OBJECT_TYPE_TOMBSTONE_COMMIT = 5
    OSTREE_OBJECT_TYPE_COMMIT_META = 6
    OSTREE_OBJECT_TYPE_PAYLOAD_LINK = 7


class OstreeObject(Content):
    """A content model for a regular OSTree object (e.g., dirtree, dirmeta, file)."""

    TYPE = "object"

    commit = models.ForeignKey(
        OstreeCommit, related_name="object_commit", null=True, on_delete=models.CASCADE
    )
    typ = models.IntegerField(choices=OstreeObjectType.choices)
    checksum = models.CharField(max_length=64, db_index=True)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        unique_together = ("checksum",)


class OstreeConfig(Content):
    """A content model for an OSTree repository configuration file."""

    TYPE = "config"

    sha256 = models.CharField(max_length=64, db_index=True)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        unique_together = ("sha256",)


class OstreeSummary(Content):
    """A content model for an OSTree summary file."""

    TYPE = "summary"

    sha256 = models.CharField(max_length=64, db_index=True)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        unique_together = ("sha256",)


class OstreeRemote(Remote):
    """A remote model for OSTree content."""

    TYPE = "ostree"

    depth = models.IntegerField(default=0)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"


class OstreeRepository(Repository):
    """A repository model for OSTree content."""

    TYPE = "ostree"

    CONTENT_TYPES = [OstreeCommit, OstreeRef, OstreeObject, OstreeConfig, OstreeSummary]

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"

    def finalize_new_version(self, new_version):
        """Handle repository duplicates."""
        remove_duplicates(new_version)
        validate_duplicate_content(new_version)


class OstreeDistribution(Distribution):
    """A distribution model for OSTree content."""

    TYPE = "ostree"

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
