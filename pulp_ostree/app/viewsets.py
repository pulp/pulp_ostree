from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action

from pulpcore.plugin.viewsets import ReadOnlyContentViewSet, ContentFilter, NAME_FILTER_OPTIONS
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
            shared_resources=[remote],
            exclusive_resources=[repository],
            kwargs={
                "remote_pk": str(remote.pk),
                "repository_pk": str(repository.pk),
                "mirror": mirror,
            },
        )
        return core.OperationPostponedResponse(result, request)

    @extend_schema(
        description="Trigger an asynchronous task to create a new OSTree repository version.",
        summary="Import commits to a repository",
        responses={202: AsyncOperationResponseSerializer},
    )
    @action(detail=True, methods=["post"], serializer_class=serializers.OstreeRepoImportSerializer)
    def import_commits(self, request, pk):
        """Add new commits to a repository."""
        repository = self.get_object()

        serializer = serializers.OstreeRepoImportSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        artifact = serializer.validated_data["artifact"]
        repository_name = serializer.validated_data["repository_name"]
        ref = serializer.validated_data["ref"]
        parent_commit = serializer.validated_data["parent_commit"]

        async_result = dispatch(
            tasks.import_ostree_content,
            exclusive_resources=[artifact, repository],
            kwargs={
                "artifact_pk": str(artifact.pk),
                "repository_pk": str(repository.pk),
                "repository_name": repository_name,
                "ref": ref,
                "parent_commit": parent_commit,
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


class RefContentFilter(ContentFilter):
    """A filterset class for refs."""

    class Meta:
        model = models.OstreeRef
        fields = {"name": NAME_FILTER_OPTIONS}


class OstreeRefViewSet(ReadOnlyContentViewSet):
    """A ViewSet class for OSTree head commits."""

    endpoint_name = "refs"
    queryset = models.OstreeRef.objects.all()
    serializer_class = serializers.OstreeRefSerializer
    filterset_class = RefContentFilter


class CommitContentFilter(ContentFilter):
    """A filterset class for commits."""

    class Meta:
        model = models.OstreeCommit
        fields = {"checksum": ["exact"]}


class OstreeCommitViewSet(ReadOnlyContentViewSet):
    """A ViewSet class for OSTree commits."""

    endpoint_name = "commits"
    queryset = models.OstreeCommit.objects.all()
    serializer_class = serializers.OstreeCommitSerializer
    filterset_class = CommitContentFilter


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
