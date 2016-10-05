import os

from gettext import gettext as _
from logging import getLogger
from urlparse import urlparse, urlunparse

from gnupg import GPG

from mongoengine import NotUniqueError

from pulp.common.plugins import importer_constants
from pulp.plugins.util.publish_step import PluginStep, SaveUnitsStep
from pulp.server.content.storage import SharedStorage
from pulp.server.controllers.repository import associate_single_unit
from pulp.server.exceptions import PulpCodedException

from pulp_ostree.common import constants, errors
from pulp_ostree.plugins.db import model
from pulp_ostree.plugins import lib


log = getLogger(__name__)


ALL = None  # all branches (refs)


class Main(PluginStep):
    """
    The main synchronization step.
    """

    def __init__(self, **kwargs):
        super(Main, self).__init__(
            step_type=constants.IMPORT_STEP_MAIN,
            plugin_type=constants.WEB_IMPORTER_TYPE_ID,
            **kwargs)
        if not self.feed_url:
            raise PulpCodedException(errors.OST0004)
        self.remote_id = model.generate_remote_id(self.feed_url)
        self.add_child(Create())
        self.add_child(Summary())
        self.add_child(Pull())
        self.add_child(Add())
        self.add_child(Clean())

    @property
    def feed_url(self):
        return self.config.get(importer_constants.KEY_FEED)

    @property
    def branches(self):
        return self.config.get(constants.IMPORTER_CONFIG_KEY_BRANCHES, ALL)

    @property
    def depth(self):
        depth = self.config.get(constants.IMPORTER_CONFIG_KEY_DEPTH, constants.DEFAULT_DEPTH)
        return int(depth)

    @property
    def repo_id(self):
        return self.get_repo().id

    @property
    def storage_dir(self):
        storage_id = self.remote_id
        with SharedStorage(constants.STORAGE_PROVIDER, storage_id) as storage:
            return storage.content_dir


class Create(PluginStep):
    """
    Ensure the local ostree repository has been created
    and the configured.  A temporary remote is created using the repo_id as
    the remote_id.  The remote is created using the Remote which stores SSL
    certificates in the working directory.
    """

    def __init__(self):
        super(Create, self).__init__(step_type=constants.IMPORT_STEP_CREATE_REPOSITORY)
        self.description = _('Create Local Repository')

    def process_main(self, item=None):
        """
        Ensure the local ostree repository has been created
        and the configured.  Also creates and configures a temporary remote
        used for the subsequent pulls.

        :raises PulpCodedException:
        """
        path = self.parent.storage_dir
        try:
            repository = lib.Repository(path)
            try:
                repository.open()
            except lib.LibError:
                repository.create()
            remote = Remote(self, repository)
            remote.add()
        except lib.LibError, le:
            pe = PulpCodedException(errors.OST0001, path=path, reason=str(le))
            raise pe


class Summary(PluginStep):
    """
    Update the summary information stored in the repository scratchpad.
    """

    def __init__(self):
        super(Summary, self).__init__(step_type=constants.IMPORT_STEP_SUMMARY)
        self.description = _('Update Summary')

    def process_main(self, item=None):
        """
        Add/update the remote summary information in the
        repository scratchpad.
        """
        try:
            lib_repository = lib.Repository(self.parent.storage_dir)
            remote = lib.Remote(self.parent.repo_id, lib_repository)
            refs = [r.dict() for r in remote.list_refs()]
        except lib.LibError, le:
            pe = PulpCodedException(errors.OST0005, reason=str(le))
            raise pe
        repository = self.get_repo().repo_obj
        map(self.clean_metadata, refs)
        repository.scratchpad.update({
            constants.REMOTE: {
                constants.SUMMARY: refs
            }
        })
        repository.save()

    @staticmethod
    def clean_metadata(ref):
        """
        Updates the metadata part of the specified ref by replacing
        keys containing dot (.) with underscores (-).  This ensures the
        keys can be stored in the DB.

        :param ref: A dictionary retrieved with lib.Remote().list_refs()
        :type  ref: dict
        """
        key = 'metadata'
        ref[key] = dict((k.replace('.', '-'), v) for k, v in ref[key].items())


