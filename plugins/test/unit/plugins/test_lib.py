from unittest import TestCase

from mock import patch, Mock, ANY

from pulp_ostree.plugins.lib import (
    Lib,
    LibError,
    ProgressReport,
    Commit,
    Ref,
    Remote,
    Variant,
    Repository,
    Summary,
    wrapped)


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
        self.assertEqual(ref.path, 1)  # backwards compatibility
        self.assertEqual(ref.name, 1)
        self.assertEqual(ref.commit, 2)
        self.assertEqual(ref.metadata, 3)

    def test_dict(self):
        ref = Ref(1, 2, 3)
        self.assertEqual(ref.dict(), ref.__dict__)


class TestLoad(TestCase):

    @patch('__builtin__.__import__')
    def test_load(self, _import):
        _import.side_effect = Import()

        # test
        lib = Lib()

        # validation
        self.assertEqual(_import.call_count, len(lib.__dict__))
        for name in lib.__dict__.keys():
            _import.assert_any_call(G_OBJECT, fromlist=[name])
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


class TestVariant(TestCase):

    @patch('pulp_ostree.plugins.lib.Lib')
    def test_str(self, lib):
        _lib = Mock()
        _lib.GLib.Variant.side_effect = Mock(side_effect=variant)
        lib.return_value = _lib
        # str
        s = 'hello'
        tag, value = Variant.str(s)
        self.assertEqual(tag, 's')
        self.assertEqual(value, s)
        # none
        self.assertTrue(Variant.str(None) is None)

    @patch('pulp_ostree.plugins.lib.Lib')
    def test_int(self, lib):
        _lib = Mock()
        _lib.GLib.Variant.side_effect = Mock(side_effect=variant)
        lib.return_value = _lib
        # integer
        n = '10'
        tag, value = Variant.int(n)
        self.assertEqual(tag, 'i')
        self.assertEqual(value, int(n))
        # none
        self.assertTrue(Variant.int(None) is None)

    @patch('pulp_ostree.plugins.lib.Lib')
    def test_bool(self, lib):
        _lib = Mock()
        _lib.GLib.Variant.side_effect = Mock(side_effect=variant)
        lib.return_value = _lib
        # bool
        b = True
        tag, value = Variant.bool(b)
        self.assertEqual(tag, 's')
        self.assertEqual(value, 'true')
        # negated
        b = True
        tag, value = Variant.bool(b, negated=True)
        self.assertEqual(tag, 's')
        self.assertEqual(value, 'false')
        # none
        self.assertTrue(Variant.bool(None) is None)

    @patch('pulp_ostree.plugins.lib.Lib')
    def test_str_list(self, lib):
        _lib = Mock()
        _lib.GLib.Variant.side_effect = Mock(side_effect=variant)
        lib.return_value = _lib
        # list
        _list = ['1', '2']
        tag, value = Variant.str_list(_list)
        self.assertEqual(tag, 'as')
        self.assertEqual(value, tuple(_list))
        # none
        self.assertTrue(Variant.str_list(None) is None)

    @patch('pulp_ostree.plugins.lib.Lib')
    def test_dict(self, lib):
        _lib = Mock()
        _lib.GLib.Variant.side_effect = Mock(side_effect=variant)
        lib.return_value = _lib
        d = dict(a=1, b=2)
        tag, value = Variant.dict(d)
        self.assertEqual(tag, 'a{sv}')
        self.assertEqual(value, d)

    @patch('pulp_ostree.plugins.lib.Lib')
    def test_options(self, lib):
        _lib = Mock()
        _lib.GLib.Variant.side_effect = Mock(side_effect=variant)
        lib.return_value = _lib
        d = dict(a=1, b=2, c=3)
        tag, value = Variant.dict(d)
        self.assertEqual(tag, 'a{sv}')
        self.assertEqual(value, dict((k, v) for k, v in d.iteritems() if v))


