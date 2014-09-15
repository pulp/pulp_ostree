import os
import shutil

from gettext import gettext as _
from tempfile import mkdtemp
from datetime import datetime

from pulp.common.util import encode_unicode
from pulp.common.plugins import importer_constants
from pulp.plugins.importer import Importer
from pulp.plugins.util.publish_step import PluginStep

from pulp_ostree.common import constants
from pulp_ostree.common import model
from pulp_ostree.plugins.importers import lib


STORAGE_DIR = '/var/lib/pulp/content/ostree/'


def entry_point():
    """
    Entry point that pulp platform uses to load the importer
    :return: importer class and its config
    :rtype:  Importer, dict
    """
    return WebImporter, {}


class WebImporter(Importer):

    def __init__(self):
        super(WebImporter, self).__init__()
        self.sync_step = None

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
        Validate the configuration.

        :param repo: metadata describing the repository
        :type  repo: pulp.plugins.model.Repository

        :param config: plugin configuration
        :type  config: pulp.plugins.config.PluginCallConfiguration
        """
        return True, ''

    def sync_repo(self, repo, conduit, config):
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

        :param conduit: provides access to relevant Pulp functionality
        :type  conduit: pulp.plugins.conduits.repo_sync.RepoSyncConduit

        :param config: plugin configuration
        :type  config: pulp.plugins.config.PluginCallConfiguration

        :return: report of the details of the sync
        :rtype:  pulp.plugins.model.SyncReport
        """
        working_dir = mkdtemp(dir=repo.working_dir)

        try:
            self.sync_step = Main(repo, conduit, config)
            return self.sync_step.process_lifecycle()
        finally:
            shutil.rmtree(working_dir, ignore_errors=True)
            self.sync_step = None

    def cancel_sync_repo(self):
        """
        Cancels an in-progress sync.

        This call is responsible for halting a current sync by stopping any
        in-progress downloads and performing any cleanup necessary to get the
        system back into a stable state.
        """
        if self.sync_step:
            self.sync_step.cancel()

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


# --- steps ------------------------------------------------------------------


class Main(PluginStep):
    """
    The main synchronization step.
    """

    def __init__(self, repo=None, conduit=None, config=None, working_dir=None):
        super(Main, self).__init__(
            step_type=constants.WEB_SYNC_MAIN_STEP,
            repo=repo,
            conduit=conduit,
            config=config,
            working_dir=working_dir,
            plugin_type=constants.WEB_IMPORTER_TYPE_ID,
        )
        self.add_child(Create())
        self.add_child(Pull())
        self.add_child(Add())

    @property
    def branches(self):
        """
        The list of branches to pull.

        :return: The branches to pull.
        :rtype list
        """
        return self.config.get(constants.IMPORTER_CONFIG_KEY_BRANCHES, [])

    @property
    def remote_id(self):
        """
        The remote ID to be pulled.

        :return: The remote ID.
        :rtype: str
        """
        remote_id = model.generate_remote_id(self.feed_url)
        return remote_id

    @property
    def storage_path(self):
        """
        The absolute path to the local ostree repository
        used to store the content units.

        :return: The storage path.
        :rtype: str
        """
        path = os.path.join(STORAGE_DIR, self.remote_id)
        return path

    @property
    def feed_url(self):
        """
        The feel URL to the remote repository.

        :return: The feed URL.
        :rtype: unicode
        """
        feed_url = self.config.get(importer_constants.KEY_FEED)
        return encode_unicode(feed_url)


class Create(PluginStep):
    """
    Ensure the local ostree repository has been created
    and the configured.
    """

    def __init__(self):
        super(Create, self).__init__(step_type=constants.WEB_SYNC_CREATE_STEP)

    def process_main(self):
        """
        Ensure the local ostree repository has been created
        and the configured.
        """
        path = self.parent.storage_path
        remote_id = self.parent.remote_id
        url = self.parent.feed_url
        try:
            os.makedirs(path)
        except OSError:
            pass
        repository = lib.Repository(path)
        repository.create()
        repository.add_remote(remote_id, url)


class Pull(PluginStep):
    """
    Pull each of the specified branches.

    :ivar pull_request: An active pull request.
    :type pull_request: PullRequest
    """

    def __init__(self):
        super(Pull, self).__init__(step_type=constants.WEB_SYNC_PULL_STEP)
        self.description = _('pull')
        self.pull_request = None

    def _report_progress(self, report):
        """
        Callback used to report progress from the ostree lib.

        :param report: The progress report.
        :type report: pulp_ostree.plugins.importers.lib.ProgressReport
        """
        self.description = \
            'fetching objects %d/%d [%d%%]' % (report.fetched, report.requested, report.percent)
        self.report_progress(force=True)

    def process_main(self):
        """
        Pull each of the specified branches.
        """
        path = self.parent.storage_path
        remote_id = self.parent.remote_id
        for branch_id in self.parent.branches:
            self.description = branch_id
            self.pull_request = lib.PullRequest(path, remote_id, [branch_id])
            self.pull_request(self._report_progress)
            if self.canceled:
                break

    def cancel(self):
        """
        Cancel the pull request.
        """
        super(Pull, self).cancel()
        if self.pull_request:
            self.pull_request.cancel()
            self.pull_request = None


class Add(PluginStep):
    """
    Add content units.
    """

    def __init__(self):
        super(Add, self).__init__(step_type=constants.WEB_SYNC_ADD_STEP)

    def process_main(self):
        """
        Find all branch (heads) in the local repository and
        create content units for them.
        """
        refs = model.Refs()
        timestamp = datetime.utcnow()
        for branch in self.find_branches():
            refs.add_head(branch)
        unit = model.Repository(self.parent.remote_id, refs, timestamp)
        conduit = self.get_conduit()
        unit = conduit.init_unit(unit.TYPE_ID, unit.unit_key, unit.metadata, unit.relative_path)
        conduit.save_unit(unit)

    def find_branches(self):
        """
        Find and return all of the branch heads in the local repository.

        :return: List of: model.Head
        :rtype: generator
        """
        root_dir = os.path.join(self.parent.storage_path, 'refs', 'heads')
        for root, dirs, files in os.walk(root_dir):
            for name in files:
                path = os.path.join(root, name)
                branch_id = os.path.relpath(path, root_dir)
                with open(path) as fp:
                    commit_id = fp.read()
                    yield model.Head(branch_id, commit_id.strip())
