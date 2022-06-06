.. _sync-workflow:

Synchronize a Repository
========================

Users can populate their repositories with content from an external sources by syncing
their repository.

Create a Repository
-------------------

Start by creating a new repository named "foo"::

    pulp ostree repository create --name foo

Create a Remote
---------------

Creating a remote object informs Pulp about an external content source::

    pulp ostree remote create --name bar --url https://fixtures.pulpproject.org/ostree/small/

Use the standard Linux wildcards ``*``, ``?`` to include or exclude refs from a remote repository
when syncing::

    pulp ostree remote create --name bar-filtered --url https://fixtures.pulpproject.org/ostree/small/ --include-refs "[\"stable\"]" --exclude-refs "[\"raw*\"]"

Sync the Repository
-------------------

Use the remote object to kick off a synchronization task by specifying a repository to sync with.
This tells Pulp to fetch content from the remote source and add it to the repository::

    pulp ostree repository sync --name foo --remote bar

.. note::

    The OSTree plugin currently supports only repositories with the modern ``archive`` format. The
    repository's config file still uses the historical term ``archive-z2`` to signify such a format.
