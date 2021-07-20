Publish and Host
================

This section assumes that you have a repository with content in it. To do this, see the
:doc:`sync` or :doc:`upload` documentation.

Create a Publication
--------------------

Publications contain extra settings for how to publish::

    $ http POST ${BASE_ADDR}/pulp/api/v3/publications/ostree/ostree/ repository=${REPO_HREF}

Response::

    {
        "task": "/pulp/api/v3/tasks/e66fb408-5dce-42df-90ac-45580a0a78be/"
    }


Host a Publication (Create a Distribution)
--------------------------------------------

To host a publication, (which makes it consumable by a package manager), users create a distribution which
will serve the associated publication at ``/pulp/content/<distribution.base_path>``::

    $ http POST ${BASE_ADDR}/pulp/api/v3/distributions/ostree/ostree/ name='baz' base_path='foo' publication=${PUBLICATION_HREF}

Response::

    {
        "task": "/pulp/api/v3/tasks/1974aa50-d862-4eb7-84a3-1dc4000f34bf/"
    }

