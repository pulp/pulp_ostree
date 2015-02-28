import os

import unittest

from mock import Mock, patch

from pulp.common import constants as pulp_constants

from pulp_ostree.common import constants
from pulp_ostree.plugins.distributors import steps


class TestWebPublisher(unittest.TestCase):

    @patch('pulp_ostree.plugins.distributors.steps.mkdir')
    @patch('pulp_ostree.plugins.distributors.steps.configuration')
    @patch('pulp_ostree.plugins.distributors.steps.AtomicDirectoryPublishStep')
    @patch('pulp_ostree.plugins.distributors.steps.MainStep')
    def test_init(self, mock_main, mock_atomic, mock_configuration, mock_mkdir):
        repo = Mock(id='test', working_dir='/tmp/working')
        conduit = Mock()
        publish_dir = '/tmp/pub'
        master_pub_dir = '/tmp/master/pub'
        config = Mock()
        mock_configuration.get_web_publish_dir.return_value = publish_dir
        mock_configuration.get_master_publish_dir.return_value = master_pub_dir

        # test
        publisher = steps.WebPublisher(repo, conduit, config)

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
        mock_mkdir.assert_called_once_with(publisher.web_working_dir)


class TestMainStep(unittest.TestCase):

    def test_init(self):
        main = steps.MainStep()
        self.assertEqual(main.step_id, constants.PUBLISH_STEP_MAIN)

    @patch('pulp_ostree.plugins.distributors.steps.MainStep._add_ref')
    @patch('pulp_ostree.plugins.distributors.steps.lib')
    @patch('pulp_ostree.plugins.distributors.steps.UnitAssociationCriteria')
    def test_process_main(self, criteria, lib, add_ref):
        working_dir = '/tmp/working'
        units = [
            Mock(
                storage_path='/tmp/path:1',
                unit_key={'branch': 'branch:1', 'commit': 'commit:1'},
                metadata='md:1'),
            Mock(
                storage_path='/tmp/path:2',
                unit_key={'branch': 'branch:2', 'commit': 'commit:2'},
                metadata='md:2'),
        ]
        repo = Mock(id='test', working_dir=working_dir)
        conduit = Mock()
        conduit.get_units.return_value = units
        parent = Mock()
        parent.get_repo.return_value = repo
        parent.working_dir = working_dir
        parent.get_conduit.return_value = conduit

        ostree_repo = Mock()
        lib.Repository.return_value = ostree_repo

        # test
        main = steps.MainStep()
        main.parent = parent
        main.process_main()

        # validation
        path = os.path.join(working_dir, repo.id)
        lib.Repository.assert_called_once_with(path)
        ostree_repo.create.assert_called_once_with()
        criteria.assert_called_once_with(
            unit_sort=[('created', pulp_constants.SORT_DIRECTION[pulp_constants.SORT_ASCENDING])],
            type_ids=[constants.OSTREE_TYPE_ID])
        self.assertEqual(
            ostree_repo.pull_local.call_args_list,
            [
                ((units[0].storage_path, [units[0].unit_key['commit']]), {}),
                ((units[1].storage_path, [units[1].unit_key['commit']]), {}),
            ])
        self.assertEqual(
            add_ref.call_args_list,
            [
                ((path, units[0].unit_key['branch'], units[0].unit_key['commit']), {}),
                ((path, units[1].unit_key['branch'], units[1].unit_key['commit']), {}),
            ])

    @patch('__builtin__.open')
    @patch('pulp_ostree.plugins.distributors.steps.mkdir')
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
