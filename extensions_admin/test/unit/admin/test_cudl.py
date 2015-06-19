import unittest

from mock import Mock, patch
from pulp.client.arg_utils import InvalidConfig
from pulp.common.constants import REPO_NOTE_TYPE_KEY
from pulp.common.plugins.importer_constants import KEY_FEED
from pulp.devel.unit.util import compare_dict

from pulp_ostree.common import constants
from pulp_ostree.extensions.admin import cudl


class TestRead(unittest.TestCase):

    @patch('__builtin__.open')
    def test_read(self, _open):
        path = '/tmp/xx'
        fp = Mock()
        fp.__enter__ = Mock(return_value=fp)
        fp.__exit__ = Mock()
        _open.return_value = fp

        # test
        content = cudl.read(path)

        # validation
        _open.assert_called_once_with(path)
        fp.__enter__.assert_called_once_with()
        fp.__exit__.assert_called_once_with(None, None, None)
        fp.read.assert_called_once_with()
        self.assertEqual(content, fp.read.return_value)

    @patch('__builtin__.open')
    def test_read_failed(self, _open):
        path = '/tmp/xx'
        _open.side_effect = IOError

        # test
        self.assertRaises(InvalidConfig, cudl.read, path)

        # validation
        _open.assert_called_once_with(path)


class TestCreateOSTreerRepositoryCommand(unittest.TestCase):
    def test_default_notes(self):
        # make sure this value is set and is correct
        self.assertEqual(cudl.CreateOSTreeRepositoryCommand.default_notes.get(REPO_NOTE_TYPE_KEY),
                         constants.REPO_NOTE_OSTREE)

    def test_importer_id(self):
        # this value is required to be set, so just make sure it's correct
        self.assertEqual(cudl.CreateOSTreeRepositoryCommand.IMPORTER_TYPE_ID,
                         constants.WEB_IMPORTER_TYPE_ID)

    def test_describe_distributors(self):
        command = cudl.CreateOSTreeRepositoryCommand(Mock())
        relative_path = '7/x86/standard'
        user_input = {
            cudl.OPT_RELATIVE_PATH.keyword: relative_path
        }
        result = command._describe_distributors(user_input)
        target_result = {'distributor_id': constants.CLI_WEB_DISTRIBUTOR_ID,
                         'distributor_type_id': constants.WEB_DISTRIBUTOR_TYPE_ID,
                         'distributor_config': {
                             constants.DISTRIBUTOR_CONFIG_KEY_RELATIVE_PATH: relative_path
                         },
                         'auto_publish': True}
        compare_dict(result[0], target_result)

    def test_describe_distributors_using_feed(self):
        command = cudl.CreateOSTreeRepositoryCommand(Mock())
        relative_path = '/7/x86/standard'
        feed_url = 'http://planet.com%s' % relative_path
        user_input = {
            command.options_bundle.opt_feed.keyword: feed_url
        }
        result = command._describe_distributors(user_input)
        target_result = {'distributor_id': constants.CLI_WEB_DISTRIBUTOR_ID,
                         'distributor_type_id': constants.WEB_DISTRIBUTOR_TYPE_ID,
                         'distributor_config': {
                             constants.DISTRIBUTOR_CONFIG_KEY_RELATIVE_PATH: relative_path
                         },
                         'auto_publish': True}
        compare_dict(result[0], target_result)

    def test_describe_distributors_override_auto_publish(self):
        command = cudl.CreateOSTreeRepositoryCommand(Mock())
        user_input = {
            'auto-publish': False
        }
        result = command._describe_distributors(user_input)
        self.assertEquals(result[0]["auto_publish"], False)

    @patch('pulp_ostree.extensions.admin.cudl.read')
    def test_describe_importers(self, read):
        command = cudl.CreateOSTreeRepositoryCommand(Mock())
        read.side_effect = hash
        paths = ['path-1', 'path-2']
        branches = ['apple', 'orange']
        user_input = {
            'branch': branches,
            'gpg-key': paths
        }
        result = command._parse_importer_config(user_input)
        self.assertEqual(
            read.call_args_list,
            [((p,), {}) for p in paths])
        target_result = {
            constants.IMPORTER_CONFIG_KEY_BRANCHES: branches,
            constants.IMPORTER_CONFIG_KEY_GPG_KEYS: map(hash, paths)
        }
        compare_dict(result, target_result)


