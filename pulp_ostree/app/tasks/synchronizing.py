import os
import logging

from gettext import gettext as _
from pathlib import Path
from urllib.parse import urljoin

from pulpcore.plugin.models import Repository, ProgressReport, Artifact, Remote
from pulpcore.plugin.stages import (
    ArtifactSaver,
    ArtifactDownloader,
    ContentSaver,
    DeclarativeVersion,
    DeclarativeArtifact,
    DeclarativeContent,
    QueryExistingArtifacts,
    QueryExistingContents,
    RemoteArtifactSaver,
    ResolveContentFutures,
    Stage,
)

from pulp_ostree.app.models import (
    OstreeRemote,
    OstreeObjectType,
    OstreeCommit,
    OstreeConfig,
    OstreeSummary,
)
from pulp_ostree.app.tasks.stages import OstreeAssociateContent, DeclarativeContentCreatorMixin
from pulp_ostree.app.tasks.utils import get_checksum_filepath, bytes_to_checksum

import gi

gi.require_version("OSTree", "1.0")
from gi.repository import Gio, GLib, OSTree  # noqa: E402: module level not at top of file

log = logging.getLogger(__name__)


def synchronize(remote_pk, repository_pk, mirror):
    """
    Sync content from the remote repository.

    Create a new version of the repository that is synchronized with the remote.

    Args:
        remote_pk (str): The remote PK.
        repository_pk (str): The repository PK.
        mirror (bool): True for mirror mode, False for additive.

    Raises:
        ValueError: If the remote does not specify a URL to sync

    """
    remote = OstreeRemote.objects.get(pk=remote_pk)
    repository = Repository.objects.get(pk=repository_pk)

    if not remote.url:
        raise ValueError(_("A remote must have a url specified to synchronize."))

    deferred_download = remote.policy != Remote.IMMEDIATE
    first_stage = OstreeFirstStage(remote, deferred_download)
    dv = OstreeSyncDeclarativeVersion(first_stage, repository, mirror=mirror)
    return dv.create()


