import unittest

import mock

from pulp.client.commands.unit import UnitCopyCommand, UnitRemoveCommand
from pulp.client.commands.repo.cudl import CreateRepositoryCommand, DeleteRepositoryCommand
from pulp.client.commands.repo.cudl import UpdateRepositoryCommand
from pulp.client.commands.repo.cudl import ListRepositoriesCommand
from pulp.client.commands.repo.sync_publish import PublishStatusCommand,\
    RunPublishRepositoryCommand, RunSyncRepositoryCommand
from pulp.client.extensions.core import PulpCli

from pulp_ostree.extensions.admin import pulp_cli


class TestInitialize(unittest.TestCase):
    def test_structure(self):
        context = mock.MagicMock()
        context.config = {
            'filesystem': {'upload_working_dir': '/a/b/c'},
            'output': {'poll_frequency_in_seconds': 3}
        }
        context.cli = PulpCli(context)

        # create the tree of commands and sections
        pulp_cli.initialize(context)

        # verify that sections exist and have the right commands
        ostree_section = context.cli.root_section.subsections['ostree']

        repo_section = ostree_section.subsections['repo']
        self.assertTrue(isinstance(repo_section.commands['create'], CreateRepositoryCommand))
        self.assertTrue(isinstance(repo_section.commands['delete'], DeleteRepositoryCommand))
        self.assertTrue(isinstance(repo_section.commands['update'], UpdateRepositoryCommand))
        self.assertTrue(isinstance(repo_section.commands['list'], ListRepositoriesCommand))
        self.assertTrue(isinstance(repo_section.commands['copy'], UnitCopyCommand))
        self.assertTrue(isinstance(repo_section.commands['remove'], UnitRemoveCommand))

        section = repo_section.subsections['sync']
        self.assertTrue(isinstance(section.commands['run'], RunSyncRepositoryCommand))

        section = repo_section.subsections['publish']
        self.assertTrue(isinstance(section.commands['status'], PublishStatusCommand))
        self.assertTrue(isinstance(section.commands['run'], RunPublishRepositoryCommand))
