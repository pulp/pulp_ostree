from gettext import gettext as _

from django_filters.filters import CharFilter
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.serializers import ValidationError

from pulpcore.plugin.viewsets import (
    ReadOnlyContentViewSet,
    ContentFilter,
    NAME_FILTER_OPTIONS,
    SingleArtifactContentUploadViewSet,
)
from pulpcore.plugin import viewsets as core
from pulpcore.plugin.models import RepositoryVersion
from pulpcore.plugin.actions import ModifyRepositoryActionMixin
from pulpcore.plugin.serializers import (
    AsyncOperationResponseSerializer,
    RepositoryAddRemoveContentSerializer,
    RepositorySyncURLSerializer,
)
from pulpcore.plugin.tasking import dispatch
from pulpcore.plugin.util import get_objects_for_user

from . import models, serializers, tasks


REPO_VIEW_PERM = "ostree.view_ostreerepository"


class OstreeRemoteViewSet(core.RemoteViewSet, core.RolesMixin):
    """A ViewSet class for OSTree remote repositories."""

    endpoint_name = "ostree"
    queryset = models.OstreeRemote.objects.all()
    serializer_class = serializers.OstreeRemoteSerializer
    queryset_filtering_required_permission = "ostree.view_ostreeremote"

    DEFAULT_ACCESS_POLICY = {
        "statements": [
            {
                "action": ["list", "my_permissions"],
                "principal": "authenticated",
                "effect": "allow",
            },
            {
                "action": ["create"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": "has_model_perms:ostree.add_ostreeremote",
            },
            {
                "action": ["retrieve"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": "has_model_or_obj_perms:ostree.view_ostreeremote",
            },
            {
                "action": ["update", "partial_update", "set_label", "unset_label"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": [
                    "has_model_or_obj_perms:ostree.change_ostreeremote",
                ],
            },
            {
                "action": ["destroy"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": [
                    "has_model_or_obj_perms:ostree.delete_ostreeremote",
                ],
            },
            {
                "action": ["list_roles", "add_role", "remove_role"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": ["has_model_or_obj_perms:ostree.manage_roles_ostreeremote"],
            },
        ],
        "creation_hooks": [
            {
                "function": "add_roles_for_object_creator",
                "parameters": {"roles": "ostree.ostreeremote_owner"},
            },
        ],
        "queryset_scoping": {"function": "scope_queryset"},
    }
    LOCKED_ROLES = {
        "ostree.ostreeremote_creator": ["ostree.add_ostreeremote"],
        "ostree.ostreeremote_owner": [
            "ostree.view_ostreeremote",
            "ostree.change_ostreeremote",
            "ostree.delete_ostreeremote",
            "ostree.manage_roles_ostreeremote",
        ],
        "ostree.ostreeremote_viewer": ["ostree.view_ostreeremote"],
    }


class OstreeRepositoryViewSet(core.RepositoryViewSet, ModifyRepositoryActionMixin, core.RolesMixin):
    """A ViewSet class for OSTree repositories."""

    endpoint_name = "ostree"
    queryset = models.OstreeRepository.objects.all()
    serializer_class = serializers.OstreeRepositorySerializer
    queryset_filtering_required_permission = "ostree.view_ostreerepository"

    DEFAULT_ACCESS_POLICY = {
        "statements": [
            {
                "action": ["list", "my_permissions"],
                "principal": "authenticated",
                "effect": "allow",
            },
            {
                "action": ["create"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": [
                    "has_model_perms:ostree.add_ostreerepository",
                    "has_remote_param_model_or_obj_perms:ostree.view_ostreeremote",
                ],
            },
            {
                "action": ["retrieve"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": "has_model_or_obj_perms:ostree.view_ostreerepository",
            },
            {
                "action": ["destroy"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": [
                    "has_model_or_obj_perms:ostree.delete_ostreerepository",
                ],
            },
            {
                "action": ["update", "partial_update", "set_label", "unset_label"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": [
                    "has_model_or_obj_perms:ostree.change_ostreerepository",
                    "has_remote_param_model_or_obj_perms:ostree.view_ostreeremote",
                ],
            },
            {
                "action": ["sync"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": [
                    "has_model_or_obj_perms:ostree.sync_ostreerepository",
                    "has_remote_param_model_or_obj_perms:ostree.view_ostreeremote",
                    "has_model_or_obj_perms:ostree.view_ostreerepository",
                ],
            },
            {
                "action": ["import_all", "import_commits"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": [
                    "has_model_or_obj_perms:ostree.import_commits_ostreerepository"
                    "has_model_or_obj_perms:ostree.view_ostreerepository",
                ],
            },
            {
                "action": ["modify"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": [
                    "has_model_or_obj_perms:ostree.modify_ostreerepository",
                ],
            },
            {
                "action": ["list_roles", "add_role", "remove_role"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": ["has_model_or_obj_perms:ostree.manage_roles_ostreerepository"],
            },
        ],
        "creation_hooks": [
            {
                "function": "add_roles_for_object_creator",
                "parameters": {"roles": "ostree.ostreerepository_owner"},
            },
        ],
        "queryset_scoping": {"function": "scope_queryset"},
    }
    LOCKED_ROLES = {
        "ostree.ostreerepository_creator": ["ostree.add_ostreerepository"],
        "ostree.ostreerepository_owner": [
            "ostree.view_ostreerepository",
            "ostree.change_ostreerepository",
            "ostree.delete_ostreerepository",
            "ostree.modify_ostreerepository",
            "ostree.sync_ostreerepository",
            "ostree.manage_roles_ostreerepository",
            "ostree.repair_ostreerepository",
            "ostree.import_commits_ostreerepository",
        ],
        "ostree.ostreerepository_viewer": ["ostree.view_ostreerepository"],
    }

    @extend_schema(
        description="Trigger an asynchronous task to sync content.",
        summary="Sync from remote",
        responses={202: AsyncOperationResponseSerializer},
    )
    @action(detail=True, methods=["post"], serializer_class=RepositorySyncURLSerializer)
    def sync(self, request, pk):
        """Dispatch a sync task."""
        repository = self.get_object()
        serializer = RepositorySyncURLSerializer(
            data=request.data, context={"request": request, "repository_pk": pk}
        )
        serializer.is_valid(raise_exception=True)
        remote = serializer.validated_data.get("remote", repository.remote)
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
        description="Trigger an asynchronous task to import all refs and commits to a repository.",
        summary="Import refs and commits to a repository",
        responses={202: AsyncOperationResponseSerializer},
    )
    @action(detail=True, methods=["post"], serializer_class=serializers.OstreeImportAllSerializer)
    def import_all(self, request, pk):
        """Import all refs and commits to a repository."""
        repository = self.get_object()

        serializer = serializers.OstreeImportAllSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        artifact = serializer.validated_data["artifact"]
        repository_name = serializer.validated_data["repository_name"]

        async_result = dispatch(
            tasks.import_all_refs_and_commits,
            exclusive_resources=[artifact, repository],
            kwargs={
                "artifact_pk": str(artifact.pk),
                "repository_pk": str(repository.pk),
                "repository_name": repository_name,
            },
        )
        return core.OperationPostponedResponse(async_result, request)

    @extend_schema(
        description="Trigger an asynchronous task to append child commits to a repository.",
        summary="Append child commits to a repository",
        responses={202: AsyncOperationResponseSerializer},
    )
    @action(
        detail=True,
        methods=["post"],
        serializer_class=serializers.OstreeImportCommitsToRefSerializer,
    )
    def import_commits(self, request, pk):
        """Append child commits to a repository."""
        repository = self.get_object()

        serializer = serializers.OstreeImportCommitsToRefSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        artifact = serializer.validated_data["artifact"]
        repository_name = serializer.validated_data["repository_name"]
        ref = serializer.validated_data["ref"]

        async_result = dispatch(
            tasks.import_child_commits,
            exclusive_resources=[artifact, repository],
            kwargs={
                "artifact_pk": str(artifact.pk),
                "repository_pk": str(repository.pk),
                "repository_name": repository_name,
                "ref": ref,
            },
        )
        return core.OperationPostponedResponse(async_result, request)

    @extend_schema(
        description="Trigger an asynchronous task to modify content.",
        summary="Modify repository",
        responses={202: AsyncOperationResponseSerializer},
    )
    @action(
        detail=True,
        methods=["post"],
        serializer_class=RepositoryAddRemoveContentSerializer,
    )
    def modify(self, request, pk):
        """Queues a task that adds and remove content units within a repository."""
        repository = self.get_object()
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        if "base_version" in request.data:
            base_version_pk = self.get_resource(request.data["base_version"], RepositoryVersion).pk
        else:
            base_version_pk = None

        task = dispatch(
            tasks.modify_content,
            exclusive_resources=[repository],
            kwargs={
                "repository_pk": pk,
                "base_version_pk": base_version_pk,
                "add_content_units": serializer.validated_data.get("add_content_units", []),
                "remove_content_units": serializer.validated_data.get("remove_content_units", []),
            },
        )
        return core.OperationPostponedResponse(task, request)

    def verify_content_units(self, content_units, all_content_units):
        """Verify referenced content units."""
        existing_content_units_pks = content_units.values_list("pk", flat=True)
        existing_content_units_pks = {str(pk) for pk in existing_content_units_pks}

        missing_pks = set(all_content_units.keys()) - existing_content_units_pks
        if missing_pks:
            missing_hrefs = [all_content_units[pk] for pk in missing_pks]
            raise ValidationError(
                _("Could not find the following content units: {}").format(missing_hrefs)
            )


class OstreeRepositoryVersionViewSet(core.RepositoryVersionViewSet):
    """A ViewSet class that represents a single OSTree repository version."""

    parent_viewset = OstreeRepositoryViewSet

    DEFAULT_ACCESS_POLICY = {
        "statements": [
            {
                "action": ["list", "retrieve"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": "has_repository_model_or_obj_perms:ostree.view_ostreerepository",
            },
            {
                "action": ["destroy"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": [
                    "has_repository_model_or_obj_perms:ostree.delete_ostreerepository",
                    "has_repository_model_or_obj_perms:ostree.delete_ostreerepository_version",
                    "has_repository_model_or_obj_perms:ostree.view_ostreerepository",
                ],
            },
            {
                "action": ["repair"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": [
                    "has_repository_model_or_obj_perms:ostree.repair_ostreerepository",
                ],
            },
        ],
    }


class OstreeDistributionViewSet(core.DistributionViewSet, core.RolesMixin):
    """A ViewSet class for OSTree distributions."""

    endpoint_name = "ostree"
    queryset = models.OstreeDistribution.objects.all()
    serializer_class = serializers.OstreeDistributionSerializer
    queryset_filtering_required_permission = "ostree.view_ostreedistribution"

    DEFAULT_ACCESS_POLICY = {
        "statements": [
            {
                "action": ["list", "my_permissions"],
                "principal": "authenticated",
                "effect": "allow",
            },
            {
                "action": ["create"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": [
                    "has_model_perms:ostree.add_ostreedistribution",
                    "has_repo_or_repo_ver_param_model_or_obj_perms:" "ostree.view_ostreerepository",
                    "has_publication_param_model_or_obj_perms:ostree.view_ostreepublication",
                ],
            },
            {
                "action": ["retrieve"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": "has_model_or_obj_perms:ostree.view_ostreedistribution",
            },
            {
                "action": ["update", "partial_update", "set_label", "unset_label"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": [
                    "has_model_or_obj_perms:ostree.change_ostreedistribution",
                    "has_repo_or_repo_ver_param_model_or_obj_perms:" "ostree.view_ostreerepository",
                    "has_publication_param_model_or_obj_perms:ostree.view_ostreepublication",
                ],
            },
            {
                "action": ["destroy"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": [
                    "has_model_or_obj_perms:ostree.delete_ostreedistribution",
                ],
            },
            {
                "action": ["list_roles", "add_role", "remove_role"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": ["has_model_or_obj_perms:ostree.manage_roles_ostreedistribution"],
            },
        ],
        "creation_hooks": [
            {
                "function": "add_roles_for_object_creator",
                "parameters": {"roles": "ostree.ostreedistribution_owner"},
            },
        ],
        "queryset_scoping": {"function": "scope_queryset"},
    }
    LOCKED_ROLES = {
        "ostree.ostreedistribution_creator": ["ostree.add_ostreedistribution"],
        "ostree.ostreedistribution_owner": [
            "ostree.view_ostreedistribution",
            "ostree.change_ostreedistribution",
            "ostree.delete_ostreedistribution",
            "ostree.manage_roles_ostreedistribution",
        ],
        "ostree.ostreedistribution_viewer": ["ostree.view_ostreedistribution"],
    }


class OstreeRefFilter(ContentFilter):
    """A filterset class for refs."""

    checksum = CharFilter(field_name="commit__checksum")

    class Meta:
        model = models.OstreeRef
        fields = {"name": NAME_FILTER_OPTIONS}


class OstreeContentQuerySetMixin:
    """
    A mixin that filters content units based on their object-level permissions.
    """

    def _scope_repos_by_repo_version(self, repo_version_href):
        repo_version = core.NamedModelViewSet.get_resource(repo_version_href, RepositoryVersion)
        repo = repo_version.repository.cast()

        has_model_perm = self.request.user.has_perm(REPO_VIEW_PERM)
        has_object_perm = self.request.user.has_perm(REPO_VIEW_PERM, repo)

        if has_model_perm or has_object_perm:
            return [repo]
        else:
            return []

    def get_content_qs(self, qs):
        """
        Get a filtered QuerySet based on the current request's scope.

        This method returns only content units a user is allowed to preview. The user with the
        global import and mirror permissions (i.e., having the "ostree.view_ostreerepository")
        can see orphaned content too.
        """
        if self.request.user.has_perm(REPO_VIEW_PERM):
            return qs

        if repo_version_href := self.request.query_params.get("repository_version"):
            allowed_repos = self._scope_repos_by_repo_version(repo_version_href)
        else:
            allowed_repos = get_objects_for_user(
                self.request.user, REPO_VIEW_PERM, models.OstreeRepository.objects.all()
            ).only("pk")

        return qs.model.objects.filter(repositories__in=allowed_repos)


class OstreeRefViewSet(OstreeContentQuerySetMixin, ReadOnlyContentViewSet):
    """A ViewSet class for OSTree head commits."""

    endpoint_name = "refs"
    queryset = models.OstreeRef.objects.all()
    serializer_class = serializers.OstreeRefSerializer
    filterset_class = OstreeRefFilter

    DEFAULT_ACCESS_POLICY = {
        "statements": [
            {
                "action": ["list", "retrieve"],
                "principal": "authenticated",
                "effect": "allow",
            },
        ],
        "queryset_scoping": {"function": "get_content_qs"},
    }


class OstreeCommitFilter(ContentFilter):
    """A filterset class for commits."""

    class Meta:
        model = models.OstreeCommit
        fields = {"checksum": ["exact"]}


class OstreeCommitViewSet(OstreeContentQuerySetMixin, ReadOnlyContentViewSet):
    """A ViewSet class for OSTree commits."""

    endpoint_name = "commits"
    queryset = models.OstreeCommit.objects.all()
    serializer_class = serializers.OstreeCommitSerializer
    filterset_class = OstreeCommitFilter

    DEFAULT_ACCESS_POLICY = {
        "statements": [
            {
                "action": ["list", "retrieve"],
                "principal": "authenticated",
                "effect": "allow",
            },
        ],
        "queryset_scoping": {"function": "get_content_qs"},
    }


class OstreeObjectFilter(ContentFilter):
    """A filterset class for objects."""

    class Meta:
        model = models.OstreeObject
        fields = {"checksum": ["exact"]}


class OstreeObjectViewSet(OstreeContentQuerySetMixin, ReadOnlyContentViewSet):
    """A ViewSet class for OSTree objects (e.g., dirtree, dirmeta, file)."""

    endpoint_name = "objects"
    queryset = models.OstreeObject.objects.all()
    serializer_class = serializers.OstreeObjectSerializer
    filterset_class = OstreeObjectFilter

    DEFAULT_ACCESS_POLICY = {
        "statements": [
            {
                "action": ["list", "retrieve"],
                "principal": "authenticated",
                "effect": "allow",
            },
        ],
        "queryset_scoping": {"function": "get_content_qs"},
    }


class OstreeContentViewSet(OstreeContentQuerySetMixin, SingleArtifactContentUploadViewSet):
    """A ViewSet class for uncategorized content units (e.g., static deltas)."""

    endpoint_name = "content"
    queryset = models.OstreeContent.objects.all()
    serializer_class = serializers.OstreeContentSerializer

    DEFAULT_ACCESS_POLICY = {
        "statements": [
            {
                "action": ["list", "retrieve"],
                "principal": "authenticated",
                "effect": "allow",
            },
            {
                "action": ["create"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": [
                    "has_required_repo_perms_on_upload:ostree.modify_ostreerepository",
                    "has_upload_param_model_or_obj_perms:core.change_upload",
                ],
            },
        ],
        "queryset_scoping": {"function": "get_content_qs"},
    }


class OstreeConfigViewSet(OstreeContentQuerySetMixin, ReadOnlyContentViewSet):
    """A ViewSet class for OSTree repository configurations."""

    endpoint_name = "configs"
    queryset = models.OstreeConfig.objects.all()
    serializer_class = serializers.OstreeConfigSerializer

    DEFAULT_ACCESS_POLICY = {
        "statements": [
            {
                "action": ["list", "retrieve"],
                "principal": "authenticated",
                "effect": "allow",
            },
        ],
        "queryset_scoping": {"function": "get_content_qs"},
    }


class OstreeSummaryViewSet(OstreeContentQuerySetMixin, ReadOnlyContentViewSet):
    """A ViewSet class for OSTree repository summary files."""

    endpoint_name = "summaries"
    queryset = models.OstreeSummary.objects.all()
    serializer_class = serializers.OstreeSummarySerializer

    DEFAULT_ACCESS_POLICY = {
        "statements": [
            {
                "action": ["list", "retrieve"],
                "principal": "authenticated",
                "effect": "allow",
            },
        ],
        "queryset_scoping": {"function": "get_content_qs"},
    }
