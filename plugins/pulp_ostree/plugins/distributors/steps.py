import os
import logging

from gettext import gettext as _

from pulp.plugins.util.misc import mkdir
from pulp.plugins.util.publish_step import PluginStep, AtomicDirectoryPublishStep
from pulp.common.constants import SORT_DIRECTION, SORT_ASCENDING
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

    def __init__(self, repo, conduit, config):
        """
        :param repo: Pulp managed Yum repository
        :type  repo: pulp.plugins.model.Repository
        :param conduit: Conduit providing access to relative Pulp functionality
        :type  conduit: pulp.plugins.conduits.repo_publish.RepoPublishConduit
        :param config: Pulp configuration for the distributor
        :type  config: pulp.plugins.config.PluginCallConfiguration
        """
        super(WebPublisher, self).__init__(
            constants.PUBLISH_STEP_WEB_PUBLISHER,
            repo,
            conduit,
            config)

        publish_dir = configuration.get_web_publish_dir(repo, config)
        self.web_working_dir = os.path.join(self.get_working_dir(), repo.id)
        master_publish_dir = configuration.get_master_publish_dir(repo, config)
        atomic_publish = AtomicDirectoryPublishStep(
            self.get_working_dir(),
            [(repo.id, publish_dir)],
            master_publish_dir,
            step_type=constants.PUBLISH_STEP_OVER_HTTP)

        atomic_publish.description = _('Making files available via web.')

        main = MainStep()
        self.add_child(main)
        self.add_child(atomic_publish)
        mkdir(self.web_working_dir)


class MainStep(PluginStep):

    def __init__(self, **kwargs):
        super(MainStep, self).__init__(constants.PUBLISH_STEP_MAIN, **kwargs)
        self.context = None
        self.redirect_context = None
        self.description = _('Publish Trees')

    def process_main(self):
        """
        create a blank ostree
        """
        repo = self.get_repo()
        path = os.path.join(self.get_working_dir(), repo.id)
        ostree_repo = lib.Repository(path)
        ostree_repo.create()
        criteria = UnitAssociationCriteria(
            type_ids=[constants.OSTREE_TYPE_ID],
            unit_sort=[('created', SORT_DIRECTION[SORT_ASCENDING])])
        units = self.get_conduit().get_units(criteria, as_generator=True)
        for unit in units:
            branch = unit.unit_key['branch']
            commit = unit.unit_key['commit']
            ostree_repo.pull_local(unit.storage_path, [commit])
            MainStep._add_ref(path, branch, commit)

    @staticmethod
    def _add_ref(path, branch, commit):
        path = os.path.join(path, 'refs', 'heads', os.path.dirname(branch))
        mkdir(path)
        path = os.path.join(path, os.path.basename(branch))
        with open(path, 'w+') as fp:
            fp.write(commit)
