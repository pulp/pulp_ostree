"""
Migration to remove Branch._created which is no longer used.
"""

from pulp.server.db import connection


def migrate(*args, **kwargs):
    """
    Remove Branch._created which is no longer used.

    :param args: unused
    :type  args: tuple
    :param kwargs: unused
    :type  kwargs: dict
    """
    collection = connection.get_collection('units_ostree')
    collection.update_many({}, {'$unset': {'_created': ''}})
