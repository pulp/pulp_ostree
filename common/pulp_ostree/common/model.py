"""
The content model:

{ remote_id: <id>
  digest: <hex-digest>
  timestamp: <timestamp>
  refs: {
    heads [
      path: <path>, commit_id: <commit>,
      path: <path>, commit_id: <commit>,
    ]
  }
}
"""

import os

from hashlib import sha256

from pulp_ostree.common import constants


def generate_remote_id(url):
    """
    Generate a remote_id based on the url.

    :param url: The remote URL.
    :type url: basestring
    :return: The generated ID.
    :rtype:str
    """
    h = sha256()
    h.update(url)
    return h.hexdigest()


class Head(object):
    """
    Branch (tree) head.

    :cvar PATH: The path dictionary key.
    :type PATH: str
    :cvar COMMIT_ID: The commit_id dictionary key.
    :type COMMIT_ID: str

    :ivar path: The branch head file path.
    :type path: str
    :ivar commit_id: The unique identifier for the commit
        object that is the branch head.
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
    Repository *refs/* content.  Currently this only contains
    the branch heads but will likely contain tags when they are
    supported by ostree.

    :cvar HEADS: The heads dictionary key.
    :type HEADS: str

    :ivar heads: The list of branch head objects.
    :type heads: list
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

    def add_head(self, head):
        """
        Add the specified head.
        :param head: The head to add.
        :type head: Head
        """
        self.heads.append(head)

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
    An ostree repository content unit.

    :cvar TYPE_ID: The content type ID.
    :type TYPE_ID: str
    :cvar REMOTE_ID: The remote_id dictionary key.
    :type REMOTE_ID: str
    :cvar TIMESTAMP: The timestamp dictionary key.
    :type TIMESTAMP: str
    :cvar DIGEST: The digest dictionary key.
    :type DIGEST: str
    :cvar REFS: The refs dictionary key.
    :type REFS: str

    :ivar remote_id: The unique identifier for the remote ostree repository.
        This is likely to be the sha256 digest of the remote URL until
        something is supported by ostree.
    :type remote_id: str
    :ivar timestamp: The UTC timestamp of when the repository snapshot
        was taken.
    :type timestamp: datetime.datetime
    :ivar refs: The repository references.
    :type refs: Refs
    """

    TYPE_ID = constants.OSTREE_TYPE_ID

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
        Get the unit key.

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
    def storage_path(self):
        """
        :return: The unit storage path.
        :rtype: str
        """
        return os.path.join(constants.SHARED_STORAGE,
                            self.remote_id,
                            constants.LINKS_DIR,
                            self.digest)
