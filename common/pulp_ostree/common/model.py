"""
The content model:

{ remote_id: <id>, branch: <path>, commit: <commit>}
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


class Commit(object):
    """
    Commit object.

    :ivar digest: The commit (hash) digest.
    :type digest: str
    :ivar metadata: The commit metadata.
    :type metadata: dict
    """

    def __init__(self, digest, metadata):
        """
        :param digest: The commit (hash) digest.
        :type digest: str
        :param metadata: The commit metadata.
        :type metadata: dict
        """
        self.digest = digest
        self.metadata = metadata


class Head(object):
    """
    Tree reference.

    :ivar remote_id: Uniquely identifies an OSTree remote.
    :type remote_id: str
    :ivar branch: The branch head file path.
    :type branch: str
    :ivar commit: The branch head commit.
    :type commit: Commit
    """

    REMOTE_ID = 'remote_id'
    BRANCH = 'branch'
    COMMIT = 'commit'

    def __init__(self, remote_id, branch, commit):
        """
        :param remote_id: Uniquely identifies a *remote* OSTree repository.
        :type remote_id: str
        :param branch: The branch path.
        :type branch: str
        :param commit: A commit.
        :type commit: Commit
        """
        self.remote_id = remote_id
        self.branch = branch
        self.commit = commit

    @property
    def digest(self):
        """
        Get the content-based digest.

        :return: The content-based digest.
        :rtype: str
        """
        h = sha256()
        h.update(self.remote_id)
        h.update(self.branch)
        h.update(self.commit.digest)
        return h.hexdigest()

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


class Unit(Head):
    """
    Stored content unit.
    """
    TYPE_ID = constants.OSTREE_TYPE_ID

    COMMIT = 'commit'

    @property
    def key(self):
        """
        Unit Key.

        :return: The unit key.
        :rtype: dict
        """
        return {
            Head.REMOTE_ID: self.remote_id,
            Head.BRANCH: self.branch,
            Head.COMMIT: self.commit.digest
        }

    @property
    def metadata(self):
        """
        Unit Metadata.

        :return: The commit metadata.
        :rtype: dict
        """
        return self.commit.metadata
