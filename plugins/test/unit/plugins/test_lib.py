from unittest import TestCase

from mock import patch, Mock, ANY

from pulp_ostree.plugins.lib import Lib, ProgressReport, Ref, Repository, LibError, wrapped


G_OBJECT = 'gi.repository'


class Import(object):

    def __init__(self):
        self.mod = Mock()

    def __call__(self, ignored, fromlist):
        for name in fromlist:
            setattr(self.mod, name, hash(name))
        return self.mod


class GError(Exception):
    pass


def variant(encoding, value):
    """
    Fake Variant constructor.
    """
    return encoding, value


class TestRef(TestCase):

    def test_init(self):
        ref = Ref(1, 2, 3)
        self.assertEqual(ref.path, 1)
        self.assertEqual(ref.commit, 2)
        self.assertEqual(ref.metadata, 3)


class TestLoad(TestCase):

    @patch('__builtin__.__import__')
    def test_load(self, _import):
        _import.side_effect = Import()

        # test
        lib = Lib()

        # validation
        self.assertEqual(_import.call_count, len(lib.__dict__))
        for name in lib.__dict__.keys():
            _import.assert_any_with(G_OBJECT, fromlist=[name])
            self.assertEqual(getattr(lib, name), hash(name))


class TestProgressReport(TestCase):

    def test_init(self):
        lib_report = Mock()
        lib_report.get_uint = Mock(side_effect=[10, 20])
        lib_report.get_uint64 = Mock(return_value=30)

        # test
        report = ProgressReport(lib_report)

        # validation
        self.assertEqual(report.status, lib_report.get_status.return_value)
        self.assertEqual(report.bytes_transferred, 30)
        self.assertEqual(report.fetched, 10)
        self.assertEqual(report.requested, 20)
        self.assertEqual(report.percent, 50)

    def test_init_zero_percent(self):
        lib_report = Mock()
        lib_report.get_uint = Mock(side_effect=[10, 0])
        lib_report.get_uint64 = Mock(return_value=30)

        # test
        report = ProgressReport(lib_report)

        # validation
        self.assertEqual(report.status, lib_report.get_status())
        self.assertEqual(report.bytes_transferred, 30)
        self.assertEqual(report.fetched, 10)
        self.assertEqual(report.requested, 0)
        self.assertEqual(report.percent, 0)


