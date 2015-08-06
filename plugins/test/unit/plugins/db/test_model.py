from hashlib import sha256
from unittest import TestCase

from mock import patch, Mock

from pulp_ostree.plugins.db.model import Branch, MetadataField, generate_remote_id


class TestUtils(TestCase):

    def test_generate_remote_id(self):
        url = 'url-test'
        remote_id = generate_remote_id(url)
        h = sha256()
        h.update(url)
        self.assertEqual(remote_id, h.hexdigest())


class TestMetadataField(TestCase):

    def test_to_mongo(self):
        _in = {
            'elmer.j.fudd': 1,
            'bugs.bunny': 2,
            'other': 3
        }
        _out = {
            'elmer-j-fudd': 1,
            'bugs-bunny': 2,
            'other': 3
        }
        field = MetadataField()
        self.assertEqual(field.to_mongo(_in), _out)


class TestBranch(TestCase):

    @patch('pulp_ostree.plugins.db.model.datetime')
    def test_pre_save_signal(self, datetime):
        sender = Mock()
        kwargs = {'a': 1, 'b': 2}

        # test
        unit = Branch()
        with patch('pulp.server.db.model.SharedContentUnit.pre_save_signal') as base:
            unit.pre_save_signal(sender, unit, **kwargs)

        # validation
        base.assert_called_once_with(sender, unit, **kwargs)
        self.assertEqual(unit.created, datetime.utcnow.return_value)

    def test_storage_id(self):
        unit = Branch(remote_id='123')
        self.assertEqual(unit.storage_id, unit.remote_id)
