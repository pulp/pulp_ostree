import os

from hashlib import sha256

from pulp_ostree.common import constants


class Head(object):
    """
    Branch (tree) head.
    """

    PATH = 'path'
    COMMIT_ID = 'commit_id'

    @staticmethod
    def from_dict(d):
        """
        Construct using a dictionary representation.
        :param d: A dictionary representation.
        :type d: dict
        """
        return Head(d[Head.PATH], d[Head.COMMIT_ID])

    def __init__(self, path, commit_id):
        """
        :param path: The branch path.
        :type path: str
        :param commit_id: The commit ID (digest).
        :type commit_id: str
        """
        self.path = path
        self.commit_id = commit_id

    @property
    def digest(self):
        """
        Get the content-based digest.
        :return: The content-based digest.
        :rtype: str
        """
        h = sha256()
        h.update(self.path)
        h.update(self.commit_id)
        return h.hexdigest()

    def to_dict(self):
        """
        Get a dictionary representation.
        :return: A dictionary representation.
        :rtype: dict
        """
        return {
            Head.PATH: self.path,
            Head.COMMIT_ID: self.commit_id
        }


class Refs(object):
    """
    Repository references.
    """

    HEADS = 'heads'

    @staticmethod
    def from_dict(d):
        """
        Construct using a dictionary representation.
        :param d: A dictionary representation.
        :type d: dict
        """
        heads = [Head.from_dict(h) for h in d[Refs.HEADS]]
        return Refs(heads)

    def __init__(self, heads=None):
        """
        :param heads: collection of heads.
        :type heads: iterable
        """
        self.heads = heads or []

    @property
    def digest(self):
        """
        Get the content-based digest.
        :return: The content-based digest.
        :rtype: str
        """
        h = sha256()
        for head in sorted(self.heads, key=lambda obj: obj.path):
            h.update(head.digest)
        return h.hexdigest()

    def to_dict(self):
        """
        Get a dictionary representation.
        :return: A dictionary representation.
        :rtype: dict
        """
        return {
            Refs.HEADS: [h.to_dict() for h in self.heads]
        }


class Repository(object):
    """
    An ostree repository unit.
    """

    TYPE_ID = constants.REPOSITORY_TYPE_ID

    REMOTE_ID = 'remote_id'
    TIMESTAMP = 'timestamp'
    DIGEST = 'digest'
    REFS = 'refs'

    @staticmethod
    def from_dict(d):
        """
        Construct using a dictionary representation.
        :param d: A dictionary representation.
        :type d: dict
        """
        return Repository(
            d[Repository.REMOTE_ID],
            Refs.from_dict(d[Repository.REFS]),
            d[Repository.TIMESTAMP])

    def __init__(self, remote_id, refs, timestamp):
        """
        :param remote_id: The unique identifier for the remote.
        :type remote_id: str
        :param timestamp: The unit timestamp in UTC.
        :type timestamp: datetime.datetime
        :param refs: The repository references.
        :type refs: Refs
        """
        self.remote_id = remote_id
        self.timestamp = timestamp
        self.refs = refs

    @property
    def digest(self):
        """
        Get the content-based digest.
        :return: The content-based digest.
        :rtype: str
        """
        return self.refs.digest

    @property
    def unit_key(self):
        """
        Get the unit key
        :return: The unit key.
        :rtype: dict
        """
        return {
            Repository.REMOTE_ID: self.remote_id,
            Repository.DIGEST: self.digest
        }

    @property
    def metadata(self):
        """
        Get the unit metadata
        :return: The unit metadata
        :rtype dict
        """
        return {
            Repository.TIMESTAMP: self.timestamp,
            Repository.REFS: self.refs.to_dict()
        }

    @property
    def relative_path(self):
        """
        :return: The relative path to where the unit is stored.
        :rtype: str
        """
        return os.path.join(self.TYPE_ID, self.remote_id)
