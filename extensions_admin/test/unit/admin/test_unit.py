from unittest import TestCase

from mock import Mock

from pulp_ostree.common.constants import OSTREE_TYPE_ID
from pulp_ostree.extensions.admin.unit import format_unit, CopyCommand, RemoveCommand


class TestFunctions(TestCase):

    def test_format(self):
        unit = dict(remote_id='test-id', digest='test-digest')
        formatted = format_unit(unit)
        self.assertEqual(formatted, 'remote_id: test-id digest: test-digest')


class TestCopyCommand(TestCase):

    def test_copy_command(self):
        context = Mock()
        context.config = {
            'output': {'poll_frequency_in_seconds': 1}
        }
        command = CopyCommand(context)
        fn = command.get_formatter_for_type(OSTREE_TYPE_ID)
        self.assertEqual(fn, format_unit)


class TestRemoveCommand(TestCase):

    def test_copy_command(self):
        context = Mock()
        context.config = {
            'output': {'poll_frequency_in_seconds': 1}
        }
        command = RemoveCommand(context)
        fn = command.get_formatter_for_type(OSTREE_TYPE_ID)
        self.assertEqual(fn, format_unit)
