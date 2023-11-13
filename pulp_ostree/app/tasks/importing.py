import os
import tarfile

from gettext import gettext

from asgiref.sync import sync_to_async

from pulpcore.plugin.models import Artifact, Repository, ProgressReport
from pulpcore.plugin.stages import (
    ArtifactSaver,
    ContentSaver,
    DeclarativeVersion,
    QueryExistingContents,
    ResolveContentFutures,
    Stage,
)
from pulpcore.plugin.sync import sync_to_async_iterable

from pulp_ostree.app.models import (
    OstreeCommit,
    OstreeRef,
    OstreeConfig,
    OstreeObject,
    OstreeObjectType,
    OstreeSummary,
)
from pulp_ostree.app.tasks.utils import copy_to_local_storage, get_checksum_filepath
from pulp_ostree.app.tasks.stages import OstreeAssociateContent, DeclarativeContentCreatorMixin

import gi

gi.require_version("OSTree", "1.0")
from gi.repository import Gio, GLib, OSTree  # noqa: E402: module level not at top of file


def import_all_refs_and_commits(artifact_pk, repository_pk, repository_name):
    """Import all ref and commits to an OSTree repository.

    Args:
        artifact_pk (str): The PK of an artifact that identifies a tarball.
        repository_pk (str): The repository PK.
        repository_name (str): The name of an OSTree repository (e.g., "repo").

    Raises:
        ValueError: If an OSTree repository could not be properly parsed or the specified ref
            does not exist.
    """
    tarball_artifact = Artifact.objects.get(pk=artifact_pk)
    repository = Repository.objects.get(pk=repository_pk)
    compute_delta = repository.cast().compute_delta
    first_stage = OstreeImportAllRefsFirstStage(
        tarball_artifact, repository_name, compute_delta, repository
    )
    dv = OstreeImportDeclarativeVersion(first_stage, repository)
    return dv.create()


def import_child_commits(artifact_pk, repository_pk, repository_name, ref):
    """Import child commits to a specific ref.

    Args:
        artifact_pk (str): The PK of an artifact that identifies a tarball.
        repository_pk (str): The repository PK.
        repository_name (str): The name of an OSTree repository (e.g., "repo").
        ref (str): The name of a ref object that points to the last commit.

    Raises:
        ValueError: If an OSTree repository could not be properly parsed or the specified ref
            does not exist.
    """
    tarball_artifact = Artifact.objects.get(pk=artifact_pk)
    repository = Repository.objects.get(pk=repository_pk)
    compute_delta = repository.cast().compute_delta
    first_stage = OstreeImportSingleRefFirstStage(
        tarball_artifact, repository_name, ref, compute_delta
    )
    dv = OstreeImportDeclarativeVersion(first_stage, repository)
    return dv.create()


class OstreeSingleRefParserMixin:
    """A mixin class that allows stages to share the same methods for parsing OSTree data."""

    async def parse_ref(self, name, ref_commit_checksum, has_referenced_parent=False):
        """Parse a single ref object with associated commits and other objects."""
        _, ref_commit, _ = self.repo.load_commit(ref_commit_checksum)
        relative_path = get_checksum_filepath(
            ref_commit_checksum, OstreeObjectType.OSTREE_OBJECT_TYPE_COMMIT
        )
        ref_path = os.path.join("refs/", "heads/", name)

        parent_checksum = OSTree.commit_get_parent(ref_commit)
        if not parent_checksum:
            # there are not any parent commits, return and continue parsing the next ref
            commit = OstreeCommit(checksum=ref_commit_checksum)
            commit_dc = self.create_dc(relative_path, commit)
            await self.put(commit_dc)

            await self.submit_related_objects(commit_dc)

            self.init_ref_object(name, ref_path, commit_dc)

            return

        checksum = ref_commit_checksum
        ref_commit = OstreeCommit(checksum=checksum)
        ref_commit_dc = self.create_dc(relative_path, ref_commit)
        self.commit_dcs.append(ref_commit_dc)

        self.init_ref_object(name, ref_path, ref_commit_dc)

        try:
            _, parent_commit, _ = self.repo.load_commit(parent_checksum)
        except GLib.Error:
            if has_referenced_parent:
                # the associated parent commit may not be present in the parsed tarball
                # and this state is still considered valid
                return parent_checksum, ref_commit_dc
            else:
                try:
                    parent_commit = await OstreeCommit.objects.aget(checksum=parent_checksum)
                except OstreeCommit.DoesNotExist:
                    raise ValueError(
                        gettext("The parent commit '{}' could not be loaded").format(
                            parent_checksum
                        )
                    )
                else:
                    await self.copy_from_storage_to_tmp(parent_commit, parent_commit.objs)
                    _, parent_commit, _ = self.repo.load_commit(parent_checksum)

        return await self.load_next_commits(parent_commit, parent_checksum, has_referenced_parent)

    async def load_next_commits(self, parent_commit, checksum, has_referenced_parent=False):
        """Queue next parent commits if exist."""
        relative_path = get_checksum_filepath(checksum, OstreeObjectType.OSTREE_OBJECT_TYPE_COMMIT)

        parent_checksum = OSTree.commit_get_parent(parent_commit)

        while parent_checksum:
            commit = OstreeCommit(checksum=checksum)
            commit_dc = self.create_dc(relative_path, commit)
            self.commit_dcs.append(commit_dc)

            checksum = parent_checksum
            relative_path = get_checksum_filepath(
                checksum, OstreeObjectType.OSTREE_OBJECT_TYPE_COMMIT
            )
            try:
                _, parent_commit, _ = self.repo.load_commit(parent_checksum)
            except GLib.Error:
                if has_referenced_parent:
                    # the associated parent commit may not be present in the parsed tarball
                    # and this state is still considered valid
                    return parent_checksum, commit_dc
                else:
                    raise ValueError(
                        gettext("The parent commit '{}' could not be loaded").format(
                            parent_checksum
                        )
                    )
            parent_checksum = OSTree.commit_get_parent(parent_commit)

        commit = OstreeCommit(checksum=checksum)
        commit_dc = self.create_dc(relative_path, commit)
        self.commit_dcs.append(commit_dc)

        await self.put(commit_dc)
        await self.submit_related_objects(commit_dc)

        await self.submit_previous_commits_and_related_objects()

    async def copy_from_storage_to_tmp(self, parent_commit, objs):
        file_path = os.path.join(self.repo_path, parent_commit.relative_path)
        commit_file = await parent_commit._artifacts.aget()
        copy_to_local_storage(commit_file.file, file_path)

        async for obj in objs.all():
            file_path = os.path.join(self.repo_path, obj.relative_path)
            # TODO: handle missing artifacts, if any (attached to on_demand syncing);
            #   usually, imported repositories contain all the content
            obj_file = await obj._artifacts.aget()
            copy_to_local_storage(obj_file.file, file_path)


