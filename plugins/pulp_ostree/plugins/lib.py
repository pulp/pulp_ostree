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
    """

    def __init__(self, path):
        """
        :param path: The absolute path to an ostree repository.
        :type path: str
        """
        self.path = path

    @wrapped
    def open(self):
        """
        Open an existing repository.
        :raises LibError:
        """
        lib = Lib()
        fp = lib.Gio.File.new_for_path(self.path)
        repository = lib.OSTree.Repo.new(fp)
        repository.open(None)

    @wrapped
    def create(self):
        """
        Create the repository as needed.
        :raises LibError:
        """
        lib = Lib()
        fp = lib.Gio.File.new_for_path(self.path)
        repository = lib.OSTree.Repo.new(fp)
        repository.create(lib.OSTree.RepoMode.ARCHIVE_Z2, None)

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
        fp = lib.Gio.File.new_for_path(self.path)
        repository = lib.OSTree.Repo.new(fp)
        repository.open(None)
        _, refs = repository.list_refs(None, None)
        for path, commit_id in sorted(refs.items()):
            _, commit = repository.load_variant(lib.OSTree.ObjectType.COMMIT, commit_id)
            metadata = commit[0]
            ref = Ref(path, commit_id, metadata)
            _list.append(ref)
        return _list

    @wrapped
    def add_remote(self, remote_id, url):
        """
        Add a remote definition to the repository.

        :param remote_id: The unique identifier for the remote.
        :type remote_id: str
        :param url: The URL for the remote.
        :type url: str
        :raises LibError:
        """
        lib = Lib()
        fp = lib.Gio.File.new_for_path(self.path)
        options = lib.GLib.Variant('a{sv}', {'gpg-verify': lib.GLib.Variant('s', 'false')})
        repository = lib.OSTree.Repo.new(fp)
        repository.open(None)
        repository.remote_add(remote_id, url, options, None)

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
        fp = lib.Gio.File.new_for_path(self.path)
        progress = lib.OSTree.AsyncProgress.new()

        def report_progress(report):
            try:
                _report = ProgressReport(report)
                listener(_report)
            except Exception:
                log.exception('progress listener failed')

        try:
            progress.connect('changed', report_progress)
            repository = lib.OSTree.Repo.new(fp)
            repository.open(None)
            repository.pull(remote_id, refs, flags, progress, None)
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
        fp = lib.Gio.File.new_for_path(self.path)

        options = lib.GLib.Variant(
            'a{sv}',
            {
                'flags': lib.GLib.Variant('u', flags),
                'refs': lib.GLib.Variant('as', tuple(refs))
            })

        repository = lib.OSTree.Repo.new(fp)
        repository.open(None)
        repository.pull_with_options(url, options, None, None)