class TestRepository(TestCase):

    def test_init(self):
        path = '/tmp/path-1'
        repo = Repository(path)
        self.assertEqual(repo.path, path)
        self.assertEqual(repo.impl, None)

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
        self.assertEqual(repo.impl, lib_repo)

    @patch('pulp_ostree.plugins.lib.Lib')
    def test_already_opened(self, lib):
        path = '/tmp/path-1'
        _lib = Mock()
        lib.return_value = _lib

        # test
        repo = Repository(path)
        repo.impl = Mock()
        repo.open()

        # validation
        self.assertFalse(_lib.OSTree.Repo.new.called)

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
    def test_already_created(self, lib):
        path = '/tmp/path-1'
        _lib = Mock()
        lib.return_value = _lib

        # test
        repo = Repository(path)
        repo.impl = Mock()
        repo.create()

        # validation
        self.assertFalse(_lib.OSTree.Repo.new.called)

    def test_close(self):
        repository = Repository('')
        repository.impl = Mock()

        # test
        repository.close()

        # validation
        self.assertEqual(repository.impl, None)

    @patch('pulp_ostree.plugins.lib.Ref')
    @patch('pulp_ostree.plugins.lib.Lib')
    def test_list_refs(self, lib, ref):
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
        _lib.OSTree.ObjectType.COMMIT = 'COMMIT'
        lib.return_value = _lib

        ref_objects = [Mock(), Mock()]
        ref.side_effect = ref_objects

        # test
        repo = Repository(path)
        repo.open = Mock()
        repo.impl = lib_repo
        listed = repo.list_refs()

        # validation
        lib.assert_called_with()
        repo.open.assert_called_once_with()
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
        path = '/tmp/path-1'
        remote_id = 'remote-1'
        depth = 3
        refs = ['branch-1']
        mirror = 0xFF
        listener = Mock()
        _lib = Mock()
        lib_repo = Mock()
        progress = Mock()
        _lib.GLib.Variant.side_effect = Mock(side_effect=variant)
        _lib.OSTree.AsyncProgress.new.return_value = progress
        _lib.OSTree.RepoPullFlags.MIRROR = mirror
        lib.return_value = _lib

        # test
        repo = Repository(path)
        repo.open = Mock()
        repo.impl = lib_repo
        repo.pull(remote_id, refs, listener, depth)

        # validation
        options = (
            'a{sv}', {
                'refs': ('as', tuple(refs)),
                'depth': ('i', depth),
                'flags': ('i', mirror)
            })
        lib.assert_called_with()
        repo.open.assert_called_once_with()
        progress.connect.assert_called_once_with('changed', ANY)
        lib_repo.pull_with_options.assert_called_once_with(remote_id, options, progress, None)
        progress.finish.assert_called_once_with()

    @patch('pulp_ostree.plugins.lib.Lib')
    def test_pull_all(self, lib):
        path = '/tmp/path-1'
        remote_id = 'remote-1'
        depth = 3
        refs = None
        mirror = 0xFF
        listener = Mock()
        _lib = Mock()
        lib_repo = Mock()
        progress = Mock()
        _lib.GLib.Variant.side_effect = Mock(side_effect=variant)
        _lib.OSTree.AsyncProgress.new.return_value = progress
        _lib.OSTree.RepoPullFlags.MIRROR = mirror
        lib.return_value = _lib

        # test
        repo = Repository(path)
        repo.open = Mock()
        repo.impl = lib_repo
        repo.pull(remote_id, refs, listener, depth)

        # validation
        options = (
            'a{sv}', {
                'depth': ('i', depth),
                'flags': ('i', mirror)
            })
        lib.assert_called_with()
        repo.open.assert_called_once_with()
        progress.connect.assert_called_once_with('changed', ANY)
        lib_repo.pull_with_options.assert_called_once_with(remote_id, options, progress, None)
        progress.finish.assert_called_once_with()

    @patch('pulp_ostree.plugins.lib.Lib')
    def test_pull_local(self, lib):
        path = '/tmp/path-2'
        path_in = '/tmp/path-1'
        url = 'file://%s' % path_in
        refs = ['branch-1']
        mirror = 0xFF
        depth = 3
        _lib = Mock()
        lib_repo = Mock()
        _lib.GLib.Variant.side_effect = Mock(side_effect=variant)
        _lib.OSTree.RepoPullFlags.MIRROR = mirror
        lib.return_value = _lib

        # test
        repo = Repository(path)
        repo.open = Mock()
        repo.impl = lib_repo
        repo.pull_local(path_in, refs, depth)

        # validation
        options = (
            'a{sv}', {
                'refs': ('as', tuple(refs)),
                'depth': ('i', depth),
                'flags': ('i', mirror)
            })
        lib.assert_called_with()
        repo.open.assert_called_once_with()
        lib_repo.pull_with_options.assert_called_once_with(url, options, None, None)

    @patch('pulp_ostree.plugins.lib.Lib')
    def test_pull_local_all(self, lib):
        path = '/tmp/path-2'
        path_in = '/tmp/path-1'
        url = 'file://%s' % path_in
        refs = None
        mirror = 0xFF
        depth = 3
        _lib = Mock()
        lib_repo = Mock()
        _lib.GLib.Variant.side_effect = Mock(side_effect=variant)
        _lib.OSTree.RepoPullFlags.MIRROR = mirror
        lib.return_value = _lib

        # test
        repo = Repository(path)
        repo.open = Mock()
        repo.impl = lib_repo
        repo.pull_local(path_in, refs, depth)

        # validation
        options = (
            'a{sv}', {
                'depth': ('i', depth),
                'flags': ('i', mirror)
            })
        lib.assert_called_with()
        repo.open.assert_called_once_with()
        lib_repo.pull_with_options.assert_called_once_with(url, options, None, None)

    @patch('pulp_ostree.plugins.lib.ProgressReport')
    @patch('pulp_ostree.plugins.lib.Lib')
    def test_pull_progress_reported(self, lib, progress_report):
        _lib = Mock()
        listener = Mock()
        progress = Mock()
        _lib.OSTree.AsyncProgress.new.return_value = progress
        _lib.OSTree.RepoPullFlags.MIRROR = 0xFF
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
        _lib.OSTree.RepoPullFlags.MIRROR = 0xFF
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
        _repo.pull_with_options.side_effect = GError
        progress = Mock()
        _lib.OSTree.Repo.new.return_value = _repo
        _lib.OSTree.AsyncProgress.new.return_value = progress
        _lib.OSTree.RepoPullFlags.MIRROR = 0xFF
        lib.return_value = _lib

        # test
        repo = Repository('')

        # validation
        self.assertRaises(LibError, repo.pull, '', [], None)
        progress.finish.assert_called_once_with()

    @patch('pulp_ostree.plugins.lib.Lib')
    def test_history(self, lib):
        commit_id = '123'
        parents = [
            '456',
            '789',
            None
        ]
        variants = [
            (True, ({'version': 1},)),
            (True, ({'version': 2},)),
            (True, ({'version': 3},)),
        ]
        _repo = Mock()
        _repo.load_variant.side_effect = variants
        _lib = Mock()
        _lib.OSTree.Repo.new.return_value = _repo
        _lib.GLib.GError = GError
        _lib.OSTree.ObjectType.COMMIT = 'COMMIT'
        _lib.OSTree.commit_get_parent.side_effect = parents
        lib.return_value = _lib

        # test
        repo = Repository('')
        history = repo.history(commit_id)

        # validation
        self.assertEqual(history, [
            Commit('123', {'version': 1}),
            Commit('456', {'version': 2}),
            Commit('789', {'version': 3}),
        ])

    @patch('pulp_ostree.plugins.lib.Lib')
    def test_history_not_pulled(self, lib):
        # Depending on tree traversal depth, the entire commit
        # hierarchy may not have been pulled.
        commit_id = '123'
        parents = [
            '456',
            '789',
            None
        ]
        variants = [
            (True, ({'version': 1},)),
            (True, ({'version': 2},)),
            GError,
        ]
        _repo = Mock()
        _repo.load_variant.side_effect = variants
        _lib = Mock()
        _lib.OSTree.Repo.new.return_value = _repo
        _lib.GLib.GError = GError
        _lib.OSTree.ObjectType.COMMIT = 'COMMIT'
        _lib.OSTree.commit_get_parent.side_effect = parents
        lib.return_value = _lib

        # test
        repo = Repository('')
        history = repo.history(commit_id)

        # validation
        self.assertEqual(history, [
            Commit('123', {'version': 1}),
            Commit('456', {'version': 2}),
        ])

    @patch('pulp_ostree.plugins.lib.Lib')
    def test_history_failed(self, lib):
        commit_id = '123'
        _repo = Mock()
        _repo.load_variant.side_effect = GError
        _lib = Mock()
        _lib.OSTree.Repo.new.return_value = _repo
        _lib.GLib.GError = GError
        _lib.OSTree.ObjectType.COMMIT = 'COMMIT'
        lib.return_value = _lib

        # test
        repo = Repository('')
        self.assertRaises(GError, repo.history, commit_id)


