import os

from pulp.common.compat import unittest

from mock import patch, Mock, PropertyMock, ANY

from pulp.common.plugins import importer_constants
from pulp.server.exceptions import PulpCodedException

from mongoengine import NotUniqueError

from pulp_ostree.plugins.lib import LibError
from pulp_ostree.plugins.importers.steps import Main, Create, Summary, Pull, Add, Clean, Remote
from pulp_ostree.common import constants, errors


# The module being tested
MODULE = 'pulp_ostree.plugins.importers.steps'


class TestMainStep(unittest.TestCase):

    @patch('pulp_ostree.plugins.db.model.generate_remote_id')
    def test_init(self, fake_generate):
        repo = Mock(id='id-123')
        conduit = Mock()
        working_dir = 'dir-123'
        url = 'url-123'
        branches = ['branch-1', 'branch-2']
        depth = 3
        digest = 'digest-123'
        fake_generate.return_value = digest
        config = {
            importer_constants.KEY_FEED: url,
            constants.IMPORTER_CONFIG_KEY_BRANCHES: branches,
            constants.IMPORTER_CONFIG_KEY_DEPTH: depth,
        }

        # test
        step = Main(repo=repo, conduit=conduit, config=config, working_dir=working_dir)

        # validation
        self.assertEqual(step.step_id, constants.IMPORT_STEP_MAIN)
        self.assertEqual(step.repo, repo)
        self.assertEqual(step.conduit, conduit)
        self.assertEqual(step.config, config)
        self.assertEqual(step.working_dir, working_dir)
        self.assertEqual(step.plugin_type, constants.WEB_IMPORTER_TYPE_ID)
        self.assertEqual(step.feed_url, url)
        self.assertEqual(step.remote_id, digest)
        self.assertEqual(step.branches, branches)
        self.assertEqual(step.depth, depth)
        self.assertEqual(step.repo_id, repo.id)
        self.assertEqual(len(step.children), 5)
        self.assertTrue(isinstance(step.children[0], Create))
        self.assertTrue(isinstance(step.children[1], Summary))
        self.assertTrue(isinstance(step.children[2], Pull))
        self.assertTrue(isinstance(step.children[3], Add))
        self.assertTrue(isinstance(step.children[4], Clean))

    def test_init_no_feed(self):
        repo = Mock(id='id-123')
        url = None

        config = {
            importer_constants.KEY_FEED: url,
            constants.IMPORTER_CONFIG_KEY_BRANCHES: []
        }

        # test and validation
        try:
            Main(repo=repo, config=config)
            self.assertTrue(False, msg='Main.__init__() exception expected')
        except PulpCodedException, pe:
            self.assertEqual(pe.error_code, errors.OST0004)

    @patch(MODULE + '.SharedStorage')
    def test_storage_dir(self, storage):
        url = 'url-123'
        repo = Mock(id='id-123')
        config = {
            importer_constants.KEY_FEED: url,
        }
        st = Mock()
        st.__enter__ = Mock(return_value=st)
        st.__exit__ = Mock()
        storage.return_value = st

        # test
        step = Main(repo=repo, config=config)
        path = step.storage_dir
        storage.assert_called_once_with(constants.STORAGE_PROVIDER, step.remote_id)
        st.__enter__.assert_called_once_with()
        st.__exit__.assert_called_once_with(None, None, None)
        self.assertEqual(path, st.content_dir)


