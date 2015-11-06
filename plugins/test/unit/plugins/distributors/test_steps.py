import os

import unittest

from mock import Mock, patch

from pulp_ostree.common import constants
from pulp_ostree.plugins.distributors import steps


MODULE = 'pulp_ostree.plugins.distributors.steps'


class TestWebPublisher(unittest.TestCase):

    @patch(MODULE + '.mkdir')
    @patch(MODULE + '.configuration')
    @patch(MODULE + '.AtomicDirectoryPublishStep')
    @patch(MODULE + '.MainStep')
    def test_init(self, mock_main, mock_atomic, mock_configuration, mock_mkdir):
        repo = Mock(repo_id='test', working_dir='/tmp/working')
        conduit = Mock()
        publish_dir = '/tmp/pub'
        master_pub_dir = '/tmp/master/pub'
        config = Mock()
        mock_configuration.get_web_publish_dir.return_value = publish_dir
        mock_configuration.get_master_publish_dir.return_value = master_pub_dir

        # test
        publisher = steps.WebPublisher(repo, conduit, config, working_dir='/tmp/working')

        # validation
        mock_atomic.assert_called_once_with(
            '/tmp/working',
            [('test', '/tmp/pub')],
            '/tmp/master/pub',
            step_type=constants.PUBLISH_STEP_OVER_HTTP)
        mock_main.assert_called_once_with()
        self.assertEquals(
            publisher.children,
            [mock_main.return_value, mock_atomic.return_value])
        mock_mkdir.assert_called_once_with(publisher.publish_dir)


class TestMainStep(unittest.TestCase):

    def test_init(self):
        main = steps.MainStep()
        self.assertEqual(main.step_id, constants.PUBLISH_STEP_MAIN)

    @patch(MODULE + '.MainStep._add_ref')
    @patch(MODULE + '.lib')
    def test_process_main(self, lib, add_ref):
        units = [
            Mock(branch='branch:1', commit='commit:1', storage_path='path:1'),
            Mock(branch='branch:2', commit='commit:2', storage_path='path:2'),
        ]
        repository = Mock()
        lib.Repository.return_value = repository
        parent = Mock(publish_dir='/tmp/dir-1234')

        # test
        main = steps.MainStep()
        main._get_units = Mock(return_value=units)
        main.parent = parent
        main.process_main()

        # validation
        lib.Repository.assert_called_once_with(parent.publish_dir)
        repository.create.assert_called_once_with()
        self.assertEqual(
            repository.pull_local.call_args_list,
            [
                ((u.storage_path, [u.commit]), {}) for u in units
            ])
        self.assertEqual(
            add_ref.call_args_list,
            [
                ((parent.publish_dir, u.branch, u.commit), {}) for u in units
            ])
        lib.Summary.assert_called_once_with(repository)
        lib.Summary.return_value.generate.assert_called_once_with()

    @patch(MODULE + '.Q')
    @patch(MODULE + '.find_repo_content_units')
    def test_get_units(self, find, q):
        associations = [
            Mock(unit=Mock(name='0', branch='branch:1', created=0)),
            Mock(unit=Mock(name='1', branch='branch:1', created=1)),
            Mock(unit=Mock(name='2', branch='branch:2', created=2)),
            Mock(unit=Mock(name='3', branch='branch:2', created=3)),
            Mock(unit=Mock(name='4', branch='branch:2', created=4)),
            Mock(unit=Mock(name='5', branch='branch:3', created=5)),
        ]

        find.return_value = reversed(associations)

        parent = Mock()
        parent.get_repo.return_value = Mock(id='id-1234')

        # test
        main = steps.MainStep()
        main.parent = parent
        unit_list = main._get_units()

        # validation
        q.assert_called_once_with(_content_type_id=constants.OSTREE_TYPE_ID)
        find.assert_called_once_with(
            parent.get_repo.return_value, repo_content_unit_q=q.return_value)
        self.assertEqual(
            sorted(unit_list),
            sorted(
                [
                    associations[1].unit,
                    associations[4].unit,
                    associations[5].unit
                ]))

    @patch('__builtin__.open')
    @patch(MODULE + '.mkdir')
    def test_add_ref(self, mkdir, _open):
        path = '/tmp/path'
        branch = 'fedora/x86/core'
        commit = 'test_commit'

        fp = Mock()
        fp.__enter__ = Mock(return_value=fp)
        fp.__exit__ = Mock()
        _open.return_value = fp

        # test
        steps.MainStep._add_ref(path, branch, commit)

        # validation
        path = os.path.join(path, 'refs', 'heads', os.path.dirname(branch))
        mkdir.assert_called_once_with(path)
        path = os.path.join(path, os.path.basename(branch))
        _open.assert_called_once_with(path, 'w+')
        fp.write.assert_called_once_with(commit)
        self.assertTrue(fp.__enter__.called)
        self.assertTrue(fp.__exit__.called)