class TestRemote(TestCase):

    @patch('pulp_ostree.plugins.lib.Lib', Mock())
    def test_list(self):
        repository = Mock()

        # test
        remotes = Remote.list(repository)

        # validation
        self.assertEqual(remotes, repository.impl.remote_list.return_value)

    def test_init(self):
        repository = Mock()
        remote_id = 'test'

        # test
        remote = Remote(remote_id, repository)

        # validation
        self.assertEqual(remote.repository, repository)
        self.assertEqual(remote.id, remote_id)
        self.assertEqual(remote.url, '')
        self.assertEqual(remote.ssl_ca_path, None)
        self.assertEqual(remote.ssl_cert_path, None)
        self.assertEqual(remote.ssl_key_path, None)
        self.assertEqual(remote.proxy_url, None)
        self.assertFalse(remote.ssl_validation)
        self.assertFalse(remote.gpg_validation)

    def test_impl(self):
        repository = Mock()
        remote = Remote('123', repository)
        self.assertEqual(remote.impl, repository.impl)

    @patch('pulp_ostree.plugins.lib.Lib', Mock())
    def test_open(self):
        repository = Mock()
        remote = Remote('123', repository)
        remote.open()
        repository.open.assert_called_once_with()

    @patch('pulp_ostree.plugins.lib.Lib', Mock())
    @patch('pulp_ostree.plugins.lib.Remote.options')
    def test_add(self, options):
        repository = Mock()

        # test
        remote = Remote('123', repository)
        remote.add()

        # validation
        repository.open.assert_called_once_with()
        repository.impl.remote_add.assert_called_once_with(remote.id, remote.url, options, None)

    @patch('pulp_ostree.plugins.lib.Remote.list')
    @patch('pulp_ostree.plugins.lib.Lib', Mock())
    def test_update(self, _list):
        remote_id = '123'
        repository = Mock()
        _list.return_value = [remote_id]

        # test
        remote = Remote(remote_id, repository)
        remote.delete = Mock()
        remote.add = Mock()
        remote.update()

        # validation
        _list.assert_called_once_with(repository)
        remote.delete.assert_called_once_with()
        remote.add.assert_called_once_with()

    @patch('pulp_ostree.plugins.lib.Remote.list')
    @patch('pulp_ostree.plugins.lib.Lib', Mock())
    def test_update_not_exist(self, _list):
        repository = Mock()
        _list.return_value = []

        # test
        remote = Remote('123', repository)
        remote.delete = Mock()
        remote.add = Mock()
        remote.update()

        # validation
        _list.assert_called_once_with(repository)
        remote.add.assert_called_once_with()
        self.assertFalse(remote.delete.called)

    @patch('pulp_ostree.plugins.lib.Lib', Mock())
    def test_delete(self):
        repository = Mock()

        # test
        remote = Remote('123', repository)
        remote.delete()

        # validation
        repository.open.assert_called_once_with()
        repository.impl.remote_delete.assert_called_once_with(remote.id, None)

    @patch('pulp_ostree.plugins.lib.Lib')
    def test_import_key(self, lib):
        repository = Mock()
        keyring = '/tmp/keyring'
        key_id = 'test-key'
        fp = Mock()
        _lib = Mock()
        _lib.GLib.GError = GError
        _lib.Gio.File.new_for_path.return_value = fp
        lib.return_value = _lib

        # test
        remote = Remote('123', repository)
        remote.import_key(keyring, [key_id])

        # validation
        repository.open.assert_called_once_with()
        _lib.Gio.File.new_for_path.assert_called_once_with(keyring)
        repository.impl.remote_gpg_import.assert_called_once_with(
            remote.id, fp.read.return_value, [key_id])

    @patch('pulp_ostree.plugins.lib.Ref')
    @patch('pulp_ostree.plugins.lib.Lib')
    def test_list_refs(self, lib, ref):
        remote_id = '123'

        summary = {
            'branch:1': 'commit:1',
            'branch:2': 'commit:2'
        }
        commits = [
            ('commit:1', [{'version': 1}]),
            ('commit:2', [{'version': 2}])
        ]

        _lib = Mock()
        lib_repo = Mock()
        lib_repo.remote_list_refs.return_value = (1, summary)
        lib_repo.load_variant.side_effect = commits
        _lib.OSTree.ObjectType.COMMIT = 'COMMIT'
        _lib.OSTree.RepoPullFlags.COMMIT_ONLY = 'COMMIT_ONLY'
        lib.return_value = _lib

        ref_objects = [Mock(), Mock()]
        ref.side_effect = ref_objects

        # test
        remote = Remote(remote_id, Mock(impl=lib_repo))
        remote.open = Mock()
        listed = remote.list_refs(required=True)

        # validation
        lib.assert_called_with()
        remote.open.assert_called_once_with()
        lib_repo.remote_list_refs.assert_called_once_with(remote_id, None)
        lib_repo.pull.assert_called_once_with(
            remote_id,
            sorted(summary.keys()),
            _lib.OSTree.RepoPullFlags.COMMIT_ONLY,
            None,
            None)
        self.assertEqual(
            ref.call_args_list,
            [
                (('branch:1', 'commit:1', {'version': 1}), {}),
                (('branch:2', 'commit:2', {'version': 2}), {}),
            ])
        self.assertEqual(
            lib_repo.load_variant.call_args_list,
            [
                ((_lib.OSTree.ObjectType.COMMIT, 'commit:1'), {}),
                ((_lib.OSTree.ObjectType.COMMIT, 'commit:2'), {}),
            ])
        self.assertEqual(listed, ref_objects)

    @patch('pulp_ostree.plugins.lib.Lib')
    def test_list_refs_no_summary(self, lib):
        remote_id = '123'

        _lib = Mock()
        _lib.GLib.GError = GError
        lib_repo = Mock()
        lib_repo.remote_list_refs.side_effect = GError()
        lib.return_value = _lib

        # test
        remote = Remote(remote_id, Mock(impl=lib_repo))
        remote.open = Mock()
        listed = remote.list_refs()

        # validation
        lib.assert_called_with()
        remote.open.assert_called_once_with()
        lib_repo.remote_list_refs.assert_called_once_with(remote_id, None)
        self.assertEqual(listed, [])

    @patch('pulp_ostree.plugins.lib.Lib')
    def test_list_refs_no_summary_but_required(self, lib):
        remote_id = '123'

        _lib = Mock()
        _lib.GLib.GError = GError
        lib_repo = Mock()
        lib_repo.remote_list_refs.side_effect = GError()
        lib.return_value = _lib

        # test and validation
        remote = Remote(remote_id, Mock(impl=lib_repo))
        self.assertRaises(LibError, remote.list_refs, True)

    @patch('pulp_ostree.plugins.lib.Lib')
    def test_options(self, lib):
        _lib = Mock()
        _lib.GLib.Variant.side_effect = variant
        lib.return_value = _lib

        # test
        remote = Remote('', '')
        remote.ssl_key_path = '/tmp/key'
        remote.ssl_cert_path = '/tmp/certificate'
        remote.ssl_ca_path = '/tmp/ca'
        remote.ssl_validation = True
        remote.gpg_validation = True
        remote.proxy_url = 'http://proxy'
        options = remote.options

        # validation
        self.assertEqual(
            options,
            ('a{sv}', {
                'tls-client-cert-path': ('s', '/tmp/certificate'),
                'tls-client-key-path': ('s', '/tmp/key'),
                'tls-permissive': ('s', 'false'),
                'gpg-verify': ('s', 'true'),
                'tls-ca-path': ('s', '/tmp/ca'),
                'proxy': ('s', 'http://proxy')
            })
        )