class OstreeImportStage(Stage):
    """A stage generalizing the common methods for initializing an OSTree repository."""

    def __init__(self, repo_name):
        """Initialize class variables that are common for tasks that import OSTree content."""
        super().__init__()

        self.repo_name = repo_name.lstrip("/")
        self.repo = None
        self.repo_path = None

        self.commit_dcs = []
        self.refs_dcs = []

    def init_repository(self):
        """Initialize new OSTree repository objects."""
        self.repo_path = os.path.join(os.getcwd(), self.repo_name)

        self.repo = OSTree.Repo.new(Gio.File.new_for_path(self.repo_path))

        try:
            self.repo.open()
        except GLib.Error:
            raise ValueError(
                gettext("An invalid path to the repository provided: {}").format(self.repo_name)
            )


class OstreeImportSingleRefFirstStage(
    DeclarativeContentCreatorMixin, OstreeSingleRefParserMixin, OstreeImportStage
):
    """A first stage of the OSTree importing pipeline that appends child commits to a repository."""

    def __init__(self, tarball_artifact, repo_name, ref, compute_delta):
        """Initialize class variables used for parsing OSTree objects."""
        super().__init__(repo_name)
        self.tarball_artifact = tarball_artifact
        self.ref = ref
        self.compute_delta = compute_delta

        self.create_object_dc_func = self.create_dc

    async def run(self):
        """Create OSTree content units and associate them with the parent commit."""
        with tarfile.open(fileobj=self.tarball_artifact.file) as tar:
            async with ProgressReport(
                message="Adding the child commits", code="adding.commits", total=1
            ) as pb:
                tar.extractall(path=os.getcwd())
                self.init_repository()

                last_commit_dc = None
                _, refs = self.repo.list_refs()
                for name, ref_commit_checksum in refs.items():
                    if self.ref == name:
                        parsed_result = await self.parse_ref(
                            name, ref_commit_checksum, has_referenced_parent=True
                        )
                        if parsed_result is None:
                            raise ValueError(
                                gettext(
                                    "The provided ref does not exist in the repository yet. "
                                    "Try importing first the whole repository, then additional "
                                    "commits."
                                )
                            )

                        parent_checksum, last_commit_dc = parsed_result
                        break

                if last_commit_dc is None:
                    raise ValueError(
                        gettext("An invalid ref name in the repository was specified: {}").format(
                            self.ref
                        )
                    )

                parent_commit = None

                try:
                    parent_commit = await OstreeCommit.objects.aget(checksum=parent_checksum)
                except OstreeCommit.DoesNotExist:
                    pass
                else:
                    last_commit_dc.extra_data["parent_commit"] = parent_commit
                    await self.put(last_commit_dc)
                    await self.submit_related_objects(last_commit_dc)

                await self.submit_previous_commits_and_related_objects()

                if self.compute_delta:
                    num_of_parsed_commits = len(self.commit_dcs)

                    # ensure there are at least two commits we can compute the static delta between.
                    if parent_commit and num_of_parsed_commits == 1:
                        await self.copy_from_storage_to_tmp(parent_commit, parent_commit.objs)
                        await self.compute_static_delta(ref_commit_checksum, parent_commit.checksum)
                    elif num_of_parsed_commits >= 2:
                        # the latest 2 commits are already present in the temporary repo; so,
                        # there is no need to copy files from the storage
                        ref_parent_commit_checksum = self.commit_dcs[1].content.checksum
                        await self.compute_static_delta(
                            ref_commit_checksum, ref_parent_commit_checksum
                        )

                await pb.aincrement()

            await self.submit_ref_objects()

            self.repo.regenerate_summary()
            await self.submit_metafile_object("summary", OstreeSummary())


