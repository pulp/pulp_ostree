import os

from gettext import gettext as _

from pulp.common.util import encode_unicode
from pulp.common.plugins import reporting_constants, importer_constants
from pulp.plugins.importer import Importer
from pulp.plugins.util.publish_step import PluginStep, PluginStepIterativeProcessingMixin

from pulp_ostree.common import constants
from pulp_ostree.common import model
from pulp_ostree.plugins.importers import ostree


def entry_point():
    """
    Entry point that pulp platform uses to load the importer
    :return: importer class and its config
    :rtype:  Importer, dict
    """
    return WebImporter, {}


class WebImporter(Importer):

    @classmethod
    def metadata(cls):
        """
        Used by Pulp to classify the capabilities of this importer. The
        following keys must be present in the returned dictionary:

        * id - Programmatic way to refer to this importer. Must be unique
          across all importers. Only letters and underscores are valid.
        * display_name - User-friendly identification of the importer.
        * types - List of all content type IDs that may be imported using this
          importer.

        :return:    keys and values listed above
        :rtype:     dict
        """
        return {
            'id': constants.WEB_IMPORTER_TYPE_ID,
            'display_name': _('OSTree Web Importer'),
            'types': [constants.REPOSITORY_TYPE_ID]
        }

    def validate_config(self, repo, config):
        """
        We don't have a config yet, so it's always valid
        """
        return True, ''

    def sync_repo(self, repo, sync_conduit, config):
        """
        Synchronizes content into the given repository. This call is responsible
        for adding new content units to Pulp as well as associating them to the
        given repository.

        While this call may be implemented using multiple threads, its execution
        from the Pulp server's standpoint should be synchronous. This call should
        not return until the sync is complete.

        It is not expected that this call be atomic. Should an error occur, it
        is not the responsibility of the importer to rollback any unit additions
        or associations that have been made.

        The returned report object is used to communicate the results of the
        sync back to the user. Care should be taken to i18n the free text "log"
        attribute in the report if applicable.

        :param repo: metadata describing the repository
        :type  repo: pulp.plugins.model.Repository

        :param sync_conduit: provides access to relevant Pulp functionality
        :type  sync_conduit: pulp.plugins.conduits.repo_sync.RepoSyncConduit

        :param config: plugin configuration
        :type  config: pulp.plugins.config.PluginCallConfiguration

        :return: report of the details of the sync
        :rtype:  pulp.plugins.model.SyncReport
        """

    def cancel_sync_repo(self):
        """
        Cancels an in-progress sync.

        This call is responsible for halting a current sync by stopping any
        in-progress downloads and performing any cleanup necessary to get the
        system back into a stable state.
        """

    def remove_units(self, repo, units, config):
        """
        Removes content units from the given repository.

        This method also removes the tags associated with images in the repository.

        This call will not result in the unit being deleted from Pulp itself.

        :param repo: metadata describing the repository
        :type  repo: pulp.plugins.model.Repository

        :param units: list of objects describing the units to import in
                      this call
        :type  units: list of pulp.plugins.model.AssociatedUnit

        :param config: plugin configuration
        :type  config: pulp.plugins.config.PluginCallConfiguration
        """


class WebSync(PluginStep):

    def __init__(self, repo=None, conduit=None, config=None, working_dir=None):
        super(WebSync, self).__init__(
            step_type='main',
            repo=repo,
            conduit=conduit,
            config=config,
            working_dir=working_dir,
            plugin_type=constants.WEB_IMPORTER_TYPE_ID
        )
        for branch in self.config.get('branches', []):
            step = Pull(branch)
            self.add_child(step)

    @property
    def remote_id(self):
        remote_id = model.generate_remote_id(self.feed_url)
        return remote_id

    @property
    def storage_path(self):
        root_dir = '/var/lib/pulp/content/ostree/'
        path = os.path.join(root_dir, self.remote_id)
        return path

    @property
    def feed_url(self):
        feed_url = self.config.get(importer_constants.KEY_FEED)
        return encode_unicode(feed_url)

    def initialize(self):
        super(WebSync, self).initialize()
        repository = ostree.Repository(self.storage_path)
        repository.create()
        repository.add_remote(self.remote_id, self.feed_url)


class Pull(PluginStep, PluginStepIterativeProcessingMixin):

    def __init__(self, branch_id):
        super(Pull, self).__init__(step_type='pull')
        self.branch_id = branch_id
        self.pull_request = None

    def _report_progress(self, report):
        self.description = str(report)
        self.report_progress()

    def process_main(self):
        path = self.parent.storage_path
        remote_id = self.parent.remote_id
        refs = [self.branch_id]
        self.pull_request = ostree.PullRequest(path, remote_id, refs)
        self.pull_request(self._report_progress)

    def cancel(self):
        if not self.pull_request:
            return
        self.pull_request.cancel()
        self.pull_request = None