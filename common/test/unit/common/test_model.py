import os

from hashlib import sha256
from unittest import TestCase

from mock import patch, Mock

from pulp_ostree.common.model import Refs, Head, Repository


HEADS = [
    {Head.PATH: 'path-1', Head.COMMIT_ID: 'commit-A'},
    {Head.PATH: 'path-2', Head.COMMIT_ID: 'commit-B'}
]

REFS = {
    Refs.HEADS: HEADS
}

REPOSITORY = {
    Repository.REMOTE_ID: 'remote-1',
    Repository.TIMESTAMP: 'today',
    Repository.REFS: REFS
}


class TestHeads(TestCase):

    def test_from_dict(self):
        d = HEADS[0]
        head = Head.from_dict(d)
        self.assertEqual(head.path, d[Head.PATH])
        self.assertEqual(head.commit_id, d[Head.COMMIT_ID])

    def test_init(self):
        path = 'path-1'
        commit_id = 'commit-1'
        head = Head(path, commit_id)
        self.assertEqual(head.path, path)
        self.assertEqual(head.commit_id, commit_id)

    def test_to_dict(self):
        path = HEADS[0][Head.PATH]
        commit_id = HEADS[0][Head.COMMIT_ID]
        head = Head(path, commit_id)
        self.assertEqual(head.to_dict(), HEADS[0])

    def test_digest(self):
        path = 'path-1'
        commit_id = 'commit-1'
        head = Head(path, commit_id)
        h = sha256()
        h.update(head.path)
        h.update(head.commit_id)
        self.assertEqual(h.hexdigest(), head.digest)


class TestRefs(TestCase):

    @patch('pulp_ostree.common.model.Head.from_dict')
    def test_from_dict(self, fake_from_dict):
        heads = [Mock(), Mock()]
        fake_from_dict.side_effect = heads
        refs = Refs.from_dict(REFS)
        self.assertEqual(len(refs.heads), len(HEADS))
        self.assertEqual(refs.heads[0], heads[0])
        self.assertEqual(refs.heads[1], heads[1])

    def test_init(self):
        refs = Refs()
        self.assertEqual(refs.heads, [])
        heads = [1, 2]
        refs = Refs(heads)
        self.assertEqual(refs.heads, heads)

    def test_add_head(self):
        refs = Refs()
        heads = [
            Mock(),
            Mock(),
        ]
        for head in heads:
            refs.add_head(head)
        self.assertEqual(refs.heads, heads)

    def test_digest(self):
        heads = [
            Mock(),
            Mock()
        ]
        heads[0].digest = 'A'
        heads[1].digest = 'B'
        refs = Refs(heads)
        h = sha256()
        h.update('A')
        h.update('B')
        self.assertEqual(h.hexdigest(), refs.digest)

    def test_digest_ordering(self):
        heads = [
            Head('A', 'XX'),
            Head('B', 'XX')
        ]
        digest_1 = Refs(heads).digest
        digest_2 = Refs(reversed(heads)).digest
        self.assertEqual(digest_1, digest_2)

    def test_to_dict(self):
        heads = [
            Head.from_dict(HEADS[0]),
            Head.from_dict(HEADS[1])
        ]
        refs = Refs(heads)
        self.assertEqual(refs.to_dict(), REFS)


class TestRepository(TestCase):

    @patch('pulp_ostree.common.model.Refs.from_dict')
    def test_from_dict(self, fake_from_dict):
        fake_from_dict.return_value = Mock()
        repository = Repository.from_dict(REPOSITORY)
        self.assertEqual(repository.remote_id, REPOSITORY[Repository.REMOTE_ID])
        self.assertEqual(repository.timestamp, REPOSITORY[Repository.TIMESTAMP])
        self.assertEqual(repository.refs, fake_from_dict())

    def test_init(self):
        remote_id = 'remote-1'
        refs = Refs()
        timestamp = 'today'
        repository = Repository(remote_id, refs, timestamp)
        self.assertEqual(repository.remote_id, remote_id)
        self.assertEqual(repository.refs, refs)
        self.assertEqual(repository.timestamp, timestamp)

    def test_unit_key(self):
        remote_id = 'remote-1'
        refs = Refs()
        repository = Repository(remote_id, refs, None)
        expected = {
            Repository.REMOTE_ID: remote_id,
            Repository.DIGEST: refs.digest
        }
        self.assertEqual(repository.unit_key, expected)

    def test_metadata(self):
        timestamp = 'today'
        remote_id = 'remote-1'
        refs = Refs()
        repository = Repository(remote_id, refs, timestamp)
        expected = {
            Repository.TIMESTAMP: timestamp,
            Repository.REFS: refs.to_dict()
        }
        self.assertEqual(expected, repository.metadata)

    def test_relative_path(self):
        remote_id = 'remote-1'
        refs = Refs()
        repository = Repository(remote_id, refs, None)
        self.assertEqual(repository.relative_path, remote_id)