class TestDecorator(TestCase):

    @patch('pulp_ostree.plugins.lib.Lib')
    def test_decorator(self, lib):
        _lib = Mock()
        _lib.GLib.GError = GError
        lib.return_value = _lib
        g_error = GError('bad', u'd\xf6g')

        @wrapped
        def function(a, b):
            self.assertEqual(a, 1)
            self.assertEqual(b, 2)
            raise g_error

        try:
            function(1, 2)
        except LibError, le:
            self.assertEqual(le.args[0], repr(g_error).encode('utf-8'))


class TestSummary(TestCase):

    def test_init(self):
        repo = Mock()
        summary = Summary(repo)
        self.assertEqual(summary.repository, repo)

    def test_impl(self):
        repo = Mock()
        summary = Summary(repo)
        self.assertEqual(summary.impl, repo.impl)

    @patch('pulp_ostree.plugins.lib.Lib', Mock())
    def test_open(self):
        repo = Mock()
        summary = Summary(repo)
        summary.open()
        repo.open.assert_called_once_with()

    @patch('pulp_ostree.plugins.lib.Lib', Mock())
    def test_generate(self):
        repo = Mock()

        # test
        summary = Summary(repo)
        summary.generate()

        # validation
        repo.open.assert_called_once_with()
        repo.impl.regenerate_summary.assert_called_once_with(None, None)
