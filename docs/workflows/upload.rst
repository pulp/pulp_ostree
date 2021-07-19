Upload and Manage Content
=========================

Create a repository
-------------------

If you don't already have a repository, create one::

    $ http POST $BASE_ADDR/pulp/api/v3/repositories/ostree/ostree/ name=foo

Response::

    {
        "pulp_href": "http://localhost:24817/pulp/api/v3/repositories/ostree/ostree/9b19ceb7-11e1-4309-9f97-bcbab2ae38b6/",
        ...
    }


Upload a file to Pulp
---------------------

Each artifact in Pulp represents a file. They can be created during sync or created manually by uploading a file::

    $ http --form POST $BASE_ADDR/pulp/api/v3/artifacts/ file@./my_content

Response::

    {
        "pulp_href": "http://localhost:24817/pulp/api/v3/artifacts/6f847a21-a177-4a49-ad47-86f415b3830d/",
        ...
    }


Create content from an artifact
-------------------------------

Now that Pulp has the content, its time to make it into a unit of content.

    $ http POST $BASE_ADDR/pulp/api/v3/content/ostree/ artifact=http://localhost:24817/pulp/api/v3/artifacts/6f847a21-a177-4a49-ad47-86f415b3830d/ filename=my_content

Response::

    {
        "pulp_href": "http://localhost:24817/pulp/api/v3/content/ostree/ostree/ae016be0-0499-4547-881f-c56a1d0186a6/",
        "_artifact": "http://localhost:24817/pulp/api/v3/artifacts/6f847a21-a177-4a49-ad47-86f415b3830d/",
        "digest": "b5bb9d8014a0f9b1d61e21e796d78dccdf1352f23cd32812f4850b878ae4944c",
        "filename": "my-content",
    }

Add content to a repository
---------------------------

Once there is a content unit, it can be added and removed and from to repositories::

$ http POST $REPO_HREF/pulp/api/v3/repositories/ostree/ostree/9b19ceb7-11e1-4309-9f97-bcbab2ae38b6/modify/ add_content_units:="[\"http://localhost:24817/pulp/api/v3/content/ostree/ostree/ae016be0-0499-4547-881f-c56a1d0186a6/\"]"
