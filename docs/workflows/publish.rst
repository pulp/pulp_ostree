Publish and Host
================

This section assumes that you have a repository with content in it. To do this, see the
:doc:`sync` or :doc:`upload` documentation.

Create a Publication
--------------------

Publications contain extra settings for how to publish.::

$ http POST $BASE_ADDR/pulp/api/v3/publications/ostree/ostree/ name=bar

Response::

    {
        "pulp_href": "http://localhost:24817/pulp/api/v3/publications/ostree/ostree/bar/",
        ...
    }


Host a Publication (Create a Distribution)
--------------------------------------------

To host a publication, (which makes it consumable by a package manager), users create a distribution which
will serve the associated publication at ``/pulp/content/<distribution.base_path>``::

$ http POST $BASE_ADDR/pulp/api/v3/distributions/ostree/ostree/ name='baz' base_path='foo' publication=$BASE_ADDR/publications/5fcb3a98-1bd1-445f-af94-801a1d563b9f/

Response::

    {
        "pulp_href": "http://localhost:24817/pulp/api/v3/distributions/2ac41454-931c-41c7-89eb-a9d11e19b02a/",
       ...
    }

