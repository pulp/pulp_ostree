"""
Check `Plugin Writer's Guide`_ for more details.

.. _Plugin Writer's Guide:
    https://docs.pulpproject.org/pulpcore/plugins/plugin-writer/index.html
"""

from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action

from pulpcore.plugin.viewsets import RemoteFilter, ReadOnlyContentViewSet
from pulpcore.plugin import viewsets as core
from pulpcore.plugin.actions import ModifyRepositoryActionMixin
from pulpcore.plugin.serializers import (
    AsyncOperationResponseSerializer,
    RepositorySyncURLSerializer,
)
from pulpcore.plugin.tasking import dispatch

from . import models, serializers, tasks


class OstreeRemoteFilter(RemoteFilter):
    """
    A FilterSet for OstreeRemote.
    """

    class Meta:
        model = models.OstreeRemote
        fields = [
            # ...
        ]


class OstreeRemoteViewSet(core.RemoteViewSet):
    """
    A ViewSet for OstreeRemote.

    Similar to the OstreeContentViewSet above, define endpoint_name,
    queryset and serializer, at a minimum.
    """

    endpoint_name = "ostree"
    queryset = models.OstreeRemote.objects.all()
    serializer_class = serializers.OstreeRemoteSerializer


class OstreeRepositoryViewSet(core.RepositoryViewSet, ModifyRepositoryActionMixin):
    """
    A ViewSet for OstreeRepository.

    Similar to the OstreeContentViewSet above, define endpoint_name,
    queryset and serializer, at a minimum.
    """

    endpoint_name = "ostree"
    queryset = models.OstreeRepository.objects.all()
    serializer_class = serializers.OstreeRepositorySerializer

    # This decorator is necessary since a sync operation is asyncrounous and returns
    # the id and href of the sync task.
    @extend_schema(
        description="Trigger an asynchronous task to sync content.",
        summary="Sync from remote",
        responses={202: AsyncOperationResponseSerializer},
    )
    @action(detail=True, methods=["post"], serializer_class=RepositorySyncURLSerializer)
    def sync(self, request, pk):
        """
        Dispatches a sync task.
        """
        repository = self.get_object()
        serializer = RepositorySyncURLSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        remote = serializer.validated_data.get("remote")
        mirror = serializer.validated_data.get("mirror")

        result = dispatch(
            tasks.synchronize,
            [repository, remote],
            kwargs={
                "remote_pk": str(remote.pk),
                "repository_pk": str(repository.pk),
                "mirror": mirror,
            },
        )
        return core.OperationPostponedResponse(result, request)

    @extend_schema(
        description="Trigger an asynchronous task to create a new OSTree repository version.",
        summary="Create a new OSTree repository version",
        responses={202: AsyncOperationResponseSerializer},
    )
    @action(detail=True, methods=["post"], serializer_class=serializers.OstreeRepoUploadSerializer)
    def commit(self, request, pk):
        """Upload and parse a tarball consisting of one or more OSTree commits."""
        repository = self.get_object()

        serializer = serializers.OstreeRepoUploadSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        artifact = serializer.validated_data["artifact"]
        repository_name = serializer.validated_data["repository_name"]

        async_result = dispatch(
            tasks.import_ostree_repository,
            [artifact, repository],
            kwargs={
                "artifact_pk": str(artifact.pk),
                "repository_pk": str(repository.pk),
                "repository_name": repository_name,
            },
        )
        return core.OperationPostponedResponse(async_result, request)


class OstreeRepositoryVersionViewSet(core.RepositoryVersionViewSet):
    """
    A ViewSet for a OstreeRepositoryVersion represents a single
    Ostree repository version.
    """

    parent_viewset = OstreeRepositoryViewSet


class OstreePublicationViewSet(core.PublicationViewSet):
    """
    A ViewSet for OstreePublication.

    Similar to the OstreeContentViewSet above, define endpoint_name,
    queryset and serializer, at a minimum.
    """

    endpoint_name = "ostree"
    queryset = models.OstreePublication.objects.exclude(complete=False)
    serializer_class = serializers.OstreePublicationSerializer

    # This decorator is necessary since a publish operation is asyncrounous and returns
    # the id and href of the publish task.
    @extend_schema(
        description="Trigger an asynchronous task to publish content",
        responses={202: AsyncOperationResponseSerializer},
    )
    def create(self, request):
        """
        Publishes a repository.

        Either the ``repository`` or the ``repository_version`` fields can
        be provided but not both at the same time.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        repository_version = serializer.validated_data.get("repository_version")

        result = dispatch(
            tasks.publish,
            [repository_version.repository],
            kwargs={"repository_version_pk": str(repository_version.pk)},
        )
        return core.OperationPostponedResponse(result, request)


class OstreeDistributionViewSet(core.DistributionViewSet):
    """
    A ViewSet for OstreeDistribution.

    Similar to the OstreeContentViewSet above, define endpoint_name,
    queryset and serializer, at a minimum.
    """

    endpoint_name = "ostree"
    queryset = models.OstreeDistribution.objects.all()
    serializer_class = serializers.OstreeDistributionSerializer


class OstreeRefsHeadViewSet(ReadOnlyContentViewSet):
    """A ViewSet class for OSTree head commits."""

    endpoint_name = "refsheads"
    queryset = models.OstreeRefsHead.objects.all()
    serializer_class = serializers.OstreeRefsHeadSerializer


class OstreeCommitViewSet(ReadOnlyContentViewSet):
    """A ViewSet class for OSTree commits."""

    endpoint_name = "commits"
    queryset = models.OstreeCommit.objects.all()
    serializer_class = serializers.OstreeCommitSerializer


class OstreeObjectViewSet(ReadOnlyContentViewSet):
    """A ViewSet class for OSTree objects (e.g., dirtree, dirmeta, file)."""

    endpoint_name = "objects"
    queryset = models.OstreeObject.objects.all()
    serializer_class = serializers.OstreeObjectSerializer


class OstreeConfigViewSet(ReadOnlyContentViewSet):
    """A ViewSet class for OSTree repository configurations."""

    endpoint_name = "configs"
    queryset = models.OstreeConfig.objects.all()
    serializer_class = serializers.OstreeConfigSerializer