class TestCreate(unittest.TestCase):

    def test_init(self):
        step = Create()
        self.assertEqual(step.step_id, constants.IMPORT_STEP_CREATE_REPOSITORY)
        self.assertTrue(step.description is not None)

    @patch(MODULE + '.lib')
    @patch(MODULE + '.Remote')
    def test_process_main(self, fake_remote, fake_lib):
        url = 'url-123'
        remote_id = 'remote-123'
        repo_id = 'repo-123'
        parent = Mock(
            feed_url=url,
            remote_id=remote_id,
            repo_id=repo_id,
            storage_dir='root/path-123')

        fake_lib.LibError = LibError
        fake_lib.Repository.return_value.open.side_effect = LibError

        # test
        step = Create()
        step.parent = parent
        step.process_main()

        # validation
        fake_remote.assert_called_once_with(step, fake_lib.Repository.return_value)
        fake_lib.Repository.assert_called_once_with(parent.storage_dir)
        fake_lib.Repository.return_value.open.assert_called_once_with()
        fake_lib.Repository.return_value.create.assert_called_once_with()
        fake_remote.return_value.add.assert_called_once_with()

    @patch(MODULE + '.lib')
    @patch(MODULE + '.Remote')
    def test_process_main_repository_exists(self, fake_remote, fake_lib):
        url = 'url-123'
        remote_id = 'remote-123'
        repo_id = 'repo-xyz'
        path = 'root/path-123'
        parent = Mock(
            feed_url=url,
            remote_id=remote_id,
            repo_id=repo_id,
            storage_dir='root/path-123')

        # test
        step = Create()
        step.parent = parent
        step.process_main()

        # validation
        fake_remote.assert_called_once_with(step, fake_lib.Repository.return_value)
        fake_lib.Repository.assert_called_once_with(path)
        fake_lib.Repository.return_value.open.assert_called_once_with()
        fake_remote.return_value.add.assert_called_once_with()

    @patch(MODULE + '.lib')
    def test_process_main_repository_exception(self, fake_lib):
        fake_lib.LibError = LibError
        fake_lib.Repository.side_effect = LibError
        try:
            step = Create()
            step.parent = Mock(feed_url='', remote_id='')
            step.process_main()
            self.assertTrue(False, msg='Create exception expected')
        except PulpCodedException, pe:
            self.assertEqual(pe.error_code, errors.OST0001)


class TestPull(unittest.TestCase):

    def test_init(self):
        step = Pull()
        self.assertEqual(step.step_id, constants.IMPORT_STEP_PULL)
        self.assertTrue(step.description is not None)

    def test_process_main(self):
        repo_id = 'repo-xyz'
        path = 'root/path-123'
        branches = ['branch-1', 'branch-2']
        depth = 3

        # test
        step = Pull()
        step.parent = Mock(storage_dir=path, repo_id=repo_id, branches=branches, depth=depth)
        step._pull = Mock()
        step.process_main()

        # validation
        step._pull.assert_called_once_with(path, repo_id, branches, depth)

    @patch(MODULE + '.lib')
    def test_pull(self, fake_lib):
        remote_id = 'remote-123'
        path = 'root/path-123'
        branches = ['branch-1']
        depth = 3
        repo = Mock()
        fake_lib.Repository.return_value = repo
        report = Mock(fetched=1, requested=2, percent=50)

        def fake_pull(remote_id, branch, listener, depth):
            listener(report)

        repo.pull.side_effect = fake_pull

        # test
        step = Pull()
        step.report_progress = Mock()
        step._pull(path, remote_id, branches, depth)

        # validation
        fake_lib.Repository.assert_called_once_with(path)
        repo.pull.assert_called_once_with(remote_id, branches, ANY, depth)
        step.report_progress.assert_called_with(force=True)
        self.assertEqual(step.progress_details, 'fetching 1/2 50%')

    @patch(MODULE + '.lib')
    def test_pull_raising_exception(self, fake_lib):
        fake_lib.LibError = LibError
        fake_lib.Repository.return_value.pull.side_effect = LibError
        try:
            step = Pull()
            step._pull('', '', '', 0)
            self.assertTrue(False, msg='Pull exception expected')
        except PulpCodedException, pe:
            self.assertEqual(pe.error_code, errors.OST0002)


