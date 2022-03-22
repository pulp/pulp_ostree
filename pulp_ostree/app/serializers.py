from gettext import gettext as _
from tarfile import is_tarfile

from django.urls import resolve
from rest_framework import serializers

from pulpcore.plugin import serializers as platform
from pulpcore.plugin.models import Artifact, Remote
from pulpcore.plugin.viewsets import NamedModelViewSet

from . import models


class OstreeRepoImportSerializer(serializers.Serializer):
    """A Serializer class for importing commits to a Pulp OSTree repository."""

    artifact = platform.RelatedField(
        many=False,
        lookup_field="pk",
        view_name="artifacts-detail",
        queryset=Artifact.objects.all(),
        help_text=_("An artifact representing OSTree content compressed as a tarball."),
    )
    repository_name = serializers.CharField(
        help_text=_("The name of a repository that contains the compressed OSTree content.")
    )

    ref = serializers.CharField(
        required=False,
        help_text=_("The name of a ref branch that holds the reference to the last commit."),
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
        if not is_tarfile(artifact.file.path):
            raise serializers.ValidationError(_("The artifact is not a tar archive file"))
        data["artifact"] = artifact


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

    class Meta:
        fields = platform.RepositorySerializer.Meta.fields
        model = models.OstreeRepository


class OstreeRepositoryAddRemoveContentSerializer(platform.RepositoryAddRemoveContentSerializer):
    """A Serializer class for modifying a repository from an existing repository."""

    ALLOWED_ADD_REMOVE_CONTENT_UNITS = [
        models.OstreeCommit,
        models.OstreeRef,
        models.OstreeConfig,
        models.OstreeSummary,
    ]

    def validate(self, data):
        """Validate content that will be added or removed from a repository."""
        data = super().validate(data)

        self.validate_units("add_content_units", data)
        self.validate_units("remove_content_units", data)

        return data

    def validate_units(self, units_modify_type, content):
        """Check if the content is in allowed content types (e.g., commit)."""
        if units_modify_type in content:
            for unit_href in content[units_modify_type]:
                unit_model = resolve(unit_href).func.cls.queryset.model
                if unit_model not in self.ALLOWED_ADD_REMOVE_CONTENT_UNITS:
                    raise serializers.ValidationError(
                        _(
                            "The unit {} is not allowed to be used in this endpoint".format(
                                unit_href
                            )
                        )
                    )


class OstreeDistributionSerializer(platform.DistributionSerializer):
    """A Serializer class for an OSTree distribution."""

    repository_version = platform.RepositoryVersionRelatedField(
        required=False, help_text=_("RepositoryVersion to be served"), allow_null=True
    )

    class Meta:
        fields = platform.DistributionSerializer.Meta.fields + ("repository_version",)
        model = models.OstreeDistribution
