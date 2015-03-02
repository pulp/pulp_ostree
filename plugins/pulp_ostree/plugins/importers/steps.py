import os
import errno

from gettext import gettext as _
from logging import getLogger

from pulp.common.plugins import importer_constants
from pulp.plugins.util.publish_step import PluginStep
from pulp.plugins.model import Unit
from pulp.plugins.util.misc import mkdir
from pulp.server.exceptions import PulpCodedException

from pulp_ostree.common import constants, errors
from pulp_ostree.common import model
from pulp_ostree.plugins import lib


log = getLogger(__name__)


class Main(PluginStep):
    """
    The main synchronization step.
    """

    def __init__(self, **kwargs):
        super(Main, self).__init__(
            step_type=constants.IMPORT_STEP_MAIN,
            plugin_type=constants.WEB_IMPORTER_TYPE_ID,
            **kwargs
        )
        self.feed_url = self.config.get(importer_constants.KEY_FEED)
        self.branches = self.config.get(constants.IMPORTER_CONFIG_KEY_BRANCHES, [])
        self.remote_id = model.generate_remote_id(self.feed_url)
        self.storage_path = os.path.join(
            constants.SHARED_STORAGE, self.remote_id, constants.CONTENT_DIR)
        self.add_child(Create())
        self.add_child(Pull())
        self.add_child(Add())


class Create(PluginStep):
    """
    Ensure the local ostree repository has been created
    and the configured.
    """

    @staticmethod
    def _init_repository(path, remote_id, url):
        """
        Ensure the local ostree repository has been created
        and the configured.

        :param path: The absolute path to the local repository.
        :type path: str
        :param remote_id: The remote ID.
        :type remote_id: str
        :param url: The URL to the remote repository.
        :type url: str
        :raises PulpCodedException:
        """
        try:
            repository = lib.Repository(path)
            try:
                repository.open()
            except lib.LibError:
                repository.create()
                repository.add_remote(remote_id, url)
        except lib.LibError, le:
            pe = PulpCodedException(errors.OST0001, path=path, reason=str(le))
            raise pe

    def __init__(self):
        super(Create, self).__init__(step_type=constants.IMPORT_STEP_CREATE_REPOSITORY)
        self.description = _('Create Local Repository')

    def process_main(self):
        """
        Ensure the local ostree repository has been created
        and the configured.

        :raises PulpCodedException:
        """
        path = self.parent.storage_path
        remote_id = self.parent.remote_id
        url = self.parent.feed_url
        mkdir(path)
        mkdir(os.path.join(os.path.dirname(path), constants.LINKS_DIR))
        self._init_repository(path, remote_id, url)


class Pull(PluginStep):
    """
    Pull each of the specified branches.
    """

    def __init__(self):
        super(Pull, self).__init__(step_type=constants.IMPORT_STEP_PULL)
        self.description = _('Pull Remote Branches')

    def process_main(self):
        """
        Pull each of the specified branches.

        :raises PulpCodedException:
        """
        for branch_id in self.parent.branches:
            self._pull(self.parent.storage_path, self.parent.remote_id, branch_id)

    def _pull(self, path, remote_id, branch_id):
        """
        Pull the specified branch.

        :param path: The absolute path to the local repository.
        :type path: str
        :param remote_id: The remote ID.
        :type remote_id: str
        :param branch_id: The branch to pull.
        :type branch_id: str
        :raises PulpCodedException:
        """
        def report_progress(report):
            data = dict(
                b=branch_id,
                f=report.fetched,
                r=report.requested,
                p=report.percent
            )
            self.progress_details = 'branch: %(b)s fetching %(f)d/%(r)d %(p)d%%' % data
            self.report_progress(force=True)

        try:
            repository = lib.Repository(path)
            repository.pull(remote_id, [branch_id], report_progress)
        except lib.LibError, le:
            pe = PulpCodedException(errors.OST0002, branch=branch_id, reason=str(le))
            raise pe


class Add(PluginStep):
    """
    Add content units.
    """

    def __init__(self):
        super(Add, self).__init__(step_type=constants.IMPORT_STEP_ADD_UNITS)
        self.description = _('Add Content Units')

    def process_main(self):
        """
        Find all branch (heads) in the local repository and
        create content units for them.
        """
        conduit = self.get_conduit()
        repository = lib.Repository(self.parent.storage_path)
        for ref in repository.list_refs():
            commit = model.Commit(ref.commit, ref.metadata)
            unit = model.Unit(self.parent.remote_id, ref.path, commit)
            self.link(unit)
            _unit = Unit(constants.OSTREE_TYPE_ID, unit.key, unit.metadata, unit.storage_path)
            conduit.save_unit(_unit)

    def link(self, unit):
        """
        Link the unit storage path to the main *content* storage path.
        The link will be verified if it already exits.

        :param unit: The unit to linked.
        :type unit: model.Unit
        """
        link = unit.storage_path
        target = self.parent.storage_path
        try:
            os.symlink(target, link)
        except OSError, e:
            if e.errno == errno.EEXIST and os.path.islink(link) and os.readlink(link) == target:
                pass  # identical
            else:
                raise