class TestUpdateOSTreeRepositoryCommand(unittest.TestCase):

    def setUp(self):
        self.context = Mock()
        self.context.config = {'output': {'poll_frequency_in_seconds': 3}}
        self.command = cudl.UpdateOSTreeRepositoryCommand(self.context)
        self.command.poll = Mock()
        self.mock_repo_response = Mock(response_body={})
        self.context.server.repo.repository.return_value = self.mock_repo_response

    @patch('pulp_ostree.extensions.admin.cudl.read')
    def test_run_with_importer_config(self, read):
        read.side_effect = hash
        feed = 'http://'
        paths = ['path-1', 'path-2']
        branches = ['apple', 'orange']
        user_input = {
            'repo-id': 'foo-repo',
            KEY_FEED: feed,
            'branch': branches,
            'gpg-key': paths
        }
        self.command.run(**user_input)

        expected_importer_config = {
            KEY_FEED: feed,
            constants.IMPORTER_CONFIG_KEY_BRANCHES: branches,
            constants.IMPORTER_CONFIG_KEY_GPG_KEYS: map(hash, paths)
        }

        self.context.server.repo.update.assert_called_once_with('foo-repo', {},
                                                                expected_importer_config, None)

    def test_repo_update_distributors(self):
        user_input = {
            'auto-publish': False,
            'repo-id': 'foo-repo'
        }
        self.command.run(**user_input)

        repo_config = {}
        dist_config = {constants.CLI_WEB_DISTRIBUTOR_ID: {'auto_publish': False}}
        self.context.server.repo.update.assert_called_once_with('foo-repo', repo_config,
                                                                None, dist_config)

    def test_repo_update_importer_remove_branches(self):
        user_input = {
            'branch': [''],
            'repo-id': 'foo-repo'
        }
        self.command.run(**user_input)

        repo_config = {}
        importer_config = {'branches': None}
        self.context.server.repo.update.assert_called_once_with('foo-repo', repo_config,
                                                                importer_config, None)

    def test_repo_update_importer_remove_gpg_keys(self):
        repo_id = 'test'
        user_input = {
            'gpg-key': [''],
            'repo-id': repo_id
        }
        self.command.run(**user_input)

        repo_config = {}
        importer_config = {
            constants.IMPORTER_CONFIG_KEY_GPG_KEYS: None
        }
        self.context.server.repo.update.assert_called_once_with(
            repo_id, repo_config, importer_config, None)


class TestListOSTreeRepositoriesCommand(unittest.TestCase):
    def setUp(self):
        self.context = Mock()
        self.context.config = {'output': {'poll_frequency_in_seconds': 3}}

    def test_get_all_repos(self):
        self.context.server.repo.repositories.return_value.response_body = 'foo'
        command = cudl.ListOSTreeRepositoriesCommand(self.context)
        result = command._all_repos({'bar': 'baz'})
        self.context.server.repo.repositories.assert_called_once_with({'bar': 'baz'})
        self.assertEquals('foo', result)

    def test_get_all_repos_caches_results(self):
        command = cudl.ListOSTreeRepositoriesCommand(self.context)
        command.all_repos_cache = 'foo'
        result = command._all_repos({'bar': 'baz'})
        self.assertFalse(self.context.server.repo.repositories.called)
        self.assertEquals('foo', result)

    def test_get_repositories(self):
        # Setup
        repos = [
            {
                'id': 'matching',
                'notes': {REPO_NOTE_TYPE_KEY: constants.REPO_NOTE_OSTREE, },
                'importers': [
                    {'config': {}}
                ],
                'distributors': [
                    {'id': constants.CLI_WEB_DISTRIBUTOR_ID}
                ]
            },
            {'id': 'non-rpm-repo',
             'notes': {}}
        ]
        self.context.server.repo.repositories.return_value.response_body = repos

        # Test
        command = cudl.ListOSTreeRepositoriesCommand(self.context)
        repos = command.get_repositories({})

        # Verify
        self.assertEqual(1, len(repos))
        self.assertEqual(repos[0]['id'], 'matching')

    def test_get_repositories_no_details(self):
        # Setup
        repos = [
            {
                'id': 'foo',
                'display_name': 'bar',
                'notes': {REPO_NOTE_TYPE_KEY: constants.REPO_NOTE_OSTREE, }
            }
        ]
        self.context.server.repo.repositories.return_value.response_body = repos

        # Test
        command = cudl.ListOSTreeRepositoriesCommand(self.context)
        repos = command.get_repositories({})

        # Verify
        self.assertEqual(1, len(repos))
        self.assertEqual(repos[0]['id'], 'foo')
        self.assertTrue('importers' not in repos[0])
        self.assertTrue('distributors' not in repos[0])

    def test_get_other_repositories(self):
        # Setup
        repos = [
            {
                'repo_id': 'matching',
                'notes': {REPO_NOTE_TYPE_KEY: constants.REPO_NOTE_OSTREE, },
                'distributors': [
                    {'id': constants.CLI_WEB_DISTRIBUTOR_ID}
                ]
            },
            {
                'repo_id': 'non-ostree-repo-1',
                'notes': {}
            }
        ]
        self.context.server.repo.repositories.return_value.response_body = repos

        # Test
        command = cudl.ListOSTreeRepositoriesCommand(self.context)
        repos = command.get_other_repositories({})

        # Verify
        self.assertEqual(1, len(repos))
        self.assertEqual(repos[0]['repo_id'], 'non-ostree-repo-1')
