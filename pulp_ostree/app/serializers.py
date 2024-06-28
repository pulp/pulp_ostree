import tarfile

from gettext import gettext as _

from rest_framework import serializers

from pulpcore.plugin import serializers as platform
from pulpcore.plugin.models import Artifact, Remote
from pulpcore.plugin.viewsets import NamedModelViewSet

from . import models


class OstreeImportAllSerializer(serializers.Serializer):
    """A Serializer class for importing all refs and commits to a repository."""

    artifact = platform.RelatedField(
        many=False,
        lookup_field="pk",
        view_name="artifacts-detail",
        queryset=Artifact.objects.all(),
        help_text=_("An artifact representing OSTree content compressed as a tarball."),
    )
    repository_name = serializers.CharField(
        help_text=_("The name of a repository that contains the compressed OSTree content."),
        allow_blank=True,
        default="",
    )

    def validate(self, data):
        """Validate the passed tarball and optional ref attributes."""
        new_data = {}
        new_data.update(self.initial_data)

        self.validate_tarball(new_data)

        return new_data

    def validate_tarball(self, data):
        """Check if the artifact is a tarball."""
        artifact = NamedModelViewSet.get_resource(data["artifact"])

        try:
            t = tarfile.open(fileobj=artifact.file)
        except tarfile.TarError:
            raise serializers.ValidationError(_("The artifact is not a tar archive file"))
        else:
            t.close()

        data["artifact"] = artifact


class OstreeImportCommitsToRefSerializer(OstreeImportAllSerializer):
    """A Serializer class for appending child commits to a repository."""

    ref = serializers.CharField(
        help_text=_("The name of a ref branch that holds the reference to the last commit."),
    )


class OstreeCommitSerializer(platform.SingleArtifactContentSerializer):
    """A Serializer class for OSTree commits."""

    parent_commit = platform.DetailRelatedField(
        many=False,
        view_name="ostree-commits-detail",
        queryset=models.OstreeCommit.objects.all(),
        allow_null=True,
        default=None,
    )
    checksum = serializers.CharField()
    objs = platform.DetailRelatedField(
        many=True,
        view_name="ostree-objects-detail",
        queryset=models.OstreeObject.objects.all(),
    )

    class Meta:
        fields = platform.SingleArtifactContentSerializer.Meta.fields + (
            "parent_commit",
            "checksum",
            "objs",
        )
        model = models.OstreeCommit


class OstreeRefSerializer(platform.SingleArtifactContentSerializer):
    """A Serializer class for OSTree head commits."""

    commit = platform.DetailRelatedField(
        many=False,
        view_name="ostree-commits-detail",
        queryset=models.OstreeCommit.objects.all(),
    )
    name = serializers.CharField()
    checksum = serializers.CharField(source="commit.checksum", read_only=True)

    class Meta:
        fields = platform.SingleArtifactContentSerializer.Meta.fields + (
            "commit",
            "checksum",
            "name",
        )
        model = models.OstreeRef


class OstreeObjectSerializer(platform.SingleArtifactContentSerializer):
    """A Serializer class for OSTree objects (e.g., dirtree, dirmeta, file)."""

    typ = serializers.IntegerField(
        help_text=_(
            """
            The type of an object. All values are described by the mapping declared at
            https://lazka.github.io/pgi-docs/OSTree-1.0/enums.html#OSTree.ObjectType
            """
        ),
    )
    checksum = serializers.CharField()

    class Meta:
        fields = platform.SingleArtifactContentSerializer.Meta.fields + (
            "checksum",
            "typ",
        )
        model = models.OstreeObject


class OstreeContentSerializer(platform.SingleArtifactContentSerializer):
    """A Serializer class for uncategorized content units (e.g., static deltas)."""

    relative_path = serializers.CharField()
    digest = serializers.CharField()

    class Meta:
        fields = platform.SingleArtifactContentSerializer.Meta.fields + (
            "relative_path",
            "digest",
        )
        model = models.OstreeContent


class OstreeConfigSerializer(platform.SingleArtifactContentSerializer):
    """A Serializer class for OSTree repository configuration files."""

    class Meta:
        fields = platform.SingleArtifactContentSerializer.Meta.fields
        model = models.OstreeConfig


class OstreeSummarySerializer(platform.SingleArtifactContentSerializer):
    """A Serializer class for an OSTree summary file."""

    class Meta:
        fields = platform.SingleArtifactContentSerializer.Meta.fields
        model = models.OstreeSummary


class OstreeRemoteSerializer(platform.RemoteSerializer):
    """A Serializer class for a remote OSTree repository."""

    depth = serializers.IntegerField(
        default=0,
        min_value=0,
        required=False,
        help_text=_("An option to specify how many commits to traverse."),
    )
    policy = serializers.ChoiceField(
        help_text="""
        immediate - All OSTree objects are downloaded and saved during synchronization.
        on_demand - Only commits, dirtrees, and refs are downloaded. Other OSTree objects are
                    not downloaded until they are requested for the first time by a client.
        """,
        choices=[Remote.IMMEDIATE, Remote.ON_DEMAND],
        default=Remote.IMMEDIATE,
    )
    include_refs = serializers.ListField(
        child=serializers.CharField(max_length=255),
        allow_null=True,
        required=False,
        help_text=_(
            """
            A list of refs to include during a sync.
            The wildcards *, ? are recognized.
            'include_refs' is evaluated before 'exclude_refs'.
            """
        ),
    )
    exclude_refs = serializers.ListField(
        child=serializers.CharField(max_length=255),
        allow_null=True,
        required=False,
        help_text=_(
            """
            A list of tags to exclude during a sync.
            The wildcards *, ? are recognized.
            'exclude_refs' is evaluated after 'include_refs'.
            """
        ),
    )

    class Meta:
        fields = platform.RemoteSerializer.Meta.fields + ("depth", "include_refs", "exclude_refs")
        model = models.OstreeRemote


class OstreeRepositorySerializer(platform.RepositorySerializer):
    """A Serializer class for an OSTree repository."""

    compute_delta = serializers.BooleanField(default=True)

    class Meta:
        fields = platform.RepositorySerializer.Meta.fields + ("compute_delta",)
        model = models.OstreeRepository


class OstreeDistributionSerializer(platform.DistributionSerializer):
    """A Serializer class for an OSTree distribution."""

    repository_version = platform.RepositoryVersionRelatedField(
        required=False, help_text=_("RepositoryVersion to be served"), allow_null=True
    )

    class Meta:
        fields = platform.DistributionSerializer.Meta.fields + ("repository_version",)
        model = models.OstreeDistribution
