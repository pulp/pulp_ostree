import os
import tarfile

from gettext import gettext

from asgiref.sync import sync_to_async

from pulpcore.plugin.models import Artifact, Repository, ProgressReport
from pulpcore.plugin.stages import (
    ArtifactSaver,
    ContentSaver,
    DeclarativeVersion,
    QueryExistingArtifacts,
    QueryExistingContents,
    ResolveContentFutures,
    Stage,
)

from pulp_ostree.app.models import (
    OstreeCommit,
    OstreeConfig,
    OstreeObjectType,
)
from pulp_ostree.app.tasks.utils import get_checksum_filepath
from pulp_ostree.app.tasks.stages import OstreeAssociateContent, DeclarativeContentCreatorMixin

import gi

gi.require_version("OSTree", "1.0")
from gi.repository import Gio, GLib, OSTree  # noqa: E402: module level not at top of file


def import_ostree_content(
    artifact_pk, repository_pk, repository_name, ref=None, parent_commit=None
):
    """Import content to an OSTree repository.

    Args:
        artifact_pk (str): The PK of an artifact that identifies a tarball.
        repository_pk (str): The repository PK.
        repository_name (str): The name of an OSTree repository (e.g., "repo").
        ref (str): The name of a ref object that points to the last commit.
        parent_commit (str): The checksum of a parent commit to associate the content with.

    Raises:
        ValueError: If an OSTree repository could not be properly parsed or the specified ref
            does not exist.
    """
    tarball_artifact = Artifact.objects.get(pk=artifact_pk)
    repository = Repository.objects.get(pk=repository_pk)

    if ref and parent_commit:
        first_stage = OstreeImportSingleRefFirstStage(
            tarball_artifact, repository_name, parent_commit, ref
        )
    else:
        first_stage = OstreeImportAllBranchesFirstStage(tarball_artifact, repository_name)
    dv = OstreeImportDeclarativeVersion(first_stage, repository)
    return dv.create()


class OstreeSingleBranchParserMixin:
    """A mixin class that allows stages to share the same methods for parsing OSTree data."""

    async def parse_ref(self, name, ref_commit_checksum, ref_parent_checksum=None):
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

            return commit_dc

        checksum = ref_commit_checksum
        ref_commit = OstreeCommit(checksum=checksum)
        ref_commit_dc = self.create_dc(relative_path, ref_commit)
        self.commit_dcs.append(ref_commit_dc)

        self.init_ref_object(name, ref_path, ref_commit_dc)

        try:
            _, parent_commit, _ = self.repo.load_commit(parent_checksum)
        except GLib.Error:
            if ref_parent_checksum is not None and ref_parent_checksum == parent_checksum:
                return ref_commit_dc
            else:
                raise ValueError(
                    gettext("The parent commit '{}' could not be loaded").format(parent_checksum)
                )

        return await self.load_next_commits(parent_commit, parent_checksum)

    async def load_next_commits(self, parent_commit, checksum):
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
            _, parent_commit, _ = self.repo.load_commit(checksum)
            parent_checksum = OSTree.commit_get_parent(parent_commit)

        commit = OstreeCommit(checksum=checksum)
        commit_dc = self.create_dc(relative_path, commit)
        self.commit_dcs.append(commit_dc)

        await self.put(commit_dc)
        await self.submit_related_objects(commit_dc)

        await self.submit_previous_commits_and_related_objects()

        return commit_dc


class OstreeImportStage(Stage):
    """A stage generalizing the common methods for initializing an OSTree repository."""

    def __init__(self, repo_name):
        """Initialize class variables that are common for tasks that import OSTree content."""
        super().__init__()

        self.repo_name = repo_name
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
    DeclarativeContentCreatorMixin, OstreeSingleBranchParserMixin, OstreeImportStage
):
    """A first stage of the OSTree importing pipeline that appends child commits to a repository."""

    def __init__(self, tarball_artifact, repo_name, parent_commit, ref):
        """Initialize class variables used for parsing OSTree objects."""
        super().__init__(repo_name)
        self.tarball_artifact = tarball_artifact

        self.create_object_dc_func = self.create_dc

        self.parent_commit = parent_commit
        self.ref = ref

    async def run(self):
        """Create OSTree content units and associate them with the parent commit."""
        with tarfile.open(self.tarball_artifact.file.path) as tar:
            async with ProgressReport(
                message="Adding the child commits", code="adding.commits", total=1
            ) as pb:
                tar.extractall(path=os.getcwd())
                self.init_repository()

                last_commit_dc = None
                _, refs = self.repo.list_refs()
                for name, ref_commit_checksum in refs.items():
                    if self.ref == name:
                        last_commit_dc = await self.parse_ref(
                            name, ref_commit_checksum, self.parent_commit
                        )

                if last_commit_dc is None:
                    raise ValueError(
                        gettext("An invalid ref name in the repository was specified: {}").format(
                            self.ref
                        )
                    )

                try:
                    parent_commit = await sync_to_async(OstreeCommit.objects.get)(
                        checksum=self.parent_commit
                    )
                except OstreeCommit.DoesNotExist:
                    pass
                else:
                    last_commit_dc.extra_data["parent_commit"] = parent_commit
                    await self.put(last_commit_dc)
                    await self.submit_related_objects(last_commit_dc)

                await self.submit_ref_with_last_commit(last_commit_dc)

                await pb.aincrement()

            await self.submit_ref_objects()

    async def submit_ref_with_last_commit(self, commit_dc):
        """Update the corresponding ref with the newly imported head commit."""
        ref_relative_path = os.path.join("refs/heads/", self.ref)
        self.init_ref_object(self.ref, ref_relative_path, commit_dc)


class OstreeImportAllBranchesFirstStage(
    DeclarativeContentCreatorMixin, OstreeSingleBranchParserMixin, OstreeImportStage
):
    """A first stage of the OSTree importing pipeline that handles creation of content units."""

    def __init__(self, tarball_artifact, repo_name):
        """Initialize class variables used for parsing OSTree objects."""
        super().__init__(repo_name)
        self.tarball_artifact = tarball_artifact

        self.create_object_dc_func = self.create_dc

    async def run(self):
        """Create OSTree content units and declare relations between them."""
        with tarfile.open(self.tarball_artifact.file.path) as tar:
            async with ProgressReport(
                message="Committing the tarball", code="committing.tarball", total=1
            ) as pb:
                tar.extractall(path=os.getcwd())
                self.init_repository()

                await self.submit_metafile_object("config", OstreeConfig())

                _, refs = self.repo.list_refs()
                for name, ref_commit_checksum in refs.items():
                    await self.parse_ref(name, ref_commit_checksum)

                await pb.aincrement()

            await self.submit_ref_objects()


class OstreeImportDeclarativeVersion(DeclarativeVersion):
    """A customized DeclarativeVersion class that creates a pipeline for the OSTree import."""

    def pipeline_stages(self, new_version):
        """Build a list of stages."""
        pipeline = [
            self.first_stage,
            QueryExistingArtifacts(),
            ArtifactSaver(),
            QueryExistingContents(),
            ContentSaver(),
            ResolveContentFutures(),
            OstreeAssociateContent(),
        ]

        return pipeline
