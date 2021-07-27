"""
Check `Plugin Writer's Guide`_ for more details.

.. _Plugin Writer's Guide:
    https://docs.pulpproject.org/pulpcore/plugins/plugin-writer/index.html
"""
from gettext import gettext as _
from tarfile import is_tarfile

from rest_framework import serializers

from pulpcore.plugin import serializers as platform
from pulpcore.plugin.models import Artifact
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
    checksum = serializers.CharField()

    class Meta:
        fields = platform.SingleArtifactContentSerializer.Meta.fields + ("commit", "checksum")
        model = models.OstreeObject


class OstreeConfigSerializer(platform.SingleArtifactContentSerializer):
    """A Serializer class for OSTree repository configuration files."""

    class Meta:
        fields = platform.SingleArtifactContentSerializer.Meta.fields
        model = models.OstreeConfig


class OstreeRemoteSerializer(platform.RemoteSerializer):
    """
    A Serializer for OstreeRemote.

    Add any new fields if defined on OstreeRemote.
    Similar to the example above, in OstreeContentSerializer.
    Additional validators can be added to the parent validators list

    For example::

    class Meta:
        validators = platform.RemoteSerializer.Meta.validators + [myValidator1, myValidator2]

    By default the 'policy' field in platform.RemoteSerializer only validates the choice
    'immediate'. To add on-demand support for more 'policy' options, e.g. 'streamed' or 'on_demand',
    re-define the 'policy' option as follows::

    policy = serializers.ChoiceField(
        help_text="The policy to use when downloading content. The possible values include: "
                  "'immediate', 'on_demand', and 'streamed'. 'immediate' is the default.",
        choices=models.Remote.POLICY_CHOICES,
        default=models.Remote.IMMEDIATE
    )
    """

    class Meta:
        fields = platform.RemoteSerializer.Meta.fields
        model = models.OstreeRemote


class OstreeRepositorySerializer(platform.RepositorySerializer):
    """
    A Serializer for OstreeRepository.

    Add any new fields if defined on OstreeRepository.
    Similar to the example above, in OstreeContentSerializer.
    Additional validators can be added to the parent validators list

    For example::

    class Meta:
        validators = platform.RepositorySerializer.Meta.validators + [myValidator1, myValidator2]
    """

    class Meta:
        fields = platform.RepositorySerializer.Meta.fields
        model = models.OstreeRepository


class OstreePublicationSerializer(platform.PublicationSerializer):
    """
    A Serializer for OstreePublication.

    Add any new fields if defined on OstreePublication.
    Similar to the example above, in OstreeContentSerializer.
    Additional validators can be added to the parent validators list

    For example::

    class Meta:
        validators = platform.PublicationSerializer.Meta.validators + [myValidator1, myValidator2]
    """

    class Meta:
        fields = platform.PublicationSerializer.Meta.fields
        model = models.OstreePublication


class OstreeDistributionSerializer(platform.DistributionSerializer):
    """
    A Serializer for OstreeDistribution.

    Add any new fields if defined on OstreeDistribution.
    Similar to the example above, in OstreeContentSerializer.
    Additional validators can be added to the parent validators list

    For example::

    class Meta:
        validators = platform.DistributionSerializer.Meta.validators + [
            myValidator1, myValidator2]
    """

    publication = platform.DetailRelatedField(
        required=False,
        help_text=_("Publication to be served"),
        view_name_pattern=r"publications(-.*/.*)?-detail",
        queryset=models.Publication.objects.exclude(complete=False),
        allow_null=True,
    )

    # uncomment these lines and remove the publication field if not using publications
    # repository_version = RepositoryVersionRelatedField(
    #     required=False, help_text=_("RepositoryVersion to be served"), allow_null=True
    # )

    class Meta:
        fields = platform.DistributionSerializer.Meta.fields + ("publication",)
        model = models.OstreeDistribution
