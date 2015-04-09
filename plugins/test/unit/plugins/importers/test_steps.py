import os
import errno

from unittest import TestCase

from mock import patch, Mock, ANY

from pulp.common.plugins import importer_constants
from pulp.server.exceptions import PulpCodedException

from pulp_ostree.plugins.lib import LibError
from pulp_ostree.plugins.importers.steps import Main, Create, Pull, Add
from pulp_ostree.common.model import Unit
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
        step = Main(repo=repo, conduit=conduit, config=config, working_dir=working_dir)

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

    @patch('pulp_ostree.plugins.importers.steps.lib')
    def test_init_repository(self, fake_lib):
        url = 'url-123'
        remote_id = 'remote-123'
        path = 'root/path-123'

        fake_lib.LibError = LibError
        fake_lib.Repository.return_value.open.side_effect = LibError

        # test
        Create._init_repository(path, remote_id, url)

        # validation
        fake_lib.Repository.assert_called_once_with(path)
        fake_lib.Repository.return_value.create.assert_called_once_with()
        fake_lib.Repository.return_value.add_remote.assert_called_once_with(remote_id, url)

    @patch('pulp_ostree.plugins.importers.steps.lib')
    def test_init_repository_exists(self, fake_lib):
        url = 'url-123'
        remote_id = 'remote-123'
        path = 'root/path-123'

        # test
        Create._init_repository(path, remote_id, url)

        # validation
        fake_lib.Repository.assert_called_once_with(path)
        fake_lib.Repository.return_value.open.assert_called_once_with()
        self.assertFalse(fake_lib.Repository.return_value.add_remote.called)

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

    @patch('pulp_ostree.plugins.importers.steps.mkdir')
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
        report = Mock(fetched=1, requested=2, percent=50)

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
        self.assertEqual(step.progress_details, 'branch: branch-1 fetching 1/2 50%')

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

    @patch('pulp_ostree.plugins.importers.steps.lib')
    @patch('pulp_ostree.plugins.importers.steps.model')
    @patch('pulp_ostree.plugins.importers.steps.Add.link')
    @patch('pulp_ostree.plugins.importers.steps.Unit')
    def test_process_main(self, fake_unit, fake_link, fake_model, fake_lib):
        remote_id = 'remote-1'
        commits = [
            Mock(),
            Mock()
        ]
        refs = [
            Mock(path='branch:1', commit='commit:1', metadata='md:1'),
            Mock(path='branch:2', commit='commit:2', metadata='md:2'),
            Mock(path='branch:3', commit='commit:3', metadata='md:3')
        ]
        units = [
            Mock(key='key:1', metadata=refs[0].metadata, storage_path='path:1'),
            Mock(key='key:2', metadata=refs[1].metadata, storage_path='path:2')
        ]
        pulp_units = [
            Mock(),
            Mock()
        ]

        branches = [r.path for r in refs[:-1]]

        repository = Mock()
        repository.list_refs.return_value = refs
        fake_lib.Repository.return_value = repository

        fake_model.Commit.side_effect = commits
        fake_model.Unit.side_effect = units

        fake_unit.side_effect = pulp_units

        fake_conduit = Mock()

        # test
        step = Add()
        step.parent = Mock(remote_id=remote_id, storage_path='/tmp/xyz', branches=branches)
        step.get_conduit = Mock(return_value=fake_conduit)
        step.process_main()

        # validation
        fake_lib.Repository.assert_called_once_with(step.parent.storage_path)
        self.assertEqual(
            fake_model.Commit.call_args_list,
            [
                (('commit:1', 'md:1'), {}),
                (('commit:2', 'md:2'), {}),
            ])
        self.assertEqual(
            fake_model.Unit.call_args_list,
            [
                ((remote_id, 'branch:1', commits[0]), {}),
                ((remote_id, 'branch:2', commits[1]), {}),
            ])
        self.assertEqual(
            fake_link.call_args_list,
            [
                ((units[0],), {}),
                ((units[1],), {}),
            ])
        self.assertEqual(
            fake_unit.call_args_list,
            [
                ((Unit.TYPE_ID, units[0].key, units[0].metadata, units[0].storage_path), {}),
                ((Unit.TYPE_ID, units[1].key, units[1].metadata, units[1].storage_path), {}),
            ])
        self.assertEqual(
            fake_conduit.save_unit.call_args_list,
            [
                ((pulp_units[0],), {}),
                ((pulp_units[1],), {}),
            ])

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
