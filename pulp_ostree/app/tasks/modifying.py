from collections import namedtuple

from django.db.models import Q

from pulpcore.plugin.models import Repository, RepositoryVersion, Content

from pulp_ostree.app.models import (
    OstreeCommit,
    OstreeConfig,
    OstreeRef,
    OstreeSummary,
)

ModifyContentData = namedtuple("ModifyContentData", "to_add, to_remove")


def modify_content(repository_pk, add_content_units, remove_content_units, base_version_pk=None):
    """
    Modify content in the referenced repository.

    Create a new version of the repository that will contain added or removed content.

    Args:
        repository_pk (str): The primary key of a repository.
        add_content_units (list): A list of primary keys of content units that will be added.
        remove_content_units (list): A list of primary keys of content units that will be removed.
        base_version_pk (str): The primary key for a RepositoryVersion whose content will be used
            as the initial set of content for a new RepositoryVersion.

    Raises:
        ValueError: If the remote does not specify a URL to sync
    """
    repository = Repository.objects.get(pk=repository_pk).cast()
    latest_version = repository.latest_version()
    latest_content = latest_version.content.all() if latest_version else Content.objects.none()

    summary_data = get_content_data_by_model(OstreeSummary, add_content_units, remove_content_units)
    config_data = get_content_data_by_model(OstreeConfig, add_content_units, remove_content_units)

    commit_data = get_content_data_by_model(OstreeCommit, add_content_units, remove_content_units)
    ref_data = get_content_data_by_model(OstreeRef, add_content_units, remove_content_units)

    content_to_add = recursively_get_add_content(commit_data.to_add, ref_data.to_add)

    # TODO: decide whether to add support for specifying the depth for parent commits referenced
    #   by a specific ref (currently we go only for the first commit)

    if base_version_pk:
        base_version = RepositoryVersion.objects.get(pk=base_version_pk)
    else:
        base_version = None

    content_to_remove = recursively_get_remove_content(
        commit_data.to_remove, ref_data.to_remove, latest_content
    )

    if "*" in remove_content_units:
        if latest_version:
            content_to_remove.extend(latest_version.content.values_list("pk", flat=True))

    with repository.new_version(base_version=base_version) as new_version:
        new_version.remove_content(content_to_remove)
        new_version.remove_content(summary_data.to_remove)
        new_version.remove_content(config_data.to_remove)
        new_version.add_content(content_to_add)
        new_version.add_content(summary_data.to_add)
        new_version.add_content(config_data.to_add)


def get_content_data_by_model(model_type, add_content_units, remove_content_units):
    """Return an object that holds a reference to querysets of added and removed content."""
    to_add = model_type.objects.filter(pk__in=add_content_units)
    to_remove = model_type.objects.filter(pk__in=remove_content_units)
    return ModifyContentData(to_add, to_remove)


def recursively_get_add_content(commit_data, ref_data):
    """Get all the content required for addition that the passed objects reference."""
    ref_commits_pks = ref_data.values_list("commit", flat=True)

    commit_data = commit_data.union(OstreeCommit.objects.filter(pk__in=ref_commits_pks))
    objects_pks = commit_data.values_list("objs", flat=True)
    commit_data_pks = commit_data.values_list("pk", flat=True)

    return Content.objects.filter(
        Q(pk__in=commit_data_pks) | Q(pk__in=ref_data) | Q(pk__in=objects_pks)
    )


def recursively_get_remove_content(commit_data, ref_data, latest_content):
    """Get all the content required for removal that the passed objects reference."""
    ref_commits_pks = ref_data.values_list("commit", flat=True)

    commit_data = commit_data.union(OstreeCommit.objects.filter(pk__in=ref_commits_pks))
    commit_data_pks = commit_data.values_list("pk", flat=True)

    # we do not want to get removed objects that are referenced by other commits in the repository
    remaining_commits_pks = latest_content.filter(
        ~Q(pk__in=commit_data_pks), pulp_type=OstreeCommit.get_pulp_type()
    ).values_list("pk", flat=True)
    if remaining_commits_pks:
        remaining_objects_pks = OstreeCommit.objects.filter(
            ~Q(pk__in=remaining_commits_pks)
        ).values_list("objs", flat=True)
        objects_pks = (
            OstreeCommit.objects.filter(pk__in=commit_data_pks)
            .values_list("objs", flat=True)
            .difference(remaining_objects_pks)
        )
    else:
        objects_pks = OstreeCommit.objects.filter(pk__in=commit_data_pks).values_list(
            "objs", flat=True
        )

    return Content.objects.filter(
        Q(pk__in=commit_data_pks) | Q(pk__in=ref_data) | Q(pk__in=objects_pks)
    )