class OstreeFirstStage(DeclarativeContentCreatorMixin, Stage):
    """A first stage of the OSTree syncing pipeline that handles creation of content units."""

    def __init__(self, remote, deferred_download):
        """Initialize class variables used for parsing OSTree objects."""
        super().__init__()
        self.remote = remote
        self.deferred_download = deferred_download

        self.repo_name = remote.name
        self.repo = None
        self.repo_path = None

        self.commit_dcs = []
        self.refs_dcs = []

        self.create_object_dc_func = self.create_remote_artifact_dc

    async def run(self):
        """Create OSTree content units and declare relations between them."""
        async with ProgressReport(
            message="Parsing Metadata", code="sync.parsing_metadata", total=1
        ) as pb:
            self.init_repository()

            await self.submit_metafiles()

            _, refs = self.repo.remote_list_refs(self.repo_name)
            for name, _ in refs.items():
                ref_relative_path = os.path.join("refs/heads/", name)
                await self.download_remote_object(ref_relative_path)
                local_ref_path = os.path.join(self.repo_path, ref_relative_path)

                with open(local_ref_path, "r") as f:
                    ref_commit_checksum = f.read().strip()

                relative_path = get_checksum_filepath(
                    ref_commit_checksum, OstreeObjectType.OSTREE_OBJECT_TYPE_COMMIT
                )
                await self.download_remote_object(relative_path)

                _, ref_commit, _ = self.repo.load_commit(ref_commit_checksum)
                parent_checksum = OSTree.commit_get_parent(ref_commit)
                if not parent_checksum or self.remote.depth == 0:
                    # there are not any parent commits, continue parsing the next head branch
                    commit = OstreeCommit(checksum=ref_commit_checksum)
                    commit_dc = self.create_dc(relative_path, commit)
                    await self.put(commit_dc)

                    await self.submit_related_objects(commit_dc)

                    self.init_ref_object(name, ref_relative_path, commit_dc)

                    continue

                checksum = ref_commit_checksum
                ref_commit = OstreeCommit(checksum=checksum)
                ref_commit_dc = self.create_dc(relative_path, ref_commit)
                self.commit_dcs.append(ref_commit_dc)

                relative_path = get_checksum_filepath(
                    parent_checksum, OstreeObjectType.OSTREE_OBJECT_TYPE_COMMIT
                )
                await self.download_remote_object(relative_path)
                _, parent_commit, _ = self.repo.load_commit(parent_checksum)
                parent_checksum = OSTree.commit_get_parent(parent_commit)

                max_depth = self.remote.depth

                while parent_checksum and max_depth > 0:
                    commit = OstreeCommit(checksum=checksum)
                    commit_dc = self.create_dc(relative_path, commit)
                    self.commit_dcs.append(commit_dc)

                    checksum = parent_checksum
                    relative_path = get_checksum_filepath(
                        checksum, OstreeObjectType.OSTREE_OBJECT_TYPE_COMMIT
                    )
                    await self.download_remote_object(relative_path)
                    _, parent_commit, _ = self.repo.load_commit(checksum)
                    parent_checksum = OSTree.commit_get_parent(parent_commit)

                    max_depth -= 1

                commit = OstreeCommit(checksum=checksum)
                commit_dc = self.create_dc(relative_path, commit)
                self.commit_dcs.append(commit_dc)

                await self.put(commit_dc)
                await self.submit_related_objects(commit_dc)

                await self.submit_previous_commits_and_related_objects()

                self.init_ref_object(name, ref_relative_path, ref_commit_dc)

            await pb.aincrement()

        await self.submit_ref_objects()

    def init_repository(self):
        """Initialize a new OSTree repository object."""
        self.repo_path = os.path.join(os.getcwd(), "repo/")

        self.repo = OSTree.Repo.new(Gio.File.new_for_path(self.repo_path))
        self.repo.create(OSTree.RepoMode.ARCHIVE)

        no_gpg_verify = {"gpg-verify": GLib.Variant.new_boolean(False)}
        gpg_verify_variant = GLib.Variant("a{sv}", no_gpg_verify)
        self.repo.remote_add(self.repo_name, self.remote.url, gpg_verify_variant)

    async def submit_metafiles(self):
        """Download config and summary files and create DeclarativeContent objects for them."""
        await self.download_remote_object("config")
        await self.submit_metafile_object("config", OstreeConfig())

        await self.download_remote_object("summary")
        await self.submit_metafile_object("summary", OstreeSummary())

    async def download_remote_object(self, relative_path):
        """Download an object identified by the relative path with respect to the remote."""
        url = urljoin(self.remote.url, relative_path)
        downloader = self.remote.get_downloader(url=url)
        await downloader.run()

        full_path = Path(self.repo_path, relative_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        os.rename(downloader.path, full_path)

    def create_remote_artifact_dc(self, relative_path, content):
        """Create a declarative artifact that will have associated a remote artifact with it."""
        content_url = urljoin(self.remote.url, relative_path)
        publication_path = os.path.join(self.repo_name, relative_path)
        content.relative_path = publication_path

        da = DeclarativeArtifact(
            artifact=Artifact(),
            remote=self.remote,
            url=content_url,
            relative_path=publication_path,
            deferred_download=self.deferred_download,
        )

        return DeclarativeContent(content=content, d_artifacts=[da])

    async def submit_related_objects(self, commit_dc):
        """Queue related DeclarativeContent objects and additionally download dirtree metadata."""
        _, loaded_commit, _ = self.repo.load_commit(commit_dc.content.checksum)

        # it is necessary to download referenced dirtree objects; otherwise, the traversal cannot
        # be executed without errors; the traversing allows us to read all referenced checksums,
        # meaning that in the end we will have a list of all objects referenced by a single commit
        dirtree_checksum = bytes_to_checksum(loaded_commit[6])
        relative_path = get_checksum_filepath(
            dirtree_checksum, OstreeObjectType.OSTREE_OBJECT_TYPE_DIR_TREE
        )
        await self.download_remote_object(relative_path)

        _, dirtree_obj = self.repo.load_variant(OSTree.ObjectType.DIR_TREE, dirtree_checksum)
        subtree_checksums = {bytes_to_checksum(subtree[1]) for subtree in dirtree_obj[1]}
        await self.download_dirtrees(subtree_checksums)

        await super().submit_related_objects(commit_dc)

    async def download_dirtrees(self, subtree_checksums):
        """Recursively download dirtree objects and their sub-dirtree objects."""
        for subtree_checksum in subtree_checksums:
            relative_path = get_checksum_filepath(
                subtree_checksum, OstreeObjectType.OSTREE_OBJECT_TYPE_DIR_TREE
            )
            await self.download_remote_object(relative_path)

            _, dirtree_obj = self.repo.load_variant(OSTree.ObjectType.DIR_TREE, subtree_checksum)
            child_subtree_checksums = {bytes_to_checksum(subtree[1]) for subtree in dirtree_obj[1]}
            await self.download_dirtrees(child_subtree_checksums)


class OstreeSyncDeclarativeVersion(DeclarativeVersion):
    """A customized DeclarativeVersion class that creates a pipeline for the OSTree sync."""

    def pipeline_stages(self, new_version):
        """Build a list of stages."""
        pipeline = [
            self.first_stage,
            QueryExistingArtifacts(),
            ArtifactDownloader(),
            ArtifactSaver(),
            QueryExistingContents(),
            ContentSaver(),
            RemoteArtifactSaver(),
            ResolveContentFutures(),
            OstreeAssociateContent(),
        ]

        return pipeline
