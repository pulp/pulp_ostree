import os

from hashlib import sha256
from unittest import TestCase

from mock import patch, Mock

from pulp_ostree.common.model import Head, Commit, Unit, generate_remote_id


class TestUtils(TestCase):

    def test_generate_remote_id(self):
        url = 'url-test'
        remote_id = generate_remote_id(url)
        h = sha256()
        h.update(url)
        self.assertEqual(remote_id, h.hexdigest())


class TestCommit(TestCase):

    def test_init(self):
        digest = '123'
        metadata = {
            'A': 1,
            'B.a.d': 2,
            'hello': 3
        }
        stored = {
            'A': 1,
            'B-a-d': 2,
            'hello': 3
        }
        commit = Commit(digest, metadata)
        self.assertEqual(commit.digest, digest)
        self.assertEqual(commit.metadata, stored)


class TestHeads(TestCase):

    def test_init(self):
        remote_id = '1234'
        branch = '/branch/core'
        commit = Mock()
        head = Head(remote_id, branch, commit)
        self.assertEqual(head.remote_id, remote_id)
        self.assertEqual(head.branch, branch)
        self.assertEqual(head.commit, commit)

    def test_digest(self):
        remote_id = '1234'
        branch = '/branch/core'
        commit = Mock(digest='1234')
        head = Head(remote_id, branch, commit)
        h = sha256()
        h.update(head.remote_id)
        h.update(head.branch)
        h.update(head.commit.digest)
        self.assertEqual(h.hexdigest(), head.digest)

    @patch('pulp_ostree.common.model.constants.LINKS_DIR', 'links')
    @patch('pulp_ostree.common.model.constants.SHARED_STORAGE', '/shared')
    @patch('pulp_ostree.common.model.Head.digest', 'digest')
    def test_storage_path(self):
        remote_id = '1234'
        branch = '/branch/core'
        commit = Mock(digest='1234')
        head = Head(remote_id, branch, commit)
        self.assertEqual(head.storage_path, os.path.join('/shared/1234/links/digest'))


class TestUnit(TestCase):

    def test_init(self):
        created = 1234
        remote_id = '1234'
        branch = '/branch/core'
        commit = Mock()
        unit = Unit(remote_id, branch, commit, created)
        self.assertEqual(unit.remote_id, remote_id)
        self.assertEqual(unit.branch, branch)
        self.assertEqual(unit.commit, commit)
        self.assertEqual(unit.created, created)

    @patch('pulp_ostree.common.model.datetime')
    def test_init_now(self, dt):
        now = 1234
        dt.utcnow.return_value = now
        remote_id = '1234'
        branch = '/branch/core'
        commit = Mock()
        unit = Unit(remote_id, branch, commit)
        dt.utcnow.assert_called_once_with()
        self.assertEqual(unit.remote_id, remote_id)
        self.assertEqual(unit.branch, branch)
        self.assertEqual(unit.commit, commit)
        self.assertEqual(unit.created, now)

    def test_unit_key(self):
        remote_id = '1234'
        branch = '/branch/core'
        commit = Mock(digest='1234')
        unit = Unit(remote_id, branch, commit)
        self.assertEqual(
            unit.key,
            {
                Head.BRANCH: unit.branch,
                Head.COMMIT: unit.commit.digest,
                Unit.REMOTE_ID: unit.remote_id
            })

    def test_unit_md(self):
        created = 1234
        remote_id = '1234'
        branch = '/branch/core'
        commit = Mock(metadata={'version': '1.0'})
        unit = Unit(remote_id, branch, commit, created=created)
        md = {Unit.CREATED: created}
        md.update(unit.commit.metadata)
        self.assertEqual(unit.metadata, md)
