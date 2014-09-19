from logging import getLogger

log = getLogger(__name__)

# Libs
GLib = None
Gio = None
OSTree = None


class Lib(object):
    """
    Control C library loading.
    This approach is used instead of static import statements because
    glib libraries cannot be loaded in one process then used in another.
    They cannot be loaded within mod_wsgi.
    """

    @staticmethod
    def load():
        """
        Load the C libraries.
        """
        global GLib
        global Gio
        global OSTree
        GLib = Lib._load('GLib')
        Gio = Lib._load('Gio')
        OSTree = Lib._load('OSTree')

    @staticmethod
    def _load(lib):
        """
        Load a particular library using gnome object inspection.

        :param lib: The name of a lib.
        :type lib: str
        """
        return getattr(__import__('gi.repository', fromlist=[lib]), lib)


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
        Lib.load()
        self.status = report.get_status()
        self.bytes_transferred = GLib.format_size_full(report.get_uint64('bytes-transferred'), 0)
        self.fetched = report.get_uint('fetched')
        self.requested = report.get_uint('requested')
        if self.requested == 0:
            self.percent = 0
        else:
            self.percent = int((self.fetched * 1.0 / self.requested) * 100)


class Repository(object):
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
        Lib.load()
        self.path = path

    def create(self):
        """
        Create the repository as needed.
        """
        fp = Gio.File.new_for_path(self.path)
        repository = OSTree.Repo.new(fp)
        try:
            repository.open(None)
        except GLib.GError:
            repository.create(OSTree.RepoMode.ARCHIVE_Z2, None)

    def add_remote(self, remote_id, url):
        """
        Add a remote definition to the repository.

        :param remote_id: The unique identifier for the remote.
        :type remote_id: str
        :param url: The URL for the remote.
        :type url: str
        """
        fp = Gio.File.new_for_path(self.path)
        options = GLib.Variant('a{sv}', {'gpg-verify': GLib.Variant('s', 'false')})
        repository = OSTree.Repo.new(fp)
        repository.open(None)
        repository.remote_add(remote_id, url, options, None)


class Pull(object):
    """
    Request to pull remote refs into a local repository.

    :ivar path: The absolute path to an ostree repository.
    :type path: str
    :ivar remote_id: The unique identifier for the remote.
    :type remote_id: str
    :ivar refs: A list of references to pull.
    :type refs: list
    """

    def __init__(self, path, remote_id, refs):
        """
        :param path: The absolute path to an ostree repository.
        :type path: str
        :param remote_id: The unique identifier for the remote.
        :type remote_id: str:
        :param refs: A list of references to pull.
        :type refs: list
        """
        Lib.load()
        self.path = path
        self.remote_id = remote_id
        self.refs = refs
        self.canceled = Gio.Cancellable.new()
        self.listener = None

    def cancel(self):
        """
        Cancel the request.
        """
        self.canceled.cancel()

    def _report_progress(self, report):
        """
        Report progress.

        :param report: The progress report issued by libostree.
        """
        if not self.listener:
            return
        try:
            _report = ProgressReport(report)
            self.listener(_report)
        except Exception:
            log.exception('progress reporting failed')

    def __call__(self, listener):
        """
        Run the pull request.

        :param listener: A progress listener.
        :type listener: callable
        """
        self.listener = listener
        flags = OSTree.RepoPullFlags.MIRROR
        fp = Gio.File.new_for_path(self.path)
        progress = OSTree.AsyncProgress.new()
        try:
            progress.connect('changed', self._report_progress)
            repository = OSTree.Repo.new(fp)
            repository.open(None)
            repository.pull(self.remote_id, self.refs, flags, progress, self.canceled)
        finally:
            progress.finish()