class OstreeImportAllRefsFirstStage(
    DeclarativeContentCreatorMixin, OstreeSingleRefParserMixin, OstreeImportStage
):
    """A first stage of the OSTree importing pipeline that handles creation of content units."""

    def __init__(self, tarball_artifact, repo_name, compute_delta, repository):
        """Initialize class variables used for parsing OSTree objects."""
        super().__init__(repo_name)
        self.tarball_artifact = tarball_artifact
        self.compute_delta = compute_delta
        self.repository = repository

        self.create_object_dc_func = self.create_dc

    async def run(self):
        """Create OSTree content units and declare relations between them."""
        with tarfile.open(fileobj=self.tarball_artifact.file) as tar:
            async with ProgressReport(
                message="Committing the tarball", code="committing.tarball", total=1
            ) as pb:
                tar.extractall(path=os.getcwd())
                self.init_repository()

                await self.submit_metafile_object("config", OstreeConfig())

                _, refs = self.repo.list_refs()
                for name, ref_commit_checksum in refs.items():
                    parsed_result = await self.parse_ref(name, ref_commit_checksum)

                    if parsed_result is None:
                        continue

                    if self.compute_delta:
                        num_of_parsed_commits = len(self.commit_dcs)

                        commit = await OstreeCommit.objects.select_related("parent_commit").aget(
                            checksum=ref_commit_checksum
                        )
                        parent_commit = commit.parent_commit
                        if parent_commit and num_of_parsed_commits == 1:
                            await self.copy_from_storage_to_tmp(parent_commit, parent_commit.objs)
                            await self.compute_static_delta(
                                ref_commit_checksum, parent_commit.checksum
                            )
                        elif num_of_parsed_commits >= 2:
                            # the latest 2 commits are already present in the temporary repo; so,
                            # there is no need to copy files from the storage
                            ref_parent_commit_checksum = self.commit_dcs[1].content.checksum
                            await self.compute_static_delta(
                                ref_commit_checksum, ref_parent_commit_checksum
                            )

                await pb.aincrement()

            await self.submit_ref_objects()

            latest_version = await self.repository.alatest_version()

            # consider and copy already uploaded refs to correctly regenerate the summary; skip
            # refs there were just added to the repository as new content
            refs = await sync_to_async(latest_version.get_content(OstreeRef.objects).exclude)(
                name__in=(dc.content.name for dc in self.refs_dcs)
            )
            async for ref in refs:
                file_path = os.path.join(self.repo_path, "refs", "heads", ref.name)
                ref_file = await ref._artifacts.aget()
                copy_to_local_storage(ref_file.file, file_path)

                commit = await OstreeCommit.objects.aget(refs_commit=ref)
                await self.copy_from_storage_to_tmp(commit, OstreeObject.objects.none())

            self.repo.regenerate_summary()
            await self.submit_metafile_object("summary", OstreeSummary())


class QueryExistingArtifactsOstree(Stage):
    """A customized version of the QueryExistingArtifacts stage comparing just sha256 digests."""

    async def run(self):
        """Compare existing artifacts by leveraging dictionary access."""
        async for batch in self.batches():
            artifacts_digests = []

            for d_content in batch:
                d_artifact = d_content.d_artifacts[0]
                if d_artifact.artifact._state.adding:
                    digest_value = d_artifact.artifact.sha256
                    artifacts_digests.append(digest_value)

            query_params = {
                "sha256__in": artifacts_digests,
                "pulp_domain": self.domain,
            }

            existing_artifacts_qs = Artifact.objects.filter(**query_params)
            await sync_to_async(existing_artifacts_qs.touch)()

            d = {}
            async for result in sync_to_async_iterable(existing_artifacts_qs):
                d[result.sha256] = result

            for d_content in batch:
                d_artifact = d_content.d_artifacts[0]
                artifact_digest = d_artifact.artifact.sha256
                m = d.get(artifact_digest)
                if m:
                    d_artifact.artifact = m

            for d_content in batch:
                await self.put(d_content)


class OstreeImportDeclarativeVersion(DeclarativeVersion):
    """A customized DeclarativeVersion class that creates a pipeline for the OSTree import."""

    def pipeline_stages(self, new_version):
        """Build a list of stages."""
        pipeline = [
            self.first_stage,
            QueryExistingArtifactsOstree(),
            ArtifactSaver(),
            QueryExistingContents(),
            ContentSaver(),
            ResolveContentFutures(),
            OstreeAssociateContent(),
        ]

        return pipeline
