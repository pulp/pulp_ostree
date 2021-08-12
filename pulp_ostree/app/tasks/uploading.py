import os
import tarfile

from gettext import gettext

from pulpcore.plugin.models import Artifact, Repository, ProgressReport
from pulpcore.plugin.stages import (
    ArtifactSaver,
    ContentSaver,
    DeclarativeVersion,
    QueryExistingArtifacts,
    QueryExistingContents,
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


def import_ostree_repository(artifact_pk, repository_pk, repository_name):
    """Upload content to an OSTree repository.

    Args:
        artifact_pk (str): The PK of an artifact that identifies an uploaded tarball.
        repository_pk (str): The repository PK.
        repository_name (str): The name of an OSTree repository (e.g., "repo")

    Raises:
        ValueError: If an OSTree repository could not be properly parsed.
    """
    tarball_artifact = Artifact.objects.get(pk=artifact_pk)
    repository = Repository.objects.get(pk=repository_pk)

    first_stage = OstreeUploadFirstStage(tarball_artifact, repository_name)
    dv = OstreeUploadDeclarativeVersion(first_stage, repository)
    return dv.create()


class OstreeUploadFirstStage(DeclarativeContentCreatorMixin, Stage):
    """A first stage of the OSTree uploading pipeline that handles creation of content units."""

    def __init__(self, tarball_artifact, repository_name):
        """Initialize class variables used for parsing OSTree objects."""
        super().__init__()
        self.tarball_artifact = tarball_artifact

        self.repo_name = repository_name
        self.repo = None
        self.repo_path = None

        self.create_object_dc_func = self.create_dc

    async def run(self):
        """Create OSTree content units and declare relations between them."""
        with tarfile.open(self.tarball_artifact.file.path) as tar, ProgressReport(
            message="Committing the tarball", code="committing.tarball", total=1
        ) as pb:
            tar.extractall(path=os.getcwd())
            self.init_repository()

            await self.submit_metafile_object("config", OstreeConfig())

            _, refs = self.repo.list_refs()
            for name, ref_commit_checksum in refs.items():
                _, ref_commit, _ = self.repo.load_commit(ref_commit_checksum)
                relative_path = get_checksum_filepath(
                    ref_commit_checksum, OstreeObjectType.OSTREE_OBJECT_TYPE_COMMIT
                )
                refshead_path = os.path.join("refs/", "heads/", name)

                parent_checksum = OSTree.commit_get_parent(ref_commit)
                if not parent_checksum:
                    # there are not any parent commits, continue parsing the next head branch
                    commit = OstreeCommit(checksum=ref_commit_checksum)
                    commit_dc = self.create_dc(relative_path, commit)
                    await self.put(commit_dc)

                    await self.submit_related_objects(commit)

                    await self.submit_refshead_object(name, refshead_path, commit)

                    continue

                checksum = ref_commit_checksum
                headrefs_commit = OstreeCommit(checksum=checksum)
                headrefs_commit_dc = self.create_dc(relative_path, headrefs_commit)
                commit_dcs = [headrefs_commit_dc]

                checksum = parent_checksum
                relative_path = get_checksum_filepath(
                    checksum, OstreeObjectType.OSTREE_OBJECT_TYPE_COMMIT
                )
                _, parent_commit, _ = self.repo.load_commit(checksum)
                parent_checksum = OSTree.commit_get_parent(parent_commit)

                while parent_checksum:
                    commit = OstreeCommit(checksum=checksum)
                    commit_dc = self.create_dc(relative_path, commit)
                    commit_dcs.append(commit_dc)

                    checksum = parent_checksum
                    relative_path = get_checksum_filepath(
                        checksum, OstreeObjectType.OSTREE_OBJECT_TYPE_COMMIT
                    )
                    _, parent_commit, _ = self.repo.load_commit(checksum)
                    parent_checksum = OSTree.commit_get_parent(parent_commit)

                commit = OstreeCommit(checksum=checksum)
                commit_dc = self.create_dc(relative_path, commit)
                commit_dcs.append(commit_dc)

                await self.put(commit_dc)
                await self.submit_related_objects(commit)

                await self.submit_previous_commits_and_related_objects(commit_dcs)

                await self.submit_refshead_object(name, refshead_path, headrefs_commit_dc.content)

            pb.increment()

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


class OstreeUploadDeclarativeVersion(DeclarativeVersion):
    """A customized DeclarativeVersion class that creates a pipeline for the OSTree upload."""

    def pipeline_stages(self, new_version):
        """Build a list of stages."""
        pipeline = [
            self.first_stage,
            QueryExistingArtifacts(),
            ArtifactSaver(),
            QueryExistingContents(),
            ContentSaver(),
            OstreeAssociateContent(),
        ]

        return pipeline
