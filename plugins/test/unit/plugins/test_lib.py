from unittest import TestCase

from mock import patch, Mock

from pulp_ostree.plugins.lib import Lib, ProgressReport, Repository


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


class TestLoad(TestCase):

    @patch('__builtin__.__import__')
    def test_load(self, fake_import):
        _import = Import()
        fake_import.side_effect = _import

        lib = Lib()

        self.assertEqual(fake_import.call_count, len(lib.__dict__))
        for name in lib.__dict__.keys():
            fake_import.assert_any_with(G_OBJECT, fromlist=[name])
            self.assertEqual(getattr(lib, name), hash(name))


class TestProgressReport(TestCase):

    def test_init(self):
        fake_report = Mock()
        fake_report.get_uint = Mock(side_effect=[10, 20])
        fake_report.get_uint64 = Mock(return_value=30)

        report = ProgressReport(fake_report)

        self.assertEqual(report.status, fake_report.get_status())
        self.assertEqual(report.bytes_transferred, 30)
        self.assertEqual(report.fetched, 10)
        self.assertEqual(report.requested, 20)
        self.assertEqual(report.percent, 50)

    def test_init_zero_percent(self):
        fake_report = Mock()
        fake_report.get_uint = Mock(side_effect=[10, 0])
        fake_report.get_uint64 = Mock(return_value=30)

        report = ProgressReport(fake_report)

        self.assertEqual(report.status, fake_report.get_status())
        self.assertEqual(report.bytes_transferred, 30)
        self.assertEqual(report.fetched, 10)
        self.assertEqual(report.requested, 0)
        self.assertEqual(report.percent, 0)


class TestRepository(TestCase):

    def test_init(self):
        path = '/tmp/path-1'
        r = Repository(path)
        self.assertEqual(r.path, path)

    @patch('pulp_ostree.plugins.lib.Lib')
    def test_open(self, lib):
        fp = Mock()
        path = '/tmp/path-1'
        fake_repo = Mock()
        fake_lib = Mock()
        fake_lib.Gio.File.new_for_path.return_value = fp
        fake_lib.OSTree.Repo.new.return_value = fake_repo
        lib.return_value = fake_lib
        r = Repository(path)
        r.create()

        fake_lib.Gio.File.new_for_path.assert_called_once_with(path)
        fake_lib.OSTree.Repo.new.assert_called_once_with(fp)
        fake_repo.open.assert_called_once_with(None)
        self.assertFalse(fake_repo.create.called)

    @patch('pulp_ostree.plugins.lib.Lib')
    def test_create(self, lib):
        fp = Mock()
        path = '/tmp/path-1'
        fake_repo = Mock()
        fake_repo.open.side_effect = GError
        fake_lib = Mock()
        fake_lib.GLib.GError = GError
        fake_lib.Gio.File.new_for_path.return_value = fp
        fake_lib.OSTree.Repo.new.return_value = fake_repo
        lib.return_value = fake_lib

        r = Repository(path)
        r.create()

        fake_lib.Gio.File.new_for_path.assert_called_once_with(path)
        fake_lib.OSTree.Repo.new.assert_called_once_with(fp)
        fake_repo.open.assert_called_once_with(None)
        fake_repo.create.assert_called_once_with(fake_lib.OSTree.RepoMode.ARCHIVE_Z2, None)

    @patch('pulp_ostree.plugins.lib.Lib')
    def test_add_remote(self, lib):
        fp = Mock()
        path = '/tmp/path-1'
        remote_id = 'remote-1'
        url = 'http://free-trees.com'
        fake_repo = Mock()
        fake_lib = Mock()
        fake_lib.Gio.File.new_for_path.return_value = fp
        fake_lib.OSTree.Repo.new.return_value = fake_repo
        lib.return_value = fake_lib

        r = Repository(path)
        r.add_remote(remote_id, url)
