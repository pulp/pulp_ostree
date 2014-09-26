import os
import errno

from unittest import TestCase

from mock import patch, Mock, ANY

from pulp.common.plugins import importer_constants
from pulp.server.exceptions import PulpCodedException

from pulp_ostree.plugins.lib import LibError
from pulp_ostree.plugins.importers.steps import Main, Create, Pull, Add
from pulp_ostree.common import constants, errors


class TestMainStep(TestCase):

    @patch('pulp_ostree.common.model.generate_remote_id')
    def test_init(self, fake_generate):
        repo = Mock()
        conduit = Mock()
        working_dir = 'dir-123'
        url = 'url-123'
        branches = ['branch-1', 'branch-2']
        digest = 'digest-123'
        fake_generate.return_value = digest
        config = {
            importer_constants.KEY_FEED: url,
            constants.IMPORTER_CONFIG_KEY_BRANCHES: branches
        }

        # test
        step = Main(repo, conduit, config, working_dir)

        # validation
        self.assertEqual(step.step_id, constants.IMPORT_STEP_MAIN)
        self.assertEqual(step.repo, repo)
        self.assertEqual(step.conduit, conduit)
        self.assertEqual(step.config, config)
        self.assertEqual(step.working_dir, working_dir)
        self.assertEqual(step.plugin_type, constants.WEB_IMPORTER_TYPE_ID)
        self.assertEqual(step.feed_url, url)
        self.assertEqual(step.remote_id, digest)
        self.assertEqual(step.branches, branches)
        self.assertEqual(step.storage_path,
                         os.path.join(constants.SHARED_STORAGE, digest, 'content'))

        self.assertEqual(len(step.children), 3)
        self.assertTrue(isinstance(step.children[0], Create))
        self.assertTrue(isinstance(step.children[1], Pull))
        self.assertTrue(isinstance(step.children[2], Add))


class TestCreate(TestCase):

    @patch('os.makedirs')
    def test_mkdir(self, fake_mkdir):
        path = 'path-123'
        Create.mkdir(path)

        # already existing
        fake_mkdir.assert_called_once_with(path)
        fake_mkdir.side_effect = OSError(errno.EEXIST, path)

        # other error
        Create.mkdir(path)
        fake_mkdir.side_effect = OSError(errno.EPERM, path)
        self.assertRaises(OSError, Create.mkdir, path)

    @patch('pulp_ostree.plugins.importers.steps.lib')
    def test_init_repository(self, fake_lib):
        url = 'url-123'
        remote_id = 'remote-123'
        path = 'root/path-123'

        # test
        Create._init_repository(path, remote_id, url)

        # validation
        fake_lib.Repository.assert_called_once_with(path)
        fake_lib.Repository().create.assert_called_once_with()
        fake_lib.Repository().add_remote.assert_called_once_with(remote_id, url)

    @patch('pulp_ostree.plugins.importers.steps.lib')
    def test_init_repository_exception(self, fake_lib):
        fake_lib.LibError = LibError
        fake_lib.Repository.side_effect = LibError
        try:
            Create._init_repository('', '', '')
            self.assertTrue(False, msg='Create exception expected')
        except PulpCodedException, pe:
            self.assertEqual(pe.error_code, errors.OST0001)

    def test_init(self):
        step = Create()
        self.assertEqual(step.step_id, constants.IMPORT_STEP_CREATE_REPOSITORY)
        self.assertTrue(step.description is not None)

    @patch('pulp_ostree.plugins.importers.steps.Create.mkdir')
    def test_process_main(self, fake_mkdir):
        url = 'url-123'
        remote_id = 'remote-123'
        path = 'root/path-123'

        # test
        step = Create()
        step.parent = Mock(storage_path=path, feed_url=url, remote_id=remote_id)
        step._init_repository = Mock()
        step.process_main()

        # validation
        self.assertEqual(
            fake_mkdir.call_args_list,
            [
                ((path,), {}),
                ((os.path.join(os.path.dirname(path), constants.LINKS_DIR),), {})
            ])
        step._init_repository.assert_called_with(path, remote_id, url)


