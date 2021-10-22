from gettext import gettext as _
from tarfile import is_tarfile

from django.urls import resolve
from rest_framework import serializers
from rest_framework_nested.relations import (
    NestedHyperlinkedIdentityField,
    NestedHyperlinkedRelatedField,
)
from rest_framework.utils.field_mapping import get_nested_relation_kwargs

from pulpcore.plugin import serializers as platform
from pulpcore.plugin.models import Artifact, Remote, RepositoryVersion
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
    parent_commit = serializers.CharField(
        required=False,
        help_text=_(
            "The checksum of a parent commit with which the content needs to be associated."
        ),
    )

    def validate(self, data):
        """Validate the passed tarball and optional ref attributes."""
        new_data = {}
        new_data.update(self.initial_data)

        self.validate_tarball(new_data)
        self.validate_ref_and_parent_commit(new_data)

        return new_data

    def validate_tarball(self, data):
        """Check if the artifact is a tarball."""
        artifact = NamedModelViewSet.get_resource(data["artifact"])
        if not is_tarfile(artifact.file.path):
            raise serializers.ValidationError(_("The artifact is not a tar archive file"))
        data["artifact"] = artifact

    def validate_ref_and_parent_commit(self, data):
        """Check if a user provided a ref and parent when adding commits to a repository."""
        ref = data.get("ref")
        parent_commit = data.get("parent_commit")

        if all([ref, parent_commit]) or not any([ref, parent_commit]):
            data["ref"] = ref
            data["parent_commit"] = parent_commit
        else:
            raise serializers.ValidationError(
                _("Both the parent commit and ref should be specified when adding new content")
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

    class Meta:
        fields = platform.RemoteSerializer.Meta.fields + ("depth",)
        model = models.OstreeRemote


class OstreeRepositorySerializer(platform.RepositorySerializer):
    """A Serializer class for an OSTree repository."""

    class Meta:
        fields = platform.RepositorySerializer.Meta.fields
        model = models.OstreeRepository


class NestedHyperlinkedModelSerializer(serializers.HyperlinkedModelSerializer):
    """
    A type of `ModelSerializer` that uses hyperlinked relationships with compound keys instead
    of primary key relationships.  Specifically:

    * A 'url' field is included instead of the 'id' field.
    * Relationships to other instances are hyperlinks, instead of primary keys.

    NOTE: this only works with DRF 3.1.0 and above.
    """

    parent_lookup_kwargs = {"parent_pk": "parent__pk"}

    serializer_url_field = NestedHyperlinkedIdentityField
    serializer_related_field = NestedHyperlinkedRelatedField

    def __init__(self, *args, **kwargs):
        """Initialize class-wide variables."""
        self.parent_lookup_kwargs = kwargs.pop("parent_lookup_kwargs", self.parent_lookup_kwargs)
        super(NestedHyperlinkedModelSerializer, self).__init__(*args, **kwargs)

    def build_url_field(self, field_name, model_class):
        """Return URL fields."""
        field_class, field_kwargs = super(NestedHyperlinkedModelSerializer, self).build_url_field(
            field_name, model_class
        )
        field_kwargs["parent_lookup_kwargs"] = self.parent_lookup_kwargs

        return field_class, field_kwargs

    def build_nested_field(self, field_name, relation_info, nested_depth):
        """
        Create nested fields for forward and reverse relationships.
        """

        class NestedSerializer(NestedHyperlinkedModelSerializer):
            class Meta:
                model = relation_info.related_model
                depth = nested_depth - 1
                fields = "__all__"

        field_class = NestedSerializer
        field_kwargs = get_nested_relation_kwargs(relation_info)

        return field_class, field_kwargs


class RepositoryAddRemoveContentSerializer(
    platform.ModelSerializer, NestedHyperlinkedModelSerializer
):
    """A serializer class for add/remove operations."""

    add_content_units = serializers.ListField(
        help_text=_(
            "A list of content units to add to a new repository version. This content is "
            "added after remove_content_units are removed."
        ),
        required=False,
    )
    remove_content_units = serializers.ListField(
        help_text=_(
            "A list of content units to remove from the latest repository version. "
            "You may also specify '*' as an entry to remove all content. This content is "
            "removed before add_content_units are added."
        ),
        required=False,
    )
    base_version = platform.RepositoryVersionRelatedField(
        required=False,
        help_text=_(
            "A repository version whose content will be used as the initial set of content "
            "for the new repository version"
        ),
    )

    def validate_remove_content_units(self, value):
        """Validate the passed content units."""
        if len(value) > 1 and "*" in value:
            raise serializers.ValidationError("Cannot supply content units and '*'.")
        return value

    class Meta:
        model = RepositoryVersion
        fields = ["add_content_units", "remove_content_units", "base_version"]


class OstreeRepositoryAddRemoveContentSerializer(RepositoryAddRemoveContentSerializer):
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
