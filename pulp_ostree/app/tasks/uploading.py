import glob
import os
import tarfile
import uuid

from gettext import gettext
from django.db import IntegrityError

from pulpcore.plugin.models import Artifact, Repository, ProgressReport
from pulpcore.plugin.stages import (
    ArtifactSaver,
    ContentSaver,
    DeclarativeVersion,
    DeclarativeArtifact,
    DeclarativeContent,
    QueryExistingArtifacts,
    QueryExistingContents,
    Stage,
)

from pulp_ostree.app.models import (
    OstreeRefsHead,
    OstreeCommit,
    OstreeConfig,
    OstreeObject,
    OstreeObjectType,
)

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


class OstreeUploadFirstStage(Stage):
    """A first stage of OSTree uploading pipeline that handles creation of content units."""

    def __init__(self, tarball_artifact, repository_name):
        """Initialize class variables used for parsing OSTree objects."""
        super().__init__()
        self.tarball_artifact = tarball_artifact
        self.repository_name = repository_name

        self.repo = None
        self.repo_path = None

    async def run(self):
        """Create OSTree content units and declare relations between them."""
        with tarfile.open(self.tarball_artifact.file.path) as tar, ProgressReport(
            message="Committing the tarball", code="committing.tarball", total=1
        ) as pb:
            tar.extractall(path=os.getcwd())

            self.init_repository()

            config_dc = self.create_artifact_dc("config", OstreeConfig())
            await self.put(config_dc)

            _, refs = self.repo.list_refs()
            for name, ref_commit_checksum in refs.items():
                _, ref_commit, _ = self.repo.load_commit(ref_commit_checksum)
                relative_path = get_checksum_filepath(
                    ref_commit_checksum, OstreeObjectType.OSTREE_OBJECT_TYPE_COMMIT
                )

                parent_checksum = OSTree.commit_get_parent(ref_commit)
                if not parent_checksum:
                    # there are not any parent commits, continue parsing the next head branch
                    commit = OstreeCommit(checksum=ref_commit_checksum)
                    commit_dc = self.create_artifact_dc(relative_path, commit)
                    await self.put(commit_dc)

                    await self.submit_related_objects(commit)

                    refshead = OstreeRefsHead(name=name)
                    refshead_path = os.path.join("refs/", "heads/", name)
                    refshead_dc = self.create_artifact_dc(refshead_path, refshead)
                    refshead_dc.extra_data["head_commit"] = commit
                    await self.put(refshead_dc)

                    continue

                checksum = ref_commit_checksum
                headrefs_commit = OstreeCommit(checksum=checksum)
                headrefs_commit_dc = self.create_artifact_dc(relative_path, headrefs_commit)
                commit_dcs = [headrefs_commit_dc]

                checksum = parent_checksum
                relative_path = get_checksum_filepath(
                    checksum, OstreeObjectType.OSTREE_OBJECT_TYPE_COMMIT
                )
                _, parent_commit, _ = self.repo.load_commit(checksum)
                parent_checksum = OSTree.commit_get_parent(parent_commit)

                # iterate over parent commits to create relation between them
                while parent_checksum:
                    commit = OstreeCommit(checksum=checksum)
                    commit_dc = self.create_artifact_dc(relative_path, commit)
                    commit_dcs.append(commit_dc)

                    checksum = parent_checksum
                    relative_path = get_checksum_filepath(
                        checksum, OstreeObjectType.OSTREE_OBJECT_TYPE_COMMIT
                    )
                    _, parent_commit, _ = self.repo.load_commit(checksum)
                    parent_checksum = OSTree.commit_get_parent(parent_commit)

                commit = OstreeCommit(checksum=checksum)
                commit_dc = self.create_artifact_dc(relative_path, commit)

                commit_dcs.append(commit_dc)

                await self.put(commit_dc)
                await self.submit_related_objects(commit)

                for i in range(len(commit_dcs) - 1):
                    commit_dcs[i].extra_data["parent_commit"] = commit_dcs[i + 1]

                    await self.put(commit_dcs[i])
                    await self.submit_related_objects(commit_dcs[i].content)

                refshead = OstreeRefsHead(name=name)
                refshead_path = os.path.join("refs/", "heads/", name)
                refshead_dc = self.create_artifact_dc(refshead_path, refshead)
                refshead_dc.extra_data["head_commit"] = headrefs_commit_dc.content
                await self.put(refshead_dc)

            pb.increment()

    def init_repository(self):
        """Initialize a new OSTree repository object."""
        self.repo_path = os.path.join(os.getcwd(), self.repository_name)
        self.repo = OSTree.Repo.new(Gio.File.new_for_path(self.repo_path))

        try:
            self.repo.open()
        except GLib.Error:
            raise ValueError(
                gettext("An invalid path to the repository provided: {}").format(
                    self.repository_name
                )
            )

    def create_artifact_dc(self, relative_file_path, content):
        """Create a DeclarativeContent object describing a single OSTree object (e.g., commit)."""
        filepath = os.path.join(self.repo_path, relative_file_path)

        # this is a hack that prevents the pipeline to remove a temporary file which can be
        # referenced by multiple content units at the same time; in particular, this means that
        # one OSTree object (e.g., dirmeta, file) is referenced by two different commits
        filepath_copy = filepath + str(uuid.uuid4())
        os.link(filepath, filepath_copy)

        artifact = Artifact.init_and_validate(filepath_copy)

        publication_filepath = os.path.join(self.repository_name, relative_file_path)
        # DeclarativeArtifact requires a URL to be passed to its constructor even though it will
        # never be used; specifying the URL is a requirement for standard downloading pipeline that
        # we are not utilizing right now
        da = DeclarativeArtifact(
            artifact=artifact,
            url="hackathon",
            relative_path=publication_filepath,
        )

        return DeclarativeContent(content=content, d_artifacts=[da])

    async def submit_related_objects(self, commit):
        """Create DeclarativeContent objects describing standard OSTree objects (e.g., dirtree)."""
        _, related_objects = self.repo.traverse_commit(commit.checksum, maxdepth=0)
        for obj_checksum, obj_type in related_objects.values():
            if obj_checksum == commit.checksum:
                continue

            obj = OstreeObject(commit=commit, typ=obj_type, checksum=obj_checksum)

            # OSTree objects, such as, file and filez objects are described by the same object type;
            # the ostree-libs API does not provide methods for retrieving the filename of an object;
            # therefore, we determine a correct filepath by utilizing the glob.glob() function and
            # UNIX wildcards
            _, filename = os.path.split(
                glob.glob(
                    os.path.join(self.repo_path, get_checksum_filepath(obj_checksum, obj_type))
                )[0]
            )
            obj_relative_path = os.path.join("objects/", obj_checksum[:2], filename)

            object_dc = self.create_artifact_dc(obj_relative_path, obj)
            await self.put(object_dc)


class OstreeUploadDeclarativeVersion(DeclarativeVersion):
    """A customized DeclarativeVersion class that creates a pipeline for the OSTree uploads."""

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
        except IntegrityError:
            existing_head = OstreeRefsHead.objects.get(name=dc.content.name, commit=related_commit)
            dc.content.delete()
            dc.content = existing_head


def get_checksum_filepath(checksum, obj_type):
    """Return an object's relative filepath within a repository based on its checksum and type."""
    extension = get_file_extension(obj_type)
    return os.path.join("objects/", checksum[:2], f"{checksum[2:]}.{extension}")


def get_file_extension(obj_type):
    """Return a file extension based on the type of the object."""
    if obj_type == OstreeObjectType.OSTREE_OBJECT_TYPE_FILE:
        return "file*"
    elif obj_type == OstreeObjectType.OSTREE_OBJECT_TYPE_COMMIT:
        return "commit"
    elif obj_type == OstreeObjectType.OSTREE_OBJECT_TYPE_DIR_META:
        return "dirmeta"
    elif obj_type == OstreeObjectType.OSTREE_OBJECT_TYPE_DIR_TREE:
        return "dirtree"