class TestAdd(unittest.TestCase):

    def test_init(self):
        step = Add()
        self.assertEqual(step.step_id, constants.IMPORT_STEP_ADD_UNITS)
        self.assertTrue(step.description is not None)

    @patch(MODULE + '.lib')
    @patch(MODULE + '.model')
    @patch(MODULE + '.associate_single_unit')
    def test_process_main(self, fake_associate, fake_model, fake_lib):
        repo_id = 'r-1234'
        remote_id = 'remote-1'
        refs = [
            Mock(path='branch:1', commit='commit:1', metadata='md:1'),
            Mock(path='branch:2', commit='commit:2', metadata='md:2'),
            Mock(path='branch:3', commit='commit:3', metadata='md:3'),
            Mock(path='branch:4', commit='commit:4', metadata='md:4'),
            Mock(path='branch:5', commit='commit:5', metadata='md:5'),
        ]
        units = [Mock(ref=r, unit_key={}) for r in refs]
        units[0].save.side_effect = NotUniqueError  # duplicate

        fake_model.Branch.side_effect = units
        fake_model.Branch.objects.get.return_value = units[0]

        branches = [r.path.split(':')[-1] for r in refs[:-1]]

        repository = Mock()
        repository.list_refs.return_value = refs
        fake_lib.Repository.return_value = repository

        parent = Mock(remote_id=remote_id, storage_dir='/tmp/xyz', branches=branches)
        parent.get_repo.return_value = Mock(id=repo_id)

        fake_conduit = Mock()

        # test
        step = Add()
        step.parent = parent
        step.get_conduit = Mock(return_value=fake_conduit)
        step.process_main()

        # validation
        fake_lib.Repository.assert_called_once_with(step.parent.storage_dir)
        self.assertEqual(
            fake_model.Branch.call_args_list,
            [
                ((), dict(
                    remote_id=remote_id,
                    branch=r.path.split(':')[-1],
                    commit=r.commit,
                    metadata=r.metadata))
                for r in refs[:-1]
            ])
        self.assertEqual(
            fake_associate.call_args_list,
            [
                ((parent.get_repo.return_value.repo_obj, u), {}) for u in units[:-1]
            ])


class TestSummary(unittest.TestCase):

    @patch(MODULE + '.lib')
    def test_process_main(self, fake_lib):
        refs = [
            Mock(),
            Mock(),
            Mock(),
        ]
        ref_dicts = [
            {'commit': 'abc', 'name': 'foo', 'metadata': {'a.b': 'x'}},
            {'commit': 'def', 'name': 'bar', 'metadata': {'a.b': 'y'}},
            {'commit': 'hij', 'name': 'baz', 'metadata': {'a.b': 'z'}},
        ]
        for ref, d in zip(refs, ref_dicts):
            ref.dict.return_value = d
        remote = Mock()
        remote.list_refs.return_value = refs
        lib_repository = Mock()
        repository = Mock(id='1234')
        fake_lib.Remote.return_value = remote
        fake_lib.Repository.return_value = lib_repository
        parent = Mock(storage_dir='/tmp/xx', repo_id=repository.id)
        parent.get_repo.return_value = repository

        # test
        step = Summary()
        step.parent = parent
        step.process_main()

        # validation
        fake_lib.Repository.assert_called_once_with(step.parent.storage_dir)
        fake_lib.Remote.assert_called_once_with(step.parent.repo_id, lib_repository)
        repository.repo_obj.scratchpad.update.assert_called_once_with(
            {
                constants.REMOTE: {
                    constants.SUMMARY: [
                        {'commit': 'abc', 'name': 'foo', 'metadata': {'a-b': 'x'}},
                        {'commit': 'def', 'name': 'bar', 'metadata': {'a-b': 'y'}},
                        {'commit': 'hij', 'name': 'baz', 'metadata': {'a-b': 'z'}},
                    ]
                }
            })
        repository.repo_obj.save.assert_called_once_with()

    @patch(MODULE + '.lib')
    def test_process_main_fetch_failed(self, fake_lib):
        remote = Mock()
        remote.list_refs.side_effect = LibError
        lib_repository = Mock()
        repository = Mock(id='1234')
        fake_lib.Remote.return_value = remote
        fake_lib.Repository.return_value = lib_repository
        fake_lib.LibError = LibError
        parent = Mock(storage_dir='/tmp/xx', repo_id=repository.id)
        parent.get_repo.return_value = repository

        # test and validation
        step = Summary()
        step.parent = parent
        try:
            step.process_main()
            self.assertTrue(False, msg='Fetch exception expected')
        except PulpCodedException, pe:
            self.assertEqual(pe.error_code, errors.OST0005)

    def test_clean_metadata(self):
        commit = 'abc'
        name = 'foo'
        metadata = {
            'a.b': '123',
            'a.b.c': '456',
            'created': '2016-02-23T22:49:05Z'
        }
        ref = {
            'commit': commit,
            'name': name,
            'metadata': metadata
        }

        cleaned = dict((k.replace('.', '-'), v) for k, v in metadata.items())

        # test
        Summary.clean_metadata(ref)

        # validation
        self.assertDictEqual(
            ref,
            {
                'commit': commit,
                'name': name,
                'metadata': cleaned
            })