class Pull(PluginStep):
    """
    Pull each of the specified branches.
    """

    def __init__(self):
        super(Pull, self).__init__(step_type=constants.IMPORT_STEP_PULL)
        self.description = _('Pull Remote Branches')

    def process_main(self, item=None):
        """
        Pull each of the specified branches using the temporary remote
        configured using the repo_id as the remote_id.

        :raises PulpCodedException:
        """
        self._pull(
            self.parent.storage_dir,
            self.parent.repo_id,
            self.parent.branches,
            self.parent.depth)

    def _pull(self, path, remote_id, refs, depth):
        """
        Pull the specified branch.

        :param path: The absolute path to the local repository.
        :type path: str
        :param remote_id: The remote ID.
        :type remote_id: str
        :param refs: The refs to pull.
        :type refs: list
        :param depth: The tree traversal depth.
        :type depth: int
        :raises PulpCodedException:
        """
        def report_progress(report):
            data = dict(
                f=report.fetched,
                r=report.requested,
                p=report.percent
            )
            self.progress_details = 'fetching %(f)d/%(r)d %(p)d%%' % data
            self.report_progress(force=True)

        try:
            repository = lib.Repository(path)
            repository.pull(remote_id, refs, report_progress, depth)
        except lib.LibError, le:
            pe = PulpCodedException(errors.OST0002, reason=str(le))
            raise pe


class Add(SaveUnitsStep):
    """
    Add content units.
    """

    def __init__(self):
        super(Add, self).__init__(step_type=constants.IMPORT_STEP_ADD_UNITS)
        self.description = _('Add Content Units')

    def process_main(self, item=None):
        """
        Find all branch (heads) in the local repository and
        create content units for them.
        """
        lib_repository = lib.Repository(self.parent.storage_dir)
        for ref in lib_repository.list_refs():
            # the branches listed here can have an undesired prefix ending with a ":"
            branch = ref.path.split(':')[-1]
            if self.parent.branches is not ALL:
                if branch not in self.parent.branches:
                    # not listed
                    log.debug('skipping non-selected branch: {0}'.format(branch))
                    continue
            unit = model.Branch(
                remote_id=self.parent.remote_id,
                branch=branch,
                commit=ref.commit,
                metadata=ref.metadata)
            try:
                unit.save()
            except NotUniqueError:
                unit = model.Branch.objects.get(**unit.unit_key)
            associate_single_unit(self.get_repo().repo_obj, unit)


class Clean(PluginStep):
    """
    Clean up after import.
    """

    def __init__(self):
        super(Clean, self).__init__(step_type=constants.IMPORT_STEP_CLEAN)
        self.description = _('Clean')

    def process_main(self, item=None):
        """
        Clean up after import:
         - Delete the remote used for the pull.
        """
        path = self.parent.storage_dir
        remote_id = self.parent.repo_id
        try:
            repository = lib.Repository(path)
            remote = lib.Remote(remote_id, repository)
            remote.delete()
        except lib.LibError, le:
            pe = PulpCodedException(errors.OST0003, id=remote_id, reason=str(le))
            raise pe


