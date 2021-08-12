from gettext import gettext as _
from tarfile import is_tarfile

from rest_framework import serializers

from pulpcore.plugin import serializers as platform
from pulpcore.plugin.models import Artifact, Remote
from pulpcore.plugin.viewsets import NamedModelViewSet

from . import models


class OstreeRepoUploadSerializer(serializers.Serializer):
    """A Serializer class for uploading tarballs to a Pulp OSTree repository."""

    artifact = platform.RelatedField(
        many=False,
        lookup_field="pk",
        view_name="artifacts-detail",
        queryset=Artifact.objects.all(),
        help_text=_("Artifact representing an OSTree commit."),
    )
    repository_name = serializers.CharField()

    def validate(self, data):
        """Check if the uploaded artifact is a tarball."""
        new_data = {}
        new_data.update(self.initial_data)

        artifact = NamedModelViewSet.get_resource(new_data["artifact"])
        if not is_tarfile(artifact.file.path):
            raise serializers.ValidationError(_("The uploaded artifact is not a tar archive file"))
        new_data["artifact"] = artifact

        return new_data


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

    class Meta:
        fields = platform.SingleArtifactContentSerializer.Meta.fields + (
            "parent_commit",
            "checksum",
        )
        model = models.OstreeCommit


class OstreeRefsHeadSerializer(platform.SingleArtifactContentSerializer):
    """A Serializer class for OSTree head commits."""

    commit = platform.DetailRelatedField(
        many=False,
        view_name="ostree-commits-detail",
        queryset=models.OstreeCommit.objects.all(),
    )
    name = serializers.CharField()

    class Meta:
        fields = platform.SingleArtifactContentSerializer.Meta.fields + ("commit", "name")
        model = models.OstreeRefsHead


class OstreeObjectSerializer(platform.SingleArtifactContentSerializer):
    """A Serializer class for OSTree objects (e.g., dirtree, dirmeta, file)."""

    commit = platform.DetailRelatedField(
        many=False,
        view_name="ostree-commits-detail",
        queryset=models.OstreeCommit.objects.all(),
    )
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
            "commit",
            "checksum",
            "typ",
        )
        model = models.OstreeObject


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
        on_demand - Only commits, dirtrees, and refs heads are downloaded. Other OSTree objects
                    are not downloaded until they are requested for the first time by a client.
        """,
        choices=[Remote.IMMEDIATE, Remote.ON_DEMAND],
        default=Remote.IMMEDIATE,
    )

    class Meta:
        fields = platform.RemoteSerializer.Meta.fields + ("depth",)
        model = models.OstreeRemote


class OstreeRepositorySerializer(platform.RepositorySerializer):
    """A Serializer class for an OSTree repository."""

    class Meta:
        fields = platform.RepositorySerializer.Meta.fields
        model = models.OstreeRepository


class OstreeDistributionSerializer(platform.DistributionSerializer):
    """A Serializer class for an OSTree distribution."""

    repository_version = platform.RepositoryVersionRelatedField(
        required=False, help_text=_("RepositoryVersion to be served"), allow_null=True
    )

    class Meta:
        fields = platform.DistributionSerializer.Meta.fields + ("repository_version",)
        model = models.OstreeDistribution
