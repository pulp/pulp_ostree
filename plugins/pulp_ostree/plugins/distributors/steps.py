import itertools
import os
import logging

from gettext import gettext as _

from pulp.plugins.util.misc import mkdir
from pulp.plugins.util.publish_step import PluginStep, AtomicDirectoryPublishStep
from pulp.server.controllers.repository import get_unit_model_querysets

from pulp_ostree.common import constants
from pulp_ostree.plugins import lib
from pulp_ostree.plugins.distributors import configuration
from pulp_ostree.plugins.db.model import Branch


_LOG = logging.getLogger(__name__)


class WebPublisher(PluginStep):
    """
    Web publisher class that is responsible for the actual publishing
    of a repository via a web server
    """

    def __init__(self, repo, conduit, config, working_dir=None, **kwargs):
        """
        :param repo: The repository being published.
        :type  repo: pulp.plugins.model.Repository
        :param conduit: Conduit providing access to relative Pulp functionality
        :type  conduit: pulp.plugins.conduits.repo_publish.RepoPublishConduit
        :param config: Pulp configuration for the distributor
        :type  config: pulp.plugins.config.PluginCallConfiguration
        :param working_dir: The temp directory this step should use for processing.
        :type  working_dir: str
        """
        super(WebPublisher, self).__init__(
            step_type=constants.PUBLISH_STEP_WEB_PUBLISHER,
            repo=repo,
            conduit=conduit,
            config=config,
            working_dir=working_dir,
            plugin_type=constants.WEB_DISTRIBUTOR_TYPE_ID,
            **kwargs)
        self.publish_dir = os.path.join(self.get_working_dir(), repo.id)
        atomic_publish = AtomicDirectoryPublishStep(
            self.get_working_dir(),
            [(repo.id, configuration.get_web_publish_dir(repo.repo_obj, config))],
            configuration.get_master_publish_dir(repo.repo_obj, config),
            step_type=constants.PUBLISH_STEP_OVER_HTTP)
        atomic_publish.description = _('Making files available via web.')
        main = MainStep(config=config)
        self.add_child(main)
        self.add_child(atomic_publish)
        mkdir(self.publish_dir)


class MainStep(PluginStep):

    def __init__(self, **kwargs):
        super(MainStep, self).__init__(constants.PUBLISH_STEP_MAIN, **kwargs)
        self.context = None
        self.redirect_context = None
        self.description = _('Publish Trees')

    @property
    def depth(self):
        depth = self.parent.config.get(
            constants.IMPORTER_CONFIG_KEY_DEPTH, constants.DEFAULT_DEPTH)
        return int(depth)

    def process_main(self, item=None):
        """
        Publish the repository.
        Create an empty repository.  Then, for each unit,
        perform a (local) pull which links objects in this repository to
        objects in the *backing* repository at the storage path.  This starts
        with the branch HEAD commit and then includes all referenced objects.
        """
        path = self.parent.publish_dir
        repository = lib.Repository(path)
        repository.create()
        for unit in self._get_units():
            repository.pull_local(unit.storage_path, [unit.commit], self.depth)
            MainStep._add_ref(path, unit.branch, unit.commit)
        summary = lib.Summary(repository)
        summary.generate()

    def _get_units(self):
        """
        Get the collection of units to be published.
        The collection contains only the newest unit for each branch.
        :return: An iterable of units to publish.
        :rtype: iterable
        """
        units_by_branch = {}
        units = itertools.chain(*get_unit_model_querysets(self.get_repo().id, Branch))
        for unit in sorted(units, key=lambda u: u.created):
            units_by_branch[unit.branch] = unit
        return units_by_branch.values()

    @staticmethod
    def _add_ref(path, branch, commit):
        """
        Write a branch (ref) file into the published repository.
        :param path: The absolute path to the repository.
        :type path: str
        :param branch: The branch relative path.
        :type branch: str
        :param commit: The commit hash.
        :type commit: str
        """
        path = os.path.join(path, 'refs', 'heads', os.path.dirname(branch))
        mkdir(path)
        path = os.path.join(path, os.path.basename(branch))
        with open(path, 'w+') as fp:
            fp.write(commit)