class TestPull(TestCase):

    def test_init(self):
        step = Pull()
        self.assertEqual(step.step_id, constants.IMPORT_STEP_PULL)
        self.assertTrue(step.description is not None)

    def test_process_main(self):
        remote_id = 'remote-123'
        path = 'root/path-123'
        branches = ['branch-1', 'branch-2']

        # test
        step = Pull()
        step.parent = Mock(storage_path=path, remote_id=remote_id, branches=branches)
        step._pull = Mock()
        step.process_main()

        # validation
        self.assertEqual(
            step._pull.call_args_list,
            [
                ((path, remote_id, branches[0]), {}),
                ((path, remote_id, branches[1]), {}),
            ])

    @patch('pulp_ostree.plugins.importers.steps.lib')
    def test_pull(self, fake_lib):
        remote_id = 'remote-123'
        path = 'root/path-123'
        branch = 'branch-1'
        repo = Mock()
        fake_lib.Repository.return_value = repo
        report = Mock()

        def fake_pull(remote_id, branch, listener):
            listener(report)

        repo.pull.side_effect = fake_pull

        # test
        step = Pull()
        step.report_progress = Mock()
        step._pull(path, remote_id, branch)

        # validation
        fake_lib.Repository.assert_called_once_with(path)
        repo.pull.assert_called_once_with(remote_id, [branch], ANY)
        step.report_progress.assert_called_with(force=True)

    @patch('pulp_ostree.plugins.importers.steps.lib')
    def test_pull_raising_exception(self, fake_lib):
        fake_lib.LibError = LibError
        fake_lib.Repository.return_value.pull.side_effect = LibError
        try:
            step = Pull()
            step._pull('', '', '')
            self.assertTrue(False, msg='Pull exception expected')
        except PulpCodedException, pe:
            self.assertEqual(pe.error_code, errors.OST0002)


