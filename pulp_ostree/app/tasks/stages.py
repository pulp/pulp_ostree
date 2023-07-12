import os
import shutil
import tempfile

from asgiref.sync import sync_to_async

from pulpcore.plugin.models import Artifact
from pulpcore.plugin.stages import (
    DeclarativeArtifact,
    DeclarativeContent,
    Stage,
)

from pulp_ostree.app.models import (
    OstreeCommit,
    OstreeContent,
    OstreeObject,
    OstreeRef,
    OstreeCommitObject,
)
from pulp_ostree.app.tasks.utils import compute_hash, get_checksum_filepath

import gi

gi.require_version("OSTree", "1.0")
from gi.repository import GLib, OSTree  # noqa: E402: module level not at top of file


class DeclarativeContentCreatorMixin:
    """A mixin class that defines basic methods for creating declarative content."""

    async def submit_related_objects(self, commit_dc):
        """Queue DeclarativeContent objects describing standard OSTree objects (e.g., dirtree)."""
        _, related_objects = self.repo.traverse_commit(commit_dc.content.checksum, maxdepth=0)
        for obj_checksum, obj_type in related_objects.values():
            if obj_checksum == commit_dc.content.checksum:
                continue

            obj = OstreeObject(typ=obj_type, checksum=obj_checksum)
            obj_relative_path = get_checksum_filepath(obj_checksum, obj_type)
            object_dc = self.create_object_dc_func(obj_relative_path, obj)
            object_dc.extra_data["commit_relation"] = await commit_dc.resolution()
            await self.put(object_dc)

    def init_ref_object(self, name, relative_path, commit_dc):
        """Initialize a DeclarativeContent object for a ref object."""
        ref = OstreeRef(name=name)
        ref_dc = self.create_dc(relative_path, ref)
        ref_dc.extra_data["ref_commit"] = commit_dc
        self.refs_dcs.append(ref_dc)

    async def submit_ref_objects(self):
        """Queue DeclarativeContent objects with proper reference to commits for all refs."""
        for ref_dc in self.refs_dcs:
            commit_dc = ref_dc.extra_data["ref_commit"]
            ref_dc.content.commit = await commit_dc.resolution()
            await self.put(ref_dc)

    async def submit_metafile_object(self, name, metafile_obj):
        """Queue a DeclarativeContent object for either summary or config."""
        metafile_dc = self.create_dc(name, metafile_obj)
        metafile_dc.content.sha256 = metafile_dc.d_artifacts[0].artifact.sha256
        await self.put(metafile_dc)

    async def submit_previous_commits_and_related_objects(self):
        """Associate parent and child commits while submitting all related objects to the queue."""
        for i in reversed(range(len(self.commit_dcs) - 1)):
            self.commit_dcs[i].extra_data["parent_commit"] = self.commit_dcs[i + 1].content

            await self.put(self.commit_dcs[i])
            await self.submit_related_objects(self.commit_dcs[i])

    def create_dc(self, relative_file_path, content):
        """Create a DeclarativeContent object describing a single OSTree object (e.g., commit)."""
        artifact = self.init_artifact(relative_file_path)

        content.relative_path = relative_file_path

        # DeclarativeArtifact requires a URL to be passed to its constructor even though it will
        # never be used; specifying the URL is a requirement for standard downloading pipeline that
        # we are not utilizing right now
        da = DeclarativeArtifact(
            artifact=artifact,
            url="hackathon",
            relative_path=relative_file_path,
        )

        return DeclarativeContent(content=content, d_artifacts=[da])

    def init_artifact(self, relative_file_path):
        """Initialize a new artifact from the passed filepath."""
        filepath = os.path.join(self.repo_path, relative_file_path)

        # we still need to keep the file in the local repository for further processing
        with tempfile.NamedTemporaryFile("wb", dir=".", delete=False) as new_file:
            with open(filepath, mode="rb") as f:
                shutil.copyfileobj(f, new_file)
                new_file.flush()

        return Artifact.init_and_validate(new_file.name)

    async def compute_static_delta(self, ref_commit_checksum, parent_checksum=None):
        if not self.commit_dcs:
            return

        if parent_checksum:
            from_ = parent_checksum
        else:
            from_ = self.commit_dcs[0].content.checksum

        # latest commit
        to = ref_commit_checksum

        self.repo.static_delta_generate(
            OSTree.StaticDeltaGenerateOpt.MAJOR, from_, to, None, GLib.Variant("a{sv}", None)
        )

        for dirpath, dirnames, filenames in os.walk(os.path.join(self.repo_path, "deltas/")):
            for filename in filenames:
                full_path = os.path.join(dirpath, filename)
                relative_path = os.path.relpath(full_path, self.repo_path)

                content = OstreeContent(relative_path=relative_path, digest=compute_hash(full_path))
                content_dc = self.create_dc(relative_path, content)
                await self.put(content_dc)


class OstreeAssociateContent(Stage):
    """A stage for creating associations between OSTree objects."""

    async def run(self):
        """Create relations between each OSTree object specified in DeclarativeContent objects."""
        async for batch in self.batches():
            updated_commits = []
            commits_to_objects = []
            for dc in batch:
                if dc.extra_data.get("parent_commit"):
                    updated_commits.append(self.associate_parent_commit(dc))
                elif dc.extra_data.get("commit_relation"):
                    commits_to_objects.append(self.associate_obj_commit(dc))

            await sync_to_async(OstreeCommit.objects.bulk_update)(
                objs=updated_commits, fields=["parent_commit"], batch_size=1000
            )
            await sync_to_async(OstreeCommitObject.objects.bulk_create)(
                objs=commits_to_objects, ignore_conflicts=True, batch_size=1000
            )

            for dc in batch:
                await self.put(dc)

    def associate_parent_commit(self, dc):
        """Assign the parent commit to its child commit."""
        parent_commit = dc.extra_data.get("parent_commit")
        dc.content.parent_commit = parent_commit
        return dc.content

    def associate_obj_commit(self, dc):
        """Assign the commit to its referenced object."""
        related_content = dc.extra_data.get("commit_relation")
        return OstreeCommitObject(commit=related_content, obj=dc.content)