class Remote(object):
    """
    Represents an OSTree remote.
    Used to build and configure an OSTree remote.
    The complexity of configuring the remote based on the importer
    configuration is isolated here.

    :ivar step: The create step.
    :type step: Create
    :ivar repository: An OSTree repository.
    :type repository: lib.Repository
    """

    def __init__(self, step, repository):
        """
        :param step: The create step.
        :type step: Create
        :param repository: An OSTree repository.
        :type repository: lib.Repository
        """
        self.step = step
        self.repository = repository

    @property
    def url(self):
        """
        The remote URL.

        :return: The remote URL
        :rtype: str
        """
        return self.step.parent.feed_url

    @property
    def remote_id(self):
        """
        The remote ID.

        :return: The remote ID.
        :rtype: str
        """
        return self.step.parent.repo_id

    @property
    def working_dir(self):
        """
        The working directory.

        :return: The absolute path to the working directory.
        :rtype: str
        """
        return self.step.get_working_dir()

    @property
    def config(self):
        """
        The importer configuration.

        :return: The importer configuration.
        :rtype: pulp.server.plugins.config.PluginCallConfiguration
        """
        return self.step.get_config()

    @property
    def ssl_key_path(self):
        """
        The SSL private key path.

        :return: The absolute path to the private key.
        :rtype: str
        """
        path = None
        key = self.config.get(importer_constants.KEY_SSL_CLIENT_KEY)
        if key:
            path = os.path.join(self.working_dir, 'key.pem')
            with open(path, 'w+') as fp:
                fp.write(key)
            os.chmod(path, 0600)
        return path

    @property
    def ssl_cert_path(self):
        """
        The SSL client certificate key path.

        :return: The absolute path to the client certificate.
        :rtype: str
        """
        path = None
        key = self.config.get(importer_constants.KEY_SSL_CLIENT_CERT)
        if key:
            path = os.path.join(self.working_dir, 'cert.pem')
            with open(path, 'w+') as fp:
                fp.write(key)
        return path

    @property
    def ssl_ca_path(self):
        """
        The SSL CA certificate key path.

        :return: The absolute path to the CA certificate.
        :rtype: str
        """
        path = None
        key = self.config.get(importer_constants.KEY_SSL_CA_CERT)
        if key:
            path = os.path.join(self.working_dir, 'ca.pem')
            with open(path, 'w+') as fp:
                fp.write(key)
        return path

    @property
    def ssl_validation(self):
        """
        The SSL validation flag.

        :return: True if SSL validation is enabled.
        :rtype: bool
        """
        return self.config.get(importer_constants.KEY_SSL_VALIDATION, False)

    @property
    def gpg_keys(self):
        """
        The GPG keyring path and list of key IDs.

        :return: A tuple of: (path, key_ids)
            The *path* is the absolute path to a keyring.
            The *key_ids* is a list of key IDs added to the keyring.
        :rtype: tuple
        """
        home = self.working_dir
        path = os.path.join(home, 'pubring.gpg')
        key_list = self.config.get(constants.IMPORTER_CONFIG_KEY_GPG_KEYS, [])
        gpg = GPG(gnupghome=home)
        map(gpg.import_keys, key_list)
        key_ids = [key['keyid'] for key in gpg.list_keys()]
        return path, key_ids

    @property
    def proxy_url(self):
        """
        The proxy URL.

        :return: The proxy URL.
        :rtype: str
        """
        url = None
        host = self.config.get(importer_constants.KEY_PROXY_HOST)
        port = self.config.get(importer_constants.KEY_PROXY_PORT)
        user = self.config.get(importer_constants.KEY_PROXY_USER)
        password = self.config.get(importer_constants.KEY_PROXY_PASS)
        if host:
            host = host.split('://', 1)
            if len(host) == 1:
                host = ('http', host[0])
            host = '://'.join(host)
            parsed = list(urlparse(host))
            if port:
                parsed[1] = '{}:{}'.format(parsed[1], port)
            if user and password:
                parsed[1] = '{}:{}@{}'.format(user, password, parsed[1])
            url = urlunparse(parsed)
        return url

    def add(self):
        """
        Add (or replace) this remote to the repository.
        """
        path, key_ids = self.gpg_keys
        impl = lib.Remote(self.remote_id, self.repository)
        impl.url = self.url
        impl.ssl_key_path = self.ssl_key_path
        impl.ssl_cert_path = self.ssl_cert_path
        impl.ssl_ca_path = self.ssl_ca_path
        impl.ssl_validation = self.ssl_validation
        impl.gpg_validation = len(key_ids) > 0
        impl.proxy_url = self.proxy_url
        impl.update()
        if key_ids:
            impl.import_key(path, key_ids)