class TestRepository(TestCase):

    def test_init(self):
        path = '/tmp/path-1'
        repo = Repository(path)
        self.assertEqual(repo.path, path)

    @patch('pulp_ostree.plugins.lib.Lib')
    def test_open(self, lib):
        fp = Mock()
        path = '/tmp/path-1'
        lib_repo = Mock()
        _lib = Mock()
        _lib.Gio.File.new_for_path.return_value = fp
        _lib.OSTree.Repo.new.return_value = lib_repo
        lib.return_value = _lib

        # test
        repo = Repository(path)
        repo.open()

        # validation
        lib.assert_called_with()
        _lib.Gio.File.new_for_path.assert_called_once_with(path)
        _lib.OSTree.Repo.new.assert_called_once_with(fp)
        lib_repo.open.assert_called_once_with(None)
        self.assertFalse(lib_repo.create.called)

    @patch('pulp_ostree.plugins.lib.Lib')
    def test_create(self, lib):
        fp = Mock()
        path = '/tmp/path-1'
        lib_repo = Mock()
        _lib = Mock()
        _lib.GLib.GError = GError
        _lib.Gio.File.new_for_path.return_value = fp
        _lib.OSTree.Repo.new.return_value = lib_repo
        lib.return_value = _lib

        # test
        repo = Repository(path)
        repo.create()

        # validation
        lib.assert_called_with()
        _lib.Gio.File.new_for_path.assert_called_once_with(path)
        _lib.OSTree.Repo.new.assert_called_once_with(fp)
        lib_repo.create.assert_called_once_with(_lib.OSTree.RepoMode.ARCHIVE_Z2, None)

    @patch('pulp_ostree.plugins.lib.Lib')
    def test_add_remote(self, lib):
        fp = Mock()
        path = '/tmp/path-1'
        remote_id = 'remote-1'
        url = 'http://free-trees.com'
        lib_repo = Mock()
        _lib = Mock()
        _lib.GLib.Variant.side_effect = ['v1', 'v2']
        _lib.Gio.File.new_for_path.return_value = fp
        _lib.OSTree.Repo.new.return_value = lib_repo
        lib.return_value = _lib

        # test
        repo = Repository(path)
        repo.add_remote(remote_id, url)

        # validation
        lib.assert_called_with()
        _lib.OSTree.Repo.new.assert_called_once_with(fp)
        lib_repo.open.assert_called_once_with(None)
        lib_repo.remote_add.assert_called_once_with(remote_id, url, 'v2', None)
        self.assertEqual(
            _lib.GLib.Variant.call_args_list,
            [
                (('s', 'false'), {}),
                (('a{sv}', {'gpg-verify': 'v1'}), {})
            ])

    @patch('pulp_ostree.plugins.lib.Ref')
    @patch('pulp_ostree.plugins.lib.Lib')
    def test_list_refs(self, lib, ref):
        fp = Mock()
        path = '/tmp/path-1'

        commits = [
            (1, [{'version': 1}]),
            (2, [{'version': 2}])
        ]
        refs = (
            2,
            {
                'branch:1': 'commit:1',
                'branch:2': 'commit:2'
            }
        )

        _lib = Mock()
        lib_repo = Mock()
        lib_repo.list_refs.return_value = refs
        lib_repo.load_variant.side_effect = commits
        _lib.Gio.File.new_for_path.return_value = fp
        _lib.OSTree.ObjectType.COMMIT = 'COMMIT'
        _lib.OSTree.Repo.new.return_value = lib_repo
        lib.return_value = _lib

        ref_objects = [Mock(), Mock()]
        ref.side_effect = ref_objects

        # test
        repo = Repository(path)
        listed = repo.list_refs()

        # validation
        lib.assert_called_with()
        _lib.OSTree.Repo.new.assert_called_once_with(fp)
        lib_repo.open.assert_called_once_with(None)
        lib_repo.list_refs.assert_called_once_with(None, None)
        self.assertEqual(
            ref.call_args_list,
            [
                (('branch:1', 'commit:1', {'version': 1}), {}),
                (('branch:2', 'commit:2', {'version': 2}), {}),
            ])
        self.assertEqual(
            lib_repo.load_variant.call_args_list,
            [
                (('COMMIT', 'commit:1'), {}),
                (('COMMIT', 'commit:2'), {}),
            ])
        self.assertEqual(listed, ref_objects)

    @patch('pulp_ostree.plugins.lib.Lib')
    def test_pull(self, lib):
        fp = Mock()
        path = '/tmp/path-1'
        remote_id = 'remote-1'
        refs = ['branch-1']
        mirror = 'MIRROR'
        listener = Mock()
        _lib = Mock()
        lib_repo = Mock()
        progress = Mock()
        _lib.Gio.File.new_for_path.return_value = fp
        _lib.OSTree.Repo.new.return_value = lib_repo
        _lib.OSTree.AsyncProgress.new.return_value = progress
        _lib.OSTree.RepoPullFlags.MIRROR = mirror
        lib.return_value = _lib

        # test
        repo = Repository(path)
        repo.pull(remote_id, refs, listener)

        # validation
        lib.assert_called_with()
        _lib.OSTree.Repo.new.assert_called_once_with(fp)
        lib_repo.open.assert_called_once_with(None)
        progress.connect.assert_called_once_with('changed', ANY)
        lib_repo.pull.assert_called_once_with(remote_id, refs, mirror, progress, None)
        progress.finish.assert_called_once_with()

    @patch('pulp_ostree.plugins.lib.Lib')
    def test_pull_local(self, lib):
        fp = Mock()
        path = '/tmp/path-2'
        path_in = '/tmp/path-1'
        url = 'file://%s' % path_in
        refs = ['branch-1']
        mirror = 'MIRROR'
        _lib = Mock()
        lib_repo = Mock()
        _lib.GLib.Variant.side_effect = Mock(side_effect=variant)
        _lib.Gio.File.new_for_path.return_value = fp
        _lib.OSTree.Repo.new.return_value = lib_repo
        _lib.OSTree.RepoPullFlags.MIRROR = mirror
        lib.return_value = _lib

        # test
        repo = Repository(path)
        repo.pull_local(path_in, refs)

        # validation
        options = (
            'a{sv}', {
                'refs': ('as', ('branch-1',)),
                'flags': ('u', 'MIRROR')
            })
        lib.assert_called_with()
        _lib.OSTree.Repo.new.assert_called_once_with(fp)
        lib_repo.open.assert_called_once_with(None)
        lib_repo.pull_with_options.assert_called_once_with(url, options, None, None)

    @patch('pulp_ostree.plugins.lib.ProgressReport')
    @patch('pulp_ostree.plugins.lib.Lib')
    def test_pull_progress_reported(self, lib, progress_report):
        _lib = Mock()
        listener = Mock()
        progress = Mock()
        _lib.OSTree.AsyncProgress.new.return_value = progress
        lib.return_value = _lib
        report = Mock()

        def connect(unused, fn):
            fn(report)

        progress.connect.side_effect = connect

        # test
        repo = Repository('')
        repo.pull('', [], listener)

        # validation
        progress_report.assert_called_once_with(report)
        listener.assert_called_once_with(progress_report.return_value)

    @patch('pulp_ostree.plugins.lib.ProgressReport')
    @patch('pulp_ostree.plugins.lib.Lib')
    def test_pull_progress_listener_exception(self, lib, progress_report):
        _lib = Mock()
        listener = Mock(side_effect=ValueError)
        progress = Mock()
        _lib.OSTree.AsyncProgress.new.return_value = progress
        lib.return_value = _lib
        report = Mock()

        def connect(unused, fn):
            fn(report)

        progress.connect.side_effect = connect

        # test
        repo = Repository('')
        repo.pull('', [], listener)

        # validation
        progress_report.assert_called_once_with(report)
        listener.assert_called_once_with(progress_report.return_value)

    @patch('pulp_ostree.plugins.lib.Lib')
    def test_pull_finished_always_called(self, lib):
        _lib = Mock()
        _lib.GLib.GError = GError
        _repo = Mock()
        _repo.pull.side_effect = GError
        progress = Mock()
        _lib.OSTree.Repo.new.return_value = _repo
        _lib.OSTree.AsyncProgress.new.return_value = progress
        lib.return_value = _lib

        # test
        repo = Repository('')

        # validation
        self.assertRaises(LibError, repo.pull, '', [], None)
        progress.finish.assert_called_once_with()


class TestDecorator(TestCase):

    @patch('pulp_ostree.plugins.lib.Lib')
    def test_decorator(self, lib):
        _lib = Mock()
        _lib.GLib.GError = GError
        lib.return_value = _lib
        g_error = GError()

        @wrapped
        def function(a, b):
            self.assertEqual(a, 1)
            self.assertEqual(b, 2)
            raise g_error

        try:
            function(1, 2)
        except LibError, le:
            self.assertEqual(le.args[0], repr(g_error))
