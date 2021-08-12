from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action

from pulpcore.plugin.viewsets import ReadOnlyContentViewSet
from pulpcore.plugin import viewsets as core
from pulpcore.plugin.actions import ModifyRepositoryActionMixin
from pulpcore.plugin.serializers import (
    AsyncOperationResponseSerializer,
    RepositorySyncURLSerializer,
)
from pulpcore.plugin.tasking import dispatch

from . import models, serializers, tasks


class OstreeRemoteViewSet(core.RemoteViewSet):
    """A ViewSet class for OSTree remote repositories."""

    endpoint_name = "ostree"
    queryset = models.OstreeRemote.objects.all()
    serializer_class = serializers.OstreeRemoteSerializer


class OstreeRepositoryViewSet(core.RepositoryViewSet, ModifyRepositoryActionMixin):
    """A ViewSet class for OSTree repositories."""

    endpoint_name = "ostree"
    queryset = models.OstreeRepository.objects.all()
    serializer_class = serializers.OstreeRepositorySerializer

    @extend_schema(
        description="Trigger an asynchronous task to sync content.",
        summary="Sync from remote",
        responses={202: AsyncOperationResponseSerializer},
    )
    @action(detail=True, methods=["post"], serializer_class=RepositorySyncURLSerializer)
    def sync(self, request, pk):
        """Dispatch a sync task."""
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
    """A ViewSet class that represents a single OSTree repository version."""

    parent_viewset = OstreeRepositoryViewSet


class OstreeDistributionViewSet(core.DistributionViewSet):
    """A ViewSet class for OSTree distributions."""

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


class OstreeSummaryViewSet(ReadOnlyContentViewSet):
    """A ViewSet class for OSTree repository summary files."""

    endpoint_name = "summaries"
    queryset = models.OstreeSummary.objects.all()
    serializer_class = serializers.OstreeSummarySerializer
