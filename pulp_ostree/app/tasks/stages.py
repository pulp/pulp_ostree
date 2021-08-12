import os
import uuid

from django.db import IntegrityError

from pulpcore.plugin.models import Artifact
from pulpcore.plugin.stages import (
    DeclarativeArtifact,
    DeclarativeContent,
    Stage,
)

from pulp_ostree.app.models import OstreeCommit, OstreeObject, OstreeRefsHead
from pulp_ostree.app.tasks.utils import get_checksum_filepath


class DeclarativeContentCreatorMixin:
    """A mixin class that defines basic methods for creating declarative content."""

    async def submit_related_objects(self, commit):
        """Queue DeclarativeContent objects describing standard OSTree objects (e.g., dirtree)."""
        _, related_objects = self.repo.traverse_commit(commit.checksum, maxdepth=0)
        for obj_checksum, obj_type in related_objects.values():
            if obj_checksum == commit.checksum:
                continue

            obj = OstreeObject(commit=commit, typ=obj_type, checksum=obj_checksum)
            obj_relative_path = get_checksum_filepath(obj_checksum, obj_type)
            object_dc = self.create_object_dc_func(obj_relative_path, obj)
            await self.put(object_dc)

    async def submit_refshead_object(self, name, relative_path, commit):
        """Queue a DeclarativeContent object for a branch."""
        refshead = OstreeRefsHead(name=name)
        refshead_dc = self.create_dc(relative_path, refshead)
        refshead_dc.extra_data["head_commit"] = commit
        await self.put(refshead_dc)

    async def submit_metafile_object(self, name, metafile_obj):
        """Queue a DeclarativeContent object for either summary or config."""
        metafile_dc = self.create_dc(name, metafile_obj)
        metafile_dc.content.sha256 = metafile_dc.d_artifacts[0].artifact.sha256
        await self.put(metafile_dc)

    async def submit_previous_commits_and_related_objects(self, commit_dcs):
        """Associate parent and child commits while submitting all related objects to the queue."""
        for i in range(len(commit_dcs) - 1):
            commit_dcs[i].extra_data["parent_commit"] = commit_dcs[i + 1]

            await self.put(commit_dcs[i])
            await self.submit_related_objects(commit_dcs[i].content)

    def create_dc(self, relative_file_path, content):
        """Create a DeclarativeContent object describing a single OSTree object (e.g., commit)."""
        artifact = self.init_artifact(relative_file_path)

        publication_filepath = os.path.join(self.repo_name, relative_file_path)
        # DeclarativeArtifact requires a URL to be passed to its constructor even though it will
        # never be used; specifying the URL is a requirement for standard downloading pipeline that
        # we are not utilizing right now
        da = DeclarativeArtifact(
            artifact=artifact,
            url="hackathon",
            relative_path=publication_filepath,
        )

        return DeclarativeContent(content=content, d_artifacts=[da])

    def init_artifact(self, relative_file_path):
        """Initialize a new artifact from the passed filepath."""
        filepath = os.path.join(self.repo_path, relative_file_path)

        # this is a hack that prevents the pipeline to remove a temporary file which can be
        # referenced by multiple content units at the same time; in particular, this means that
        # one OSTree object (e.g., dirmeta, filez) is referenced by two different commits
        filepath_copy = filepath + str(uuid.uuid4())
        os.link(filepath, filepath_copy)

        return Artifact.init_and_validate(filepath_copy)


class OstreeAssociateContent(Stage):
    """A stage for creating associations between OSTree objects."""

    async def run(self):
        """Create relations between each OSTree object specified in DeclarativeContent objects."""
        async for batch in self.batches():
            updated_commits = []
            updated_refs = []
            for dc in batch:
                if dc.extra_data.get("parent_commit"):
                    updated_commits.append(self.associate_parent_commit(dc))
                elif dc.extra_data.get("head_commit"):
                    updated_refs.append(self.associate_head_commit(dc))

            OstreeCommit.objects.bulk_update(
                objs=updated_commits, fields=["parent_commit"], batch_size=1000
            )
            for dc in batch:
                await self.put(dc)

    def associate_parent_commit(self, dc):
        """Assign the parent commit to its child commit."""
        parent_commit_dc = dc.extra_data.get("parent_commit")
        dc.content.parent_commit = parent_commit_dc.content
        return dc.content

    def associate_head_commit(self, dc):
        """Assign the head commit to its branch."""
        related_commit = dc.extra_data.get("head_commit")
        dc.content.commit = related_commit
        try:
            dc.content.save()
        except (IntegrityError, ValueError):
            existing_head = OstreeRefsHead.objects.get(name=dc.content.name, commit=related_commit)
            dc.content.delete()
            dc.content = existing_head
