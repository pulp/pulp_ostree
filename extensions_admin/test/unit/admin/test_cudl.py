import unittest

from mock import Mock
from pulp.common.constants import REPO_NOTE_TYPE_KEY
from pulp.common.plugins.importer_constants import KEY_FEED
from pulp.devel.unit.util import compare_dict

from pulp_ostree.common import constants
from pulp_ostree.extensions.admin import cudl


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
        user_input = {}
        result = command._describe_distributors(user_input)
        target_result = {'distributor_id': constants.CLI_WEB_DISTRIBUTOR_ID,
                         'distributor_type_id': constants.WEB_DISTRIBUTOR_TYPE_ID,
                         'distributor_config': {},
                         'auto_publish': True}
        compare_dict(result[0], target_result)

    def test_describe_distributors_override_auto_publish(self):
        command = cudl.CreateOSTreeRepositoryCommand(Mock())
        user_input = {
            'auto-publish': False
        }
        result = command._describe_distributors(user_input)
        self.assertEquals(result[0]["auto_publish"], False)


class TestUpdateOSTreeRepositoryCommand(unittest.TestCase):

    def setUp(self):
        self.context = Mock()
        self.context.config = {'output': {'poll_frequency_in_seconds': 3}}
        self.command = cudl.UpdateOSTreeRepositoryCommand(self.context)
        self.command.poll = Mock()
        self.mock_repo_response = Mock(response_body={})
        self.context.server.repo.repository.return_value = self.mock_repo_response
        self.unit_search_command = Mock(response_body=[{u'metadata': {u'image_id': 'bar123'}}])
        self.context.server.repo_unit.search.return_value = self.unit_search_command

    def test_run_with_importer_config(self):
        user_input = {
            'repo-id': 'foo-repo',
            KEY_FEED: 'blah',
            constants.IMPORTER_CONFIG_KEY_BRANCHES: ['apple', 'peach']
        }
        self.command.run(**user_input)

        expected_importer_config = {KEY_FEED: 'blah',
                                    constants.IMPORTER_CONFIG_KEY_BRANCHES: ['apple', 'peach']}

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


class TestListDockerRepositoriesCommand(unittest.TestCase):
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
