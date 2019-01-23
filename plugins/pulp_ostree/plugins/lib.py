from collections import namedtuple
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
        except lib.GLib.GError as le:
            description = repr(le).encode('utf-8')
            raise LibError(description)
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
        gi = __import__('gi')
        gi.require_version('OSTree', '1.0')
        for name in self.__dict__.keys():
            lib = getattr(__import__('gi.repository', fromlist=[name]), name)
            setattr(self, name, lib)

    def __init__(self):
        self.GLib = None
        self.Gio = None
        self.OSTree = None
        self.load()

    def __enter__(self):
        self.load()
        return self

    def __exit__(self, *unused):
        pass


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

    :ivar name: The reference name.
    :type name: str
    :ivar commit: The referenced commit hash.
    :type commit: str
    :ivar metadata: The commit metadata.
    :type metadata: dict
    """

    def __init__(self, name, commit, metadata):
        """
        :param name: The reference name.
        :type name: str
        :param commit: The referenced commit hash.
        :type commit: str
        :param metadata: The commit metadata.
        :type metadata: dict
        """
        self.name = name
        self.commit = commit
        self.metadata = metadata

    @property
    def path(self):
        """
        backwards compatibility
        """
        return self.name

    def dict(self):
        """
        Convert to a dictionary.

        :return: A dictionary representation.
        :rtype: dict
        """
        return dict(self.__dict__)


# OSTree commit.
# id (str): The commit hash.
# parent_id (): The commit parent hash.
# metadata (dict): The commit metadata.
Commit = namedtuple(
    'Commit',
    [
        'id',
        'parent_id',
        'metadata'
    ])


class Variant(object):
    """
    Variant encoding.
    """

    @staticmethod
    def utf8(thing):
        """
        Encode as UTF-8.

        :param thing: An object.
        :return: The utf-8 encoded string.
        """
        return unicode(thing).encode('utf8')

    @staticmethod
    def dict(d):
        """
        Encode as a (variant) dictionary.

        :param d: A dictionary to encode.
        :type  d: dict
        :return: The variant.
        :rtype: lib.GLib.Variant
        """
        tag = 'a{sv}'
        lib = Lib()
        return lib.GLib.Variant(tag, d)

    @staticmethod
    def opt_dict(d):
        """
        Encode as a (variant) options dictionary.
        All items with None values are omitted.

        :param d: A dictionary to encode.
        :type  d: dict
        :return: The variant.
        :rtype: lib.GLib.Variant
        """
        filtered = dict((k, v) for k, v in d.iteritems() if v)
        return Variant.dict(filtered)

    @staticmethod
    def str_list(collection):
        """
        Encode as (variant) string array.

        :param collection: An iterable.
        :type  collection: iterable
        :return: A value to be used in variants.
        :rtype: lib.GLib.Variant
        """
        tag = 'as'
        lib = Lib()
        if isinstance(collection, (list, tuple)):
            return lib.GLib.Variant(tag, tuple(map(Variant.utf8, collection)))
        else:
            return None

    @staticmethod
    def str(s):
        """
        Encode as a (variant) string.

        :param s: A string.
        :type  s: basestring
        :return: The variant.
        :rtype: lib.GLib.Variant
        """
        tag = 's'
        lib = Lib()
        if isinstance(s, basestring):
            return lib.GLib.Variant(tag, Variant.utf8(s))
        else:
            return None

    @staticmethod
    def int(n):
        """
        Encode as a (variant) integer.

        :param n: An integer.
        :type  n: int
        :return: The variant.
        :rtype: lib.GLib.Variant
        """
        tag = 'i'
        lib = Lib()
        if isinstance(n, (basestring, int, float)):
            return lib.GLib.Variant(tag, int(n))
        else:
            return None

    @staticmethod
    def bool(b, negated=False):
        """
        Encode as a (variant) boolean.

        :param b: A boolean.
        :type  b: bool
        :param negated: Negate the boolean.
        :type negated: bool
        :return: The variant.
        :rtype: lib.GLib.Variant
        """
        tag = 's'
        lib = Lib()
        if isinstance(b, bool):
            if negated:
                b = (not b)
            return lib.GLib.Variant(tag, str(b).lower())
        else:
            return None


class Repository(object):
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
        if self.impl:
            del self.impl
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
    def pull(self, remote_id, refs, listener, depth=0):
        """
        Run the pull request.

        :param remote_id: The unique identifier for the remote.
        :type remote_id: str:
        :param refs: A list of references to pull.  None = ALL.
        :type refs: list
        :param listener: A progress listener.
        :type listener: callable
        :param depth: The tree traversal depth.  Note: -1 is infinite.
        :type depth: int
        :raises LibError:
        """
        lib = Lib()
        flags = lib.OSTree.RepoPullFlags.MIRROR
        progress = lib.OSTree.AsyncProgress.new()

        options = {
            'flags': Variant.int(flags),
            'depth': Variant.int(depth),
            'refs': Variant.str_list(refs)
        }

        def report_progress(report):
            try:
                _report = ProgressReport(report)
                listener(_report)
            except Exception:
                log.exception('progress listener failed')

        try:
            progress.connect('changed', report_progress)
            self.open()
            self.impl.pull_with_options(remote_id, Variant.opt_dict(options), progress, None)
        finally:
            progress.finish()

    @wrapped
    def pull_local(self, path, refs, depth=0):
        """
        Run the pull (local) request.
        Fast pull from another repository using hard links.

        :param path: The path to another repository.
        :type path: str:
        :param refs: A list of references to pull.
        :type refs: list
        :param depth: The tree traversal depth.  Note: -1 is infinite.
        :type depth: int
        :raises LibError:
        """
        lib = Lib()
        url = 'file://' + path
        flags = lib.OSTree.RepoPullFlags.MIRROR

        options = {
            'flags': Variant.int(flags),
            'depth': Variant.int(depth),
            'refs': Variant.str_list(refs)
        }

        self.open()
        self.impl.pull_with_options(url, Variant.opt_dict(options), None, None)

    def history(self, commit_id):
        """
        Get commit history.
        Traversal of the commit hierarchy.
        Depending on the traversal 'depth' setting, the entire commit
        hierarchy may not have been pulled.  This is detected when GError
        is raised.  Unfortunately, a more specific exception is not raised.

        :param commit_id: A commit (hash) used as the starting point for the traversal.
        :type  commit_id: str
        :return: A list of: Commit.
        :rtype: list
        """
        lib = Lib()
        self.open()
        history = []
        while commit_id:
            try:
                _, commit = self.impl.load_variant(lib.OSTree.ObjectType.COMMIT, commit_id)
            except lib.GLib.GError as le:
                if history:
                    # parent not pulled.
                    log.debug(le)
                    break
                else:
                    raise
            parent_id = lib.OSTree.commit_get_parent(commit)
            h = Commit(
                id=commit_id,
                parent_id=parent_id,
                metadata=commit[0])
            history.append(h)
            commit_id = parent_id
        return history

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *unused):
        self.close()


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
    def list_refs(self, required=False):
        """
        Get (remote) repository references.

        :param required: Indicates the summary file is required and
            an exception should be raised when it cannot be fetched.
        :type required: bool
        :return: list of: Ref
        :rtype: list
        :raises LibError:
        """
        _list = []
        lib = Lib()
        self.open()
        try:
            _, summary = self.impl.remote_list_refs(self.id, None)
        except lib.GLib.GError:
            if not required:
                summary = {}
            else:
                raise
        refs = sorted(summary.keys())
        flags = lib.OSTree.RepoPullFlags.COMMIT_ONLY
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
        options = {
            'tls-client-cert-path': Variant.str(self.ssl_cert_path),
            'tls-client-key-path': Variant.str(self.ssl_key_path),
            'tls-ca-path': Variant.str(self.ssl_ca_path),
            'proxy': Variant.str(self.proxy_url),
            'tls-permissive': Variant.bool(self.ssl_validation, negated=True),
            'gpg-verify': Variant.bool(self.gpg_validation),
        }
        return Variant.opt_dict(options)


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
