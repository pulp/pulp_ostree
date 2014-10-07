import ConfigParser
import os
import shutil
import tempfile
import unittest

from mock import Mock, patch

from pulp.devel.unit.util import touch
from pulp.common import constants as pulp_constants
from pulp.plugins.model import Repository, Unit
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.conduits.repo_publish import RepoPublishConduit

from pulp_ostree.common import constants
from pulp_ostree.plugins.distributors import steps


class TestWebPublisher(unittest.TestCase):

    def setUp(self):
        self.working_directory = tempfile.mkdtemp()
        self.publish_dir = os.path.join(self.working_directory, 'publish')
        self.repo_working = os.path.join(self.working_directory, 'work')

        self.repo = Mock(id='foo', working_dir=self.repo_working)
        self.config = PluginCallConfiguration({constants.DISTRIBUTOR_CONFIG_KEY_PUBLISH_DIRECTORY:
                                              self.publish_dir}, {})

    def tearDown(self):
        shutil.rmtree(self.working_directory)

    @patch('pulp_ostree.plugins.distributors.steps.AtomicDirectoryPublishStep')
    @patch('pulp_ostree.plugins.distributors.steps.CreateEmptyOSTreeStep')
    def test_init_empty(self, mock_empty, mock_atomic):
        mock_conduit = Mock()
        mock_config = {
            constants.DISTRIBUTOR_CONFIG_KEY_PUBLISH_DIRECTORY: self.publish_dir
        }
        self.repo.content_unit_counts = {}
        publisher = steps.WebPublisher(self.repo, mock_conduit, mock_config)
        self.assertEquals(publisher.children, [mock_empty.return_value,
                                               mock_atomic.return_value])

    @patch('pulp_ostree.plugins.distributors.steps.AtomicDirectoryPublishStep')
    @patch('pulp_ostree.plugins.distributors.steps.PublishContentStep')
    @patch('pulp_ostree.plugins.distributors.steps.PublishRefsStep')
    def test_init_populated(self, mock_refs, mock_content, mock_atomic):
        mock_conduit = Mock()
        mock_config = {
            constants.DISTRIBUTOR_CONFIG_KEY_PUBLISH_DIRECTORY: self.publish_dir
        }
        self.repo.content_unit_counts = {'ostree': 1}
        publisher = steps.WebPublisher(self.repo, mock_conduit, mock_config)
        self.assertEquals(publisher.children, [mock_content.return_value,
                                               mock_refs.return_value,
                                               mock_atomic.return_value])


class TestPublishContentStep(unittest.TestCase):

    def setUp(self):
        self.working_directory = tempfile.mkdtemp()
        self.source_dir = os.path.join(self.working_directory, 'src')
        self.target_dir = os.path.join(self.working_directory, 'target')

        os.makedirs(self.source_dir)
        os.makedirs(self.target_dir)
        self.repo = Repository(id='foo', working_dir=self.target_dir)
        config = PluginCallConfiguration(None, None)
        conduit = RepoPublishConduit(self.repo.id, 'foo_repo')
        conduit.get_repo_scratchpad = Mock(return_value={u'tags': {}})
        self.parent = steps.PluginStep('test-step', self.repo, conduit, config)

    def tearDown(self):
        shutil.rmtree(self.working_directory)

    @patch('pulp_ostree.plugins.distributors.steps.PublishContentStep._get_ostree_unit')
    def test_process_main(self, mock_get_unit):
        mock_get_unit.return_value.storage_path = self.source_dir
        content_dirs = ['objects', 'remote-cache', 'tmp', 'uncompressed-objects-cache']
        for dir_name in content_dirs:
            touch(os.path.join(self.source_dir, dir_name, 'foo'))

        touch(os.path.join(self.source_dir, 'refs', 'foo'))
        step = steps.PublishContentStep()
        self.parent.add_child(step)
        step.process_main()

        for dir_name in content_dirs:
            target_dir = os.path.join(self.target_dir, dir_name)
            src_dir = os.path.join(self.source_dir, dir_name)
            self.assertEquals(os.path.realpath(target_dir), src_dir)

        self.assertFalse(os.path.exists(os.path.join(self.target_dir, 'refs')))

    @patch('pulp_ostree.plugins.distributors.steps.PublishContentStep.get_conduit')
    def test_get_ostree_unit(self, mock_get_conduit):
        get_units = mock_get_conduit.return_value.get_units
        get_units.return_value = ['foo', 'bar']
        step = steps.PublishContentStep()
        unit = step._get_ostree_unit()

        self.assertEquals('foo', unit)
        criteria = get_units.mock_calls[0][1][0]
        self.assertEquals(criteria.type_ids, [constants.OSTREE_TYPE_ID])
        sort_order = pulp_constants.SORT_DIRECTION[pulp_constants.SORT_DESCENDING]
        self.assertEquals(criteria.unit_sort, [('created', sort_order)])

    @patch('pulp_ostree.plugins.distributors.steps.PublishContentStep.get_conduit')
    def test_get_ostree_no_unit(self, mock_get_conduit):
        get_units = mock_get_conduit.return_value.get_units
        get_units.return_value = []
        step = steps.PublishContentStep()
        self.assertRaises(Exception, step._get_ostree_unit)


