from logging import getLogger

from django.db import models
from django.contrib.postgres.fields import ArrayField

from pulpcore.plugin.models import (
    AutoAddObjPermsMixin,
    Content,
    Remote,
    Repository,
    Distribution,
)
from pulpcore.plugin.repo_version_utils import remove_duplicates, validate_duplicate_content

logger = getLogger(__name__)


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

    typ = models.IntegerField(choices=OstreeObjectType.choices)
    checksum = models.CharField(max_length=64, db_index=True)
    relative_path = models.TextField(null=False)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        unique_together = [["checksum", "relative_path"]]


class OstreeCommit(Content):
    """A content model for an OSTree commit."""

    TYPE = "commit"

    parent_commit = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE)
    checksum = models.CharField(max_length=64, db_index=True)
    relative_path = models.TextField(null=False)
    objs = models.ManyToManyField(OstreeObject, through="OstreeCommitObject")

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        unique_together = [["checksum", "relative_path"]]


class OstreeRef(Content):
    """A content model for an OSTree head commit."""

    TYPE = "refs"
    repo_key_fields = ("name",)

    commit = models.ForeignKey(
        OstreeCommit, related_name="refs_commit", null=True, on_delete=models.CASCADE
    )
    name = models.CharField(max_length=255, db_index=True)
    relative_path = models.TextField(null=False)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        unique_together = [["name", "commit", "relative_path"]]


class OstreeCommitObject(models.Model):
    """Many-to-many relationship between commits and objects."""

    commit = models.ForeignKey(OstreeCommit, related_name="object_commit", on_delete=models.CASCADE)
    obj = models.ForeignKey(OstreeObject, related_name="commit_object", on_delete=models.CASCADE)

    class Meta:
        unique_together = [["commit", "obj"]]


class OstreeContent(Content):
    """Any type of content/object that is currently not tracked by separate means."""

    repo_key_fields = ("relative_path",)

    relative_path = models.TextField(null=False)
    digest = models.CharField(max_length=64, null=False)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        unique_together = ("relative_path", "digest")


class OstreeConfig(Content):
    """A content model for an OSTree repository configuration file."""

    TYPE = "config"
    repo_key_fields = ("relative_path",)

    sha256 = models.CharField(max_length=64, db_index=True)
    relative_path = models.TextField(null=False)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        unique_together = [["sha256", "relative_path"]]


class OstreeSummary(Content):
    """A content model for an OSTree summary file."""

    TYPE = "summary"
    repo_key_fields = ("relative_path",)

    sha256 = models.CharField(max_length=64, db_index=True)
    relative_path = models.TextField(null=False)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        unique_together = [["sha256", "relative_path"]]


class OstreeRemote(Remote, AutoAddObjPermsMixin):
    """A remote model for OSTree content."""

    TYPE = "ostree"

    depth = models.IntegerField(default=0)
    include_refs = ArrayField(models.CharField(max_length=255, null=True), null=True)
    exclude_refs = ArrayField(models.CharField(max_length=255, null=True), null=True)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        permissions = [
            ("manage_roles_ostreeremote", "Can manage roles on ostree remotes"),
        ]


class OstreeRepository(Repository, AutoAddObjPermsMixin):
    """A repository model for OSTree content."""

    TYPE = "ostree"

    CONTENT_TYPES = [
        OstreeCommit,
        OstreeRef,
        OstreeObject,
        OstreeConfig,
        OstreeSummary,
        OstreeContent,
    ]
    REMOTE_TYPES = [OstreeRemote]

    compute_delta = models.BooleanField(default=True)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        permissions = [
            ("sync_ostreerepository", "Can start a sync task"),
            ("modify_ostreerepository", "Can modify content of the repository"),
            ("manage_roles_ostreerepository", "Can manage roles on ostree repositories"),
            ("repair_ostreerepository", "Can repair repository versions"),
            ("import_commits_ostreerepository", "Can import commits into a repository"),
        ]

    def finalize_new_version(self, new_version):
        """Handle repository duplicates."""
        remove_duplicates(new_version)
        validate_duplicate_content(new_version)


class OstreeDistribution(Distribution, AutoAddObjPermsMixin):
    """A distribution model for OSTree content."""

    TYPE = "ostree"

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        permissions = [
            ("manage_roles_ostreedistribution", "Can manage roles on ostree distributions"),
        ]
