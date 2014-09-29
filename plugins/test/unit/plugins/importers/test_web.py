from unittest import TestCase

from mock import patch, Mock

from pulp_ostree.common import constants
from pulp_ostree.plugins.importers.web import WebImporter, entry_point


class TestImporter(TestCase):

    @patch('pulp_ostree.plugins.importers.web.read_json_config')
    def test_entry_point(self, read_json_config):
        plugin, cfg = entry_point()
        read_json_config.assert_called_with(constants.IMPORTER_CONFIG_FILE_PATH)
        self.assertEqual(plugin, WebImporter)
        self.assertEqual(cfg, read_json_config.return_value)

    def test_metadata(self):
        md = WebImporter.metadata()
        self.assertEqual(md['id'], constants.WEB_IMPORTER_TYPE_ID)
        self.assertEqual(md['types'], [constants.OSTREE_TYPE_ID])
        self.assertTrue(len(md['display_name']) > 0)

    def test_validate_config(self):
        importer = WebImporter()
        result = importer.validate_config(Mock(), Mock())
        self.assertEqual(result, (True, ''))

    @patch('pulp_ostree.plugins.importers.web.Main')
    def test_sync(self, main):
        repo = Mock()
        conduit = Mock()
        config = Mock()

        # test
        importer = WebImporter()
        report = importer.sync_repo(repo, conduit, config)

        # validation
        main.assert_called_once_with(repo, conduit, config)
        main.return_value.process_lifecycle.assert_called_once_with()
        self.assertEqual(report, main.return_value.process_lifecycle.return_value)

    @patch('sys.exit')
    def test_cancel(self, _exit):
        importer = WebImporter()
        importer.cancel_sync_repo()
        _exit.assert_called_once_with(0)
