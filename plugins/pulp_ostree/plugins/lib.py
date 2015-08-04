from logging import getLogger

log = getLogger(__name__)


class LibError(Exception):
    """
    Exception raised instead of GError
    """


def wrapped(fn):
    """
    Decorator used to ensure that functions raising GError are
    re-raised as LibError exceptions.  Using the decorator so that
    this functionality does not need to be replicated in both current
    and future methods.

    :param fn: A function that raises GError.
    :type fn: function
    :return: wrapping function.
    :rtype: function
    """
    def _fn(*args, **kwargs):
        lib = Lib()
        lib.load()
        try:
            return fn(*args, **kwargs)
        except lib.GLib.GError, ge:
            raise LibError(repr(ge))
    return _fn


class Lib(object):
    """
    Provides a C library container.
    This approach is used instead of static import statements because
    glib libraries cannot be loaded in one process then used in another.
    They cannot be loaded within mod_wsgi.
    """

    def load(self):
        """
        Load libraries using gnome object inspection API.
        """
        for name in self.__dict__.keys():
            lib = getattr(__import__('gi.repository', fromlist=[name]), name)
            setattr(self, name, lib)

    def __init__(self):
        self.GLib = None
        self.Gio = None
        self.OSTree = None
        self.load()


class ProgressReport(object):
    """
    Pull progress report.

    :ivar status: The pull status.
    :type status: str
    :ivar bytes_transferred: The total bytes downloaded.
    :type bytes_transferred: int
    :ivar fetched: The total number of objects downloaded.
    :type fetched: int
    :ivar requested: The total number of objects needing download.
    :type requested: int
    :ivar percent: The percentage of completed downloads.
    :type percent: int
    """

    def __init__(self, report):
        """
        :param report: The progress reported by libostree.
        """
        self.status = report.get_status()
        self.bytes_transferred = report.get_uint64('bytes-transferred')
        self.fetched = report.get_uint('fetched')
        self.requested = report.get_uint('requested')
        if self.requested == 0:
            self.percent = 0
        else:
            self.percent = int((self.fetched * 1.0 / self.requested) * 100)


class Ref(object):
    """
    Repository reference.
    """

    def __init__(self, path, commit, metadata):
        self.path = path
        self.commit = commit
        self.metadata = metadata


class Repository():
    """
    An ostree repository.

    :ivar path: The absolute path to an ostree repository.
    :type path: str
    :ivar impl: The libostree implementation.
    :type impl: OSTree.Repository
    """

    def __init__(self, path):
        """
        :param path: The absolute path to an ostree repository.
        :type path: str
        """
        self.path = path
        self.impl = None

    @wrapped
    def open(self):
        """
        Open an existing repository.

        :raises LibError:
        """
        if self.impl:
            # already opened
            return
        lib = Lib()
        fp = lib.Gio.File.new_for_path(self.path)
        repository = lib.OSTree.Repo.new(fp)
        repository.open(None)
        self.impl = repository

    @wrapped
    def create(self):
        """
        Create the repository as needed.

        :raises LibError:
        """
        if self.impl:
            # already created
            return
        lib = Lib()
        fp = lib.Gio.File.new_for_path(self.path)
        repository = lib.OSTree.Repo.new(fp)
        repository.create(lib.OSTree.RepoMode.ARCHIVE_Z2, None)
        self.impl = repository

    def close(self):
        """
        Close the repository.
        """
        self.impl = None

    @wrapped
    def list_refs(self):
        """
        Get repository references.

        :return: list of: Ref
        :rtype: list
        :raises LibError:
        """
        _list = []
        lib = Lib()
        self.open()
        _, refs = self.impl.list_refs(None, None)
        for path, commit_id in sorted(refs.items()):
            _, commit = self.impl.load_variant(lib.OSTree.ObjectType.COMMIT, commit_id)
            metadata = commit[0]
            ref = Ref(path, commit_id, metadata)
            _list.append(ref)
        return _list

    @wrapped
    def pull(self, remote_id, refs, listener):
        """
        Run the pull request.

        :param remote_id: The unique identifier for the remote.
        :type remote_id: str:
        :param refs: A list of references to pull.
        :type refs: list
        :param listener: A progress listener.
        :type listener: callable
        :raises LibError:
        """
        lib = Lib()
        flags = lib.OSTree.RepoPullFlags.MIRROR
        progress = lib.OSTree.AsyncProgress.new()

        def report_progress(report):
            try:
                _report = ProgressReport(report)
                listener(_report)
            except Exception:
                log.exception('progress listener failed')

        try:
            progress.connect('changed', report_progress)
            self.open()
            self.impl.pull(remote_id, refs, flags, progress, None)
        finally:
            progress.finish()

    @wrapped
    def pull_local(self, path, refs):
        """
        Run the pull (local) request.
        Fast pull from another repository using hard links.

        :param path: The path to another repository.
        :type path: str:
        :param refs: A list of references to pull.
        :type refs: list
        :raises LibError:
        """
        lib = Lib()
        url = 'file://' + path
        flags = lib.OSTree.RepoPullFlags.MIRROR

        options = lib.GLib.Variant(
            'a{sv}',
            {
                'flags': lib.GLib.Variant('u', flags),
                'refs': lib.GLib.Variant('as', tuple(refs))
            })

        self.open()
        self.impl.pull_with_options(url, options, None, None)


