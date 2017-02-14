from gettext import gettext as _

from pulp.client.commands.repo import cudl, sync_publish, status
from pulp.client.extensions.decorator import priority
from pulp.client.extensions.extensions import PulpCliFlag

from pulp_ostree.common import constants
from pulp_ostree.extensions.admin.cudl import CreateOSTreeRepositoryCommand
from pulp_ostree.extensions.admin.cudl import UpdateOSTreeRepositoryCommand
from pulp_ostree.extensions.admin.cudl import ListOSTreeRepositoriesCommand
from pulp_ostree.extensions.admin.unit import CopyCommand, RemoveCommand, SearchCommand


SECTION_ROOT = 'ostree'
DESC_ROOT = _('manage ostree repositories')

SECTION_REPO = 'repo'
DESC_REPO = _('repository lifecycle commands')

SECTION_PUBLISH = 'publish'
DESC_PUBLISH = _('publish an ostree repository')

SECTION_SYNC = 'sync'
DESC_SYNC = _('sync a ostree repository from an upstream repository')


OPT_REPAIR = PulpCliFlag(
    '--repair',
    _("repair a corrupted local repository"),
    aliases=['-r'])


@priority()
def initialize(context):
    """
    Create the ostree CLI section and add it to the root

    :param context: the CLI context.
    :type context: pulp.client.extensions.core.ClientContext
    """
    root_section = context.cli.create_section(SECTION_ROOT, DESC_ROOT)
    repo_section = add_repo_section(context, root_section)
    add_publish_section(context, repo_section)
    add_sync_section(context, repo_section)


def add_repo_section(context, parent_section):
    """
    add a repo section to the ostree section

    :type  context: pulp.client.extensions.core.ClientContext
    :param parent_section:  section of the CLI to which the repo section
                            should be added
    :type  parent_section:  pulp.client.extensions.extensions.PulpCliSection
    """
    repo_section = parent_section.create_subsection(SECTION_REPO, DESC_REPO)

    repo_section.add_command(CreateOSTreeRepositoryCommand(context))
    repo_section.add_command(UpdateOSTreeRepositoryCommand(context))
    repo_section.add_command(cudl.DeleteRepositoryCommand(context))
    repo_section.add_command(ListOSTreeRepositoriesCommand(context))
    repo_section.add_command(CopyCommand(context))
    repo_section.add_command(RemoveCommand(context))
    repo_section.add_command(SearchCommand(context))

    return repo_section


def add_publish_section(context, parent_section):
    """
    add a publish section to the repo section

    :type  context: pulp.client.extensions.core.ClientContext
    :param parent_section:  section of the CLI to which the repo section should be added
    :type  parent_section:  pulp.client.extensions.extensions.PulpCliSection
    """
    section = parent_section.create_subsection(SECTION_PUBLISH, DESC_PUBLISH)

    renderer = status.PublishStepStatusRenderer(context)
    section.add_command(
        sync_publish.RunPublishRepositoryCommand(context,
                                                 renderer,
                                                 constants.CLI_WEB_DISTRIBUTOR_ID))
    section.add_command(
        sync_publish.PublishStatusCommand(context, renderer))

    return section


def add_sync_section(context, parent_section):
    """
    add a sync section

    :param context: pulp context
    :type  context: pulp.client.extensions.core.ClientContext
    :param parent_section:  section of the CLI to which the upload section
                            should be added
    :type  parent_section:  pulp.client.extensions.extensions.PulpCliSection
    :return: populated section
    :rtype: PulpCliSection
    """
    renderer = status.PublishStepStatusRenderer(context)
    section = parent_section.create_subsection(SECTION_SYNC, DESC_SYNC)
    command = sync_publish.RunSyncRepositoryCommand(
        context=context,
        renderer=renderer,
        override_config_options=(OPT_REPAIR,))
    section.add_command(command)
    return section
