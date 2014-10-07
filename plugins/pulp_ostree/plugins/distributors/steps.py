from gettext import gettext as _
import logging
import os
import ConfigParser

from pulp.plugins.util.publish_step import PluginStep, AtomicDirectoryPublishStep
from pulp.common import constants as pulp_constants
from pulp.server.db.model.criteria import UnitAssociationCriteria

from pulp_ostree.common import constants
from pulp_ostree.plugins import lib
from pulp_ostree.plugins.distributors import configuration


_LOG = logging.getLogger(__name__)


class WebPublisher(PluginStep):
    """
    Web publisher class that is responsible for the actual publishing
    of a repository via a web server
    """

    def __init__(self, repo, publish_conduit, config):
        """
        :param repo: Pulp managed Yum repository
        :type  repo: pulp.plugins.model.Repository
        :param publish_conduit: Conduit providing access to relative Pulp functionality
        :type  publish_conduit: pulp.plugins.conduits.repo_publish.RepoPublishConduit
        :param config: Pulp configuration for the distributor
        :type  config: pulp.plugins.config.PluginCallConfiguration
        """
        super(WebPublisher, self).__init__(constants.PUBLISH_STEP_WEB_PUBLISHER,
                                           repo, publish_conduit, config)

        publish_dir = configuration.get_web_publish_dir(repo, config)
        self.web_working_dir = os.path.join(self.get_working_dir(), repo.id)
        master_publish_dir = configuration.get_master_publish_dir(repo, config)
        atomic_publish_step = AtomicDirectoryPublishStep(self.get_working_dir(),
                                                         [(repo.id, publish_dir)],
                                                         master_publish_dir,
                                                         step_type=constants.PUBLISH_STEP_OVER_HTTP)
        atomic_publish_step.description = _('Making files available via web.')

        repo = self.get_repo()
        if not repo.content_unit_counts:
            self.add_child(CreateEmptyOSTreeStep())
        else:
            os.makedirs(self.web_working_dir)
            content_step = PublishContentStep(working_dir=self.web_working_dir)
            self.add_child(content_step)
            self.add_child(PublishRefsStep(content_step, working_dir=self.web_working_dir))

        self.add_child(atomic_publish_step)


class CreateEmptyOSTreeStep(PluginStep):
    """
    Publish Metadata (refs, branch heads, etc)
    """

    def __init__(self):
        super(CreateEmptyOSTreeStep, self).__init__(constants.PUBLISH_STEP_EMPTY)
        self.context = None
        self.redirect_context = None
        self.description = _('Publishing an empty OSTree.')

    def process_main(self):
        """
        create a blank ostree
        """
        repo = self.get_repo()
        repo_path = os.path.join(self.get_working_dir(), repo.id)
        ostree_repo = lib.Repository(repo_path)
        ostree_repo.create()


class PublishContentStep(PluginStep):
    """
    Publish Content
    """

    def __init__(self, **kwargs):
        super(PublishContentStep, self).__init__(constants.PUBLISH_STEP_CONTENT, **kwargs)
        self.context = None
        self.redirect_context = None
        self.description = _('Publishing OSTree Content.')
        self.unit = None

    def process_main(self):
        """
        Publish all the ostree files themselves
        """
        # Symlink all sub directories of the storage dir except the refs directory
        self.unit = self._get_ostree_unit()
        storage_path = self.unit.storage_path
        blocked_dirs = ['refs']
        directory_entries = os.listdir(storage_path)
        working_dir = self.get_working_dir()
        for entry in directory_entries:
            source_dir = os.path.join(storage_path, entry)
            if os.path.isdir(source_dir) and entry not in blocked_dirs:
                target_dir = os.path.join(working_dir, entry)
                os.symlink(source_dir, target_dir)

    def _get_ostree_unit(self):
        """
        Get the ostree unit that was added the most recently

        :returns: The ostree unit to use for publishing content & metadata
        :rtype: pulp.plugins.model.AssociatedUnit
        """
        sort_direction = pulp_constants.SORT_DIRECTION[pulp_constants.SORT_DESCENDING]
        criteria = UnitAssociationCriteria(type_ids=[constants.OSTREE_TYPE_ID],
                                           unit_sort=[('created', sort_direction)])
        units = self.get_conduit().get_units(criteria, as_generator=True)
        for unit in units:
            return unit

        # Should not be able to get here since an empty tree will use the CreateEmptyOSTreeStep
        raise Exception(_('Unable to find OSTree unit'))


class PublishRefsStep(PluginStep):
    """
    Publish refs, branch heads, etc
    """

    def __init__(self, content_step, **kwargs):
        super(PublishRefsStep, self).__init__(constants.PUBLISH_STEP_METADATA, **kwargs)
        self.context = None
        self.redirect_context = None
        self.content_step = content_step
        self.description = _('Publishing OSTree Refs.')

    def process_main(self):
        """
        Publish all the ostree metadata or create a blank ostree if this has never been synced
        """
        # make the remotes dir
        refs_dir = os.path.join(self.get_working_dir(), 'refs')
        os.makedirs(os.path.join(refs_dir, 'remotes'))

        refs = self.content_step.unit.metadata['refs']

        # publish all the heads
        for head in refs['heads']:
            file_path = os.path.join(refs_dir, head['path'])
            if not os.path.exists(os.path.dirname(file_path)):
                os.makedirs(os.path.dirname(file_path))
                with open(file_path, "w") as f:
                    f.write(head['commit_id'])

        # copy the general config file
        # clear out the remote section of the config file for the published copy
        parser = ConfigParser.SafeConfigParser()
        parser.read(os.path.join(self.content_step.unit.storage_path, 'config'))
        for section in parser.sections():
            if section.startswith('remote'):
                parser.remove_section(section)
        with open(os.path.join(self.get_working_dir(), 'config'), 'w') as new_config:
            parser.write(new_config)