class TestCreateEmptyOSTreeStep(unittest.TestCase):
    def setUp(self):
        self.working_directory = tempfile.mkdtemp()
        self.publish_dir = os.path.join(self.working_directory, 'publish')
        self.working_temp = os.path.join(self.working_directory, 'work')
        os.makedirs(self.working_temp)
        self.repo = Repository(id='foo', working_dir=self.working_temp)
        config = PluginCallConfiguration(None, None)
        conduit = RepoPublishConduit(self.repo.id, 'foo_repo')
        conduit.get_repo_scratchpad = Mock(return_value={u'tags': {}})
        self.parent = steps.PluginStep('test-step', self.repo, conduit, config)

    def tearDown(self):
        shutil.rmtree(self.working_directory)

    @patch('pulp_ostree.plugins.distributors.steps.lib.Repository')
    def test_process_main(self, mock_ostree_repo):
        step = steps.CreateEmptyOSTreeStep()
        self.parent.add_child(step)
        step.process_main()
        target_repo = os.path.join(self.working_temp, self.repo.id)
        mock_ostree_repo.assert_called_once_with(target_repo)
        mock_ostree_repo.return_value.create.assert_called_once_with()


class TestPublishRefsStep(unittest.TestCase):

    def setUp(self):
        self.working_directory = tempfile.mkdtemp()
        self.content_dir = os.path.join(self.working_directory, 'content')
        self.working_dir = os.path.join(self.working_directory, 'work')
        os.makedirs(self.working_dir)
        self.repo = Repository(id='foo', working_dir=self.working_dir)
        config = PluginCallConfiguration(None, None)
        conduit = RepoPublishConduit(self.repo.id, 'foo_repo')
        conduit.get_repo_scratchpad = Mock(return_value={u'tags': {}})
        self.parent = steps.PluginStep('test-step', self.repo, conduit, config)

    def tearDown(self):
        shutil.rmtree(self.working_directory)

    def test_process_main_refs(self):
        touch(os.path.join(self.content_dir, 'config'))
        metadata = {
            'refs': {
                'heads': [{
                    'path': 'foo/bar/baz',
                    'commit_id': 'foo_hash'
                }]
            }
        }

        content_step = Mock(unit=Unit(constants.OSTREE_TYPE_ID,
                                      {'foo': 'bar'},
                                      metadata,
                                      self.content_dir))
        step = steps.PublishRefsStep(content_step)
        self.parent.add_child(step)
        step.process_main()
        head_file = os.path.join(self.working_dir, 'refs', 'foo/bar/baz')
        self.assertTrue(os.path.exists(head_file))
        with open(head_file) as test_fp:
            content = test_fp.read()
            self.assertEquals('foo_hash', content)

    def test_process_main_config_file(self):
        # build the source config file
        parser = ConfigParser.SafeConfigParser()
        parser.add_section('core')
        parser.set('core', 'foo', 'bar')
        parser.add_section('remote apple')
        parser.set('remote apple', 'foo', 'bar')
        os.makedirs(self.content_dir)
        with open(os.path.join(self.content_dir, 'config'), 'w') as config_file:
            parser.write(config_file)

        metadata = {
            'refs': {
                'heads': []
            }
        }

        content_step = Mock(unit=Unit(constants.OSTREE_TYPE_ID,
                                      {'foo': 'bar'},
                                      metadata,
                                      self.content_dir))
        step = steps.PublishRefsStep(content_step)
        self.parent.add_child(step)
        step.process_main()

        parser = ConfigParser.SafeConfigParser()
        parser.read(os.path.join(self.working_dir, 'config'))
        self.assertEquals(len(parser.sections()), 1)
        self.assertTrue(parser.get('core', 'foo'), 'bar')
