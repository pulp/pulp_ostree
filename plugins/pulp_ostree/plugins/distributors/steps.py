from gettext import gettext as _
import logging
import os
import subprocess

from pulp.plugins.util.publish_step import PluginStep, AtomicDirectoryPublishStep

from pulp_ostree.common import constants
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
        os.makedirs(self.get_working_dir())
        self.web_working_dir = os.path.join(self.get_working_dir(), repo.id)
        master_publish_dir = configuration.get_master_publish_dir(repo, config)
        atomic_publish_step = AtomicDirectoryPublishStep(self.get_working_dir(),
                                                         [(repo.id, publish_dir)],
                                                         master_publish_dir,
                                                         step_type=constants.PUBLISH_STEP_OVER_HTTP)
        atomic_publish_step.description = _('Making files available via web.')

        # TODO find latest image unit
        self.add_child(PublishMetadataStep())
        self.add_child(PublishContentStep())
        self.add_child(atomic_publish_step)


class PublishContentStep(PluginStep):
    """
    Publish Content
    """

    def __init__(self):
        super(PublishContentStep, self).__init__(constants.PUBLISH_STEP_CONTENT)
        self.context = None
        self.redirect_context = None
        self.description = _('Publishing OSTree Content.')

    def process_main(self):
        """
        Publish all the ostree files themselves
        """
        # TODO
        # Get the unit to link from
        # Link all the files
        pass


class PublishMetadataStep(PluginStep):
    """
    Publish Metadata (refs, branch heads, etc)
    """

    def __init__(self):
        super(PublishMetadataStep, self).__init__(constants.PUBLISH_STEP_METADATA)
        self.context = None
        self.redirect_context = None
        self.description = _('Publishing OSTree Metadata.')

    def process_main(self):
        """
        Publish all the ostree metadata or create a blank ostree if this has never been synced
        """
        # Get the unit
        # create the refs from the unit
        repo = self.get_repo()
        if not repo.content_unit_counts:
            command = ['ostree', 'init', '--repo', repo.id]
            subprocess.check_call(command, cwd=self.get_working_dir())