class Remote(object):
    """
    Represents an OSTree remote repository.

    :ivar id: The remote ID.
    :type id: str
    :ivar repository: A repository.
    :type repository: Repository
    :ivar url: The remote URL.
    :type url: str
    :ivar ssl_validation: Do SSL peer certificate validation.
    :type ssl_validation: bool
    :ivar ssl_cert_path: The fully qualified path to an SSL client certificate.
        The file must contain a PEM encoded X.509 certificate. It may optionally contain
        The PEM encoded private key.
    :type ssl_cert_path: str
    :ivar ssl_key_path: The fully qualified path to an SSL client (private) key.
        The file must contain a PEM encoded private key.
    :type ssl_key_path: str
    :ivar gpg_validation: Do GPG validation of pulled content.
    :type gpg_validation: bool
    :ivar proxy_url: The url for an HTTP proxy.
    :type proxy_url: str
    """

    @staticmethod
    @wrapped
    def list(repository):
        """
        List remotes defined within the repository.

        :param repository: The repository to be updated.
        :type repository: Repository
        :raises LibError:
        :return: A list of remote IDs.
        :rtype: list
        """
        repository.open()
        return repository.impl.remote_list()

    def __init__(self, remote_id, repository):
        """
        :param remote_id: The remote ID.
        :type remote_id: str
        :param repository: A repository.
        :type repository: Repository
        """
        self.id = remote_id
        self.repository = repository
        self.url = ''
        self.ssl_key_path = None
        self.ssl_cert_path = None
        self.ssl_ca_path = None
        self.ssl_validation = False
        self.gpg_validation = False
        self.proxy_url = None

    @property
    def impl(self):
        return self.repository.impl

    @wrapped
    def open(self):
        """
        Open the associated repository.

        :raises LibError:
        """
        self.repository.open()

    @wrapped
    def add(self):
        """
        Add a remote definition to the repository.

        :raises LibError:
        """
        self.open()
        self.impl.remote_add(self.id, self.url, self.options, None)

    @wrapped
    def update(self):
        """
        Update a remote definition to the repository.
        The remote is added if it does not already exist.

        :raises LibError:
        """
        if self.id in self.list(self.repository):
            self.delete()
        self.add()

    @wrapped
    def delete(self):
        """
        Delete a remote definition from the repository.

        :raises LibError:
        """
        self.open()
        self.impl.remote_delete(self.id, None)

    @wrapped
    def import_key(self, path, key_ids):
        """
        Import GPG key by ID.

        :param path: The absolute path to a keyring.
        :type path: str
        :param key_ids: A list of key IDs.
        :type key_ids: list
        """
        self.open()
        lib = Lib()
        fp = lib.Gio.File.new_for_path(path)
        in_str = fp.read()
        imported = self.impl.remote_gpg_import(self.id, in_str, key_ids)
        return imported

    @wrapped
    def list_refs(self):
        """
        Get (remote) repository references.

        :return: list of: Ref
        :rtype: list
        :raises LibError:
        """
        _list = []
        lib = Lib()
        self.open()
        flags = lib.OSTree.RepoPullFlags.COMMIT_ONLY
        _, summary = self.impl.remote_list_refs(self.id, None)
        refs = sorted(summary.keys())
        self.impl.pull(self.id, refs, flags, None, None)
        for path, commit_id in sorted(summary.items()):
            _, commit = self.impl.load_variant(lib.OSTree.ObjectType.COMMIT, commit_id)
            metadata = commit[0]
            ref = Ref(path, commit_id, metadata)
            _list.append(ref)
        return _list

    @property
    def options(self):
        """
        Get remote options as Variant.

        :return: A variant containing options.
        :rtype: GLib.Variant
        """
        lib = Lib()
        options = {}
        if self.ssl_cert_path:
            options['tls-client-cert-path'] = lib.GLib.Variant('s', self.ssl_cert_path)
        if self.ssl_key_path:
            options['tls-client-key-path'] = lib.GLib.Variant('s', self.ssl_key_path)
        if self.ssl_ca_path:
            options['tls-ca-path'] = lib.GLib.Variant('s', self.ssl_ca_path)
        if self.proxy_url:
            options['proxy'] = lib.GLib.Variant('s', self.proxy_url)
        options['tls-permissive'] = \
            lib.GLib.Variant('s', str(not self.ssl_validation).lower())
        options['gpg-verify'] = \
            lib.GLib.Variant('s', str(self.gpg_validation).lower())
        variant = lib.GLib.Variant('a{sv}', options)
        return variant


class Summary(object):
    """
    Represents a repository summary.

    :ivar repository: A repository.
    :type repository: Repository
    """

    def __init__(self, repository):
        """
        :param repository: A repository.
        :type repository: Repository
        """
        self.repository = repository

    @property
    def impl(self):
        return self.repository.impl

    @wrapped
    def open(self):
        """
        Open the associated repository.

        :raises LibError:
        """
        self.repository.open()

    @wrapped
    def generate(self):
        self.open()
        self.impl.regenerate_summary(None, None)