class TestClean(unittest.TestCase):

    def test_init(self):
        step = Clean()
        self.assertEqual(step.step_id, constants.IMPORT_STEP_CLEAN)
        self.assertTrue(step.description is not None)

    @patch(MODULE + '.lib')
    def test_process_main(self, fake_lib):
        path = 'root/path-123'
        repo_id = 'repo-123'

        # test
        step = Clean()
        step.parent = Mock(storage_dir=path, repo_id=repo_id)
        step.process_main()

        # validation
        fake_lib.Repository.assert_called_once_with(path)
        fake_lib.Remote.assert_called_once_with(repo_id, fake_lib.Repository.return_value)
        fake_lib.Remote.return_value.delete.assert_called_once_with()

    @patch(MODULE + '.lib')
    def test_process_main_exception(self, fake_lib):
        path = 'root/path-123'
        importer_id = 'importer-xyz'

        fake_lib.LibError = LibError
        fake_lib.Remote.return_value.delete.side_effect = LibError

        # test
        try:
            step = Clean()
            step.parent = Mock(storage_dir=path, importer_id=importer_id)
            step.process_main()
            self.assertTrue(False, msg='Delete remote exception expected')
        except PulpCodedException, pe:
            self.assertEqual(pe.error_code, errors.OST0003)


