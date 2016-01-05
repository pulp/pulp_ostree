from hashlib import sha256
from unittest import TestCase

from mock import patch, Mock
import mongoengine

from pulp_ostree.common import constants
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

    def test_validate_with_dot(self):
        """
        The base DictField from mongoengine would fail this validation because of the dot in
        the key. Our validator converts the '.' to a '-' before calling the validation code.
        """
        MetadataField().validate({'a.b': 'foo'})

    def test_validate_with_dollar(self):
        """
        Ensures that the parent class validator is still being called.
        """
        self.assertRaises(mongoengine.ValidationError, MetadataField().validate, {'$stuff': 'foo'})

    def test_validate_string(self):
        """
        Ensures that we
        :return:
        """
        self.assertRaises(mongoengine.ValidationError, MetadataField().validate, 'foo')


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

    def test_storage_provider(self):
        unit = Branch()
        self.assertEqual(unit.storage_provider, constants.STORAGE_PROVIDER)

    def test_storage_id(self):
        unit = Branch(remote_id='123')
        self.assertEqual(unit.storage_id, unit.remote_id)