class TestAdd(TestCase):

    def test_init(self):
        step = Add()
        self.assertEqual(step.step_id, constants.IMPORT_STEP_ADD_UNITS)
        self.assertTrue(step.description is not None)

    @patch('pulp_ostree.plugins.importers.steps.Unit')
    @patch('pulp_ostree.plugins.importers.steps.datetime')
    @patch('pulp_ostree.common.model.Repository')
    @patch('pulp_ostree.common.model.Refs')
    def test_process_main(self, fake_refs, fake_repo, dt, fake_unit):
        utc_now = 'utc-now'
        dt.utcnow.return_value = utc_now
        refs = Mock()
        fake_refs.return_value = refs
        heads = [Mock(), Mock()]
        remote_id = 'remote-1'
        repo = Mock(TYPE_ID='type-id',
                    unit_key='unit-key',
                    metadata='md',
                    storage_path='storage-path')
        fake_repo.return_value = repo
        unit = Mock()
        fake_unit.return_value = unit
        fake_conduit = Mock()

        # test
        step = Add()
        step.find_branches = Mock(return_value=heads)
        step.parent = Mock(remote_id=remote_id)
        step.link = Mock()
        step.get_conduit = Mock(return_value=fake_conduit)
        step.process_main()

        # validation
        dt.utcnow.assert_called_once_with()
        fake_refs.assert_called_once_with()
        step.find_branches.assert_called_once_with()
        self.assertEqual(
            refs.add_head.call_args_list,
            [
                ((heads[0],), {}),
                ((heads[1],), {}),
            ])
        fake_repo.assert_called_once_with(remote_id, fake_refs.return_value, utc_now)
        step.link.assert_called_once_with(repo)
        fake_unit.assert_called_once_with(
            repo.TYPE_ID, repo.unit_key, repo.metadata, repo.storage_path)
        fake_conduit.save_unit.assert_called_once_with(unit)

    @patch('os.symlink')
    def test_link(self, fake_link):
        target = 'path-1'
        link_path = 'path-2'
        step = Add()
        unit = Mock(storage_path=link_path)
        step.parent = Mock(storage_path=target)
        step.link(unit)
        fake_link.assert_called_with(target, link_path)

    @patch('os.readlink')
    @patch('os.path.islink')
    @patch('os.symlink')
    def test_link_exists(self, fake_link, fake_islink, fake_readlink):
        target = 'path-1'
        link_path = 'path-2'
        step = Add()
        unit = Mock(storage_path=link_path)
        step.parent = Mock(storage_path=target)
        fake_islink.return_value = True
        fake_readlink.return_value = target
        fake_link.side_effect = OSError(errno.EEXIST, link_path)

        # test
        step.link(unit)

        # validation
        fake_islink.assert_called_with(link_path)
        fake_readlink.assert_called_with(link_path)

    @patch('os.readlink')
    @patch('os.path.islink')
    @patch('os.symlink')
    def test_link_exists_not_link(self, fake_link, fake_islink, fake_readlink):
        target = 'path-1'
        link_path = 'path-2'
        step = Add()
        unit = Mock(storage_path=link_path)
        step.parent = Mock(storage_path=target)
        fake_islink.return_value = False
        fake_readlink.return_value = target
        fake_link.side_effect = OSError(errno.EEXIST, link_path)

        # test
        self.assertRaises(OSError, step.link, unit)

        # validation
        fake_islink.assert_called_with(link_path)
        self.assertFalse(fake_readlink.called)

    @patch('os.readlink')
    @patch('os.path.islink')
    @patch('os.symlink')
    def test_link_exists_wrong_target(self, fake_link, fake_islink, fake_readlink):
        target = 'path-1'
        link_path = 'path-2'
        step = Add()
        unit = Mock(storage_path=link_path)
        step.parent = Mock(storage_path=target)
        fake_islink.return_value = True
        fake_readlink.return_value = 'not-target'
        fake_link.side_effect = OSError(errno.EEXIST, link_path)

        # test
        self.assertRaises(OSError, step.link, unit)

        # validation
        fake_islink.assert_called_with(link_path)
        fake_readlink.assert_called_with(link_path)

    @patch('os.readlink')
    @patch('os.path.islink')
    @patch('os.symlink')
    def test_link_error(self, fake_link, fake_islink, fake_readlink):
        target = 'path-1'
        link_path = 'path-2'
        step = Add()
        unit = Mock(storage_path=link_path)
        step.parent = Mock(storage_path=target)
        fake_link.side_effect = OSError(errno.EPERM, link_path)

        # test
        self.assertRaises(OSError, step.link, unit)

        # validation
        self.assertFalse(fake_islink.called)
        self.assertFalse(fake_readlink.called)

    @patch('pulp_ostree.common.model.Head')
    @patch('__builtin__.open')
    @patch('os.walk')
    def test_find_branches(self, fake_walk, fake_open, fake_head):
        fp = Mock()
        fp.__enter__ = Mock(return_value=fp)
        fp.__exit__ = Mock()
        fp.read.side_effect = ['hash-1', 'hash-2']
        fake_open.return_value = fp
        path = '/path-1'
        step = Add()
        step.parent = Mock(storage_path=path)
        heads = [Mock(), Mock()]
        fake_head.side_effect = heads
        tree = [
            ('/path-1/refs/heads', ['fedora'], []),
            ('/path-1/refs/heads/fedora', ['f21'], []),
            ('/path-1/refs/heads/fedora/f21', ['i386', 'x86_64'], []),
            ('/path-1/refs/heads/fedora/f21/i386', [], ['os']),
            ('/path-1/refs/heads/fedora/f21/x86_64', [], ['os']),
        ]
        fake_walk.return_value = tree

        # test
        branches = list(step.find_branches())

        # validation
        self.assertEqual(
            fake_open.call_args_list,
            [
                (('/path-1/refs/heads/fedora/f21/i386/os',), {}),
                (('/path-1/refs/heads/fedora/f21/x86_64/os',), {})
            ])
        fake_walk.assert_called_once_with(os.path.join(path, 'refs', 'heads'))
        self.assertEqual(
            fake_head.call_args_list,
            [
                (('fedora/f21/i386/os', 'hash-1'), {}),
                (('fedora/f21/x86_64/os', 'hash-2'), {})
            ])
        self.assertEqual(len(branches), 2)
        self.assertEqual(branches, heads)