class TestRemote(unittest.TestCase):

    def test_init(self):
        step = Mock()
        repository = Mock()
        remote = Remote(step, repository)
        self.assertEqual(remote.step, step)
        self.assertEqual(remote.repository, repository)

    def test_url(self):
        step = Mock()
        step.parent = Mock(feed_url='http://')
        remote = Remote(step, None)
        self.assertEqual(remote.url, step.parent.feed_url)

    def test_remote_id(self):
        step = Mock()
        step.parent = Mock(repo_id='123')
        remote = Remote(step, None)
        self.assertEqual(remote.remote_id, step.parent.repo_id)

    def test_working_dir(self):
        step = Mock()
        remote = Remote(step, None)
        self.assertEqual(remote.working_dir, step.get_working_dir.return_value)

    def test_config(self):
        step = Mock()
        remote = Remote(step, None)
        self.assertEqual(remote.config, step.get_config.return_value)

    @patch('os.chmod')
    @patch('__builtin__.open')
    def test_ssl_key_path(self, fake_open, fake_chmod):
        key = 'test-key'
        config = {
            importer_constants.KEY_SSL_CLIENT_KEY: key
        }
        working_dir = '/tmp/test'
        step = Mock()
        step.get_config.return_value = config
        step.get_working_dir.return_value = working_dir
        fp = Mock(__enter__=Mock(), __exit__=Mock())
        fp.__enter__.return_value = fp
        fake_open.return_value = fp

        # test
        remote = Remote(step, None)
        path = remote.ssl_key_path

        # validation
        expected_path = os.path.join(working_dir, 'key.pem')
        fake_open.assert_called_once_with(expected_path, 'w+')
        fp.write.assert_called_once_with(key)
        fp.__enter__.assert_called_once_with()
        fp.__exit__.assert_called_once_with(None, None, None)
        fake_chmod.assert_called_once_with(expected_path, 0600)
        self.assertEqual(path, expected_path)

    @patch('__builtin__.open')
    def test_ssl_cert_path(self, fake_open):
        cert = 'test-key'
        config = {
            importer_constants.KEY_SSL_CLIENT_CERT: cert
        }
        working_dir = '/tmp/test'
        step = Mock()
        step.get_config.return_value = config
        step.get_working_dir.return_value = working_dir
        fp = Mock(__enter__=Mock(), __exit__=Mock())
        fp.__enter__.return_value = fp
        fake_open.return_value = fp

        # test
        remote = Remote(step, None)
        path = remote.ssl_cert_path

        # validation
        expected_path = os.path.join(working_dir, 'cert.pem')
        fake_open.assert_called_once_with(expected_path, 'w+')
        fp.write.assert_called_once_with(cert)
        fp.__enter__.assert_called_once_with()
        fp.__exit__.assert_called_once_with(None, None, None)
        self.assertEqual(path, expected_path)

    @patch('__builtin__.open')
    def test_ssl_ca_path(self, fake_open):
        cert = 'test-key'
        config = {
            importer_constants.KEY_SSL_CA_CERT: cert
        }
        working_dir = '/tmp/test'
        step = Mock()
        step.get_config.return_value = config
        step.get_working_dir.return_value = working_dir
        fp = Mock(__enter__=Mock(), __exit__=Mock())
        fp.__enter__.return_value = fp
        fake_open.return_value = fp

        # test
        remote = Remote(step, None)
        path = remote.ssl_ca_path

        # validation
        expected_path = os.path.join(working_dir, 'ca.pem')
        fake_open.assert_called_once_with(expected_path, 'w+')
        fp.write.assert_called_once_with(cert)
        fp.__enter__.assert_called_once_with()
        fp.__exit__.assert_called_once_with(None, None, None)
        self.assertEqual(path, expected_path)

    def test_ssl_validation(self):
        config = {
            importer_constants.KEY_SSL_VALIDATION: True
        }
        step = Mock()
        step.get_config.return_value = config

        # test
        remote = Remote(step, None)
        validation = remote.ssl_validation

        # validation
        self.assertTrue(validation)
        self.assertTrue(isinstance(validation, bool))

    def test_ssl_validation_not_specified(self):
        config = {}
        step = Mock()
        step.get_config.return_value = config

        # test
        remote = Remote(step, None)
        validation = remote.ssl_validation

        # validation
        self.assertFalse(validation)
        self.assertTrue(isinstance(validation, bool))

    @patch(MODULE + '.GPG')
    def test_gpg_key(self, fake_gpg):
        keys = [1, 2, 3]
        key_list = [dict(keyid=k) for k in keys]
        working_dir = '/tmp/test'
        config = {
            constants.IMPORTER_CONFIG_KEY_GPG_KEYS: keys
        }
        step = Mock()
        step.get_config.return_value = config
        step.get_working_dir.return_value = working_dir

        fake_gpg.return_value.list_keys.return_value = key_list

        # test
        remote = Remote(step, None)
        path, key_ids = remote.gpg_keys

        # validation
        fake_gpg.assert_called_once_with(gnupghome=working_dir)
        self.assertEqual(
            fake_gpg.return_value.import_keys.call_args_list,
            [((k,), {}) for k in keys])
        self.assertEqual(path, os.path.join(working_dir, 'pubring.gpg'))
        self.assertEqual(key_ids, [k['keyid'] for k in key_list])

    def test_proxy_url(self):
        host = 'http://dog.com'
        port = '3128'
        user = 'jake'
        password = 'bark'
        config = {
            importer_constants.KEY_PROXY_HOST: host,
            importer_constants.KEY_PROXY_PORT: port,
            importer_constants.KEY_PROXY_USER: user,
            importer_constants.KEY_PROXY_PASS: password,
        }
        step = Mock()
        step.get_config.return_value = config

        proxy_url = 'http://jake:bark@dog.com:3128'

        # test
        remote = Remote(step, None)

        # validation
        self.assertEqual(remote.proxy_url, proxy_url)

    def test_proxy_url_without_scheme(self):
        host = 'dog.com'
        port = '3128'
        user = 'jake'
        password = 'bark'
        config = {
            importer_constants.KEY_PROXY_HOST: host,
            importer_constants.KEY_PROXY_PORT: port,
            importer_constants.KEY_PROXY_USER: user,
            importer_constants.KEY_PROXY_PASS: password,
        }
        step = Mock()
        step.get_config.return_value = config

        proxy_url = 'http://jake:bark@dog.com:3128'

        # test
        remote = Remote(step, None)

        # validation
        self.assertEqual(remote.proxy_url, proxy_url)

    def test_proxy_url_without_port(self):
        host = 'http://dog.com'
        port = None
        user = 'jake'
        password = 'bark'
        config = {
            importer_constants.KEY_PROXY_HOST: host,
            importer_constants.KEY_PROXY_PORT: port,
            importer_constants.KEY_PROXY_USER: user,
            importer_constants.KEY_PROXY_PASS: password,
        }
        step = Mock()
        step.get_config.return_value = config

        proxy_url = 'http://jake:bark@dog.com'

        # test
        remote = Remote(step, None)

        # validation
        self.assertEqual(remote.proxy_url, proxy_url)

    def test_proxy_without_auth(self):
        host = 'http://dog.com'
        port = '3128'
        config = {
            importer_constants.KEY_PROXY_HOST: host,
            importer_constants.KEY_PROXY_PORT: port,
        }
        step = Mock()
        step.get_config.return_value = config

        proxy_url = 'http://dog.com:3128'

        # test
        remote = Remote(step, None)

        # validation
        self.assertEqual(remote.proxy_url, proxy_url)

    def test_proxy_without_host(self):
        config = {
        }
        step = Mock()
        step.get_config.return_value = config

        # test
        remote = Remote(step, None)

        # validation
        self.assertEqual(remote.proxy_url, None)

    @patch(MODULE + '.lib')
    @patch(MODULE + '.Remote.url', PropertyMock())
    @patch(MODULE + '.Remote.remote_id', PropertyMock())
    @patch(MODULE + '.Remote.ssl_key_path', PropertyMock())
    @patch(MODULE + '.Remote.ssl_cert_path', PropertyMock())
    @patch(MODULE + '.Remote.ssl_ca_path', PropertyMock())
    @patch(MODULE + '.Remote.ssl_validation', PropertyMock())
    @patch(MODULE + '.Remote.proxy_url', PropertyMock())
    @patch(MODULE + '.Remote.gpg_keys', new_callable=PropertyMock)
    def test_add(self, fake_gpg, fake_lib):
        step = Mock()
        repository = Mock()
        path = Mock()
        key_ids = [1, 2, 3]
        fake_gpg.return_value = (path, key_ids)

        # test
        remote = Remote(step, repository)
        remote.add()

        # validation
        fake_lib.Remote.assert_called_once_with(remote.remote_id, repository)
        fake_lib.Remote.return_value.update.assert_called_once_with()
        fake_lib.Remote.return_value.import_key.assert_called_once_with(path, key_ids)
        self.assertEqual(fake_lib.Remote.return_value.url, remote.url)
        self.assertEqual(fake_lib.Remote.return_value.ssl_key_path, remote.ssl_key_path)
        self.assertEqual(fake_lib.Remote.return_value.ssl_cert_path, remote.ssl_cert_path)
        self.assertEqual(fake_lib.Remote.return_value.ssl_ca_path, remote.ssl_ca_path)
        self.assertEqual(fake_lib.Remote.return_value.ssl_validation, remote.ssl_validation)
        self.assertEqual(fake_lib.Remote.return_value.proxy_url, remote.proxy_url)
        self.assertTrue(fake_lib.Remote.return_value.gpg_validation, remote.ssl_validation)
