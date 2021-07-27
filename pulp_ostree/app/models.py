"""
Check `Plugin Writer's Guide`_ for more details.

.. _Plugin Writer's Guide:
    https://docs.pulpproject.org/pulpcore/plugins/plugin-writer/index.html
"""

from logging import getLogger

from django.db import models

from pulpcore.plugin.models import (
    Content,
    Remote,
    Repository,
    Publication,
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


class OstreeRefsHead(Content):
    """A content model for an OSTree head commit."""

    TYPE = "refs"
    repo_key_fields = ("name",)

    commit = models.ForeignKey(
        OstreeCommit, related_name="refshead_commit", null=True, on_delete=models.CASCADE
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

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"


class OstreePublication(Publication):
    """
    A Publication for OstreeContent.

    Define any additional fields for your new publication if needed.
    """

    TYPE = "ostree"

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"


class OstreeRemote(Remote):
    """
    A Remote for OstreeContent.

    Define any additional fields for your new remote if needed.
    """

    TYPE = "ostree"

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"


class OstreeRepository(Repository):
    """
    A Repository for OstreeContent.

    Define any additional fields for your new repository if needed.
    """

    TYPE = "ostree"

    CONTENT_TYPES = [OstreeCommit, OstreeRefsHead, OstreeObject, OstreeConfig]

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"

    def finalize_new_version(self, new_version):
        """Handle RefsHead duplicates."""
        remove_duplicates(new_version)
        validate_duplicate_content(new_version)


class OstreeDistribution(Distribution):
    """
    A Distribution for OstreeContent.

    Define any additional fields for your new distribution if needed.
    """

    TYPE = "ostree"

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
