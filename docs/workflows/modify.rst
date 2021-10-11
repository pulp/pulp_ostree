.. _modify-workflow:

Add or Remove Content
=====================

The `modify` endpoint can be used to manage repository content. This allows adding content to a new
repository from an existing repository or removing content that lives in the existing repository.
The related content is recursively added or removed by default. For instance, this means that the
commit referenced by a ref and all its related objects will be automatically added or removed from
a repository if only the ref is specified in order to preserve the integrity of the added ref and
commit.

Users remove content from a repository by issuing the following command::

    http POST ${BASE_ADDR}${REPO_HREF}modify/ remove_content_units:=\[\"${REF_HREF}\"\]

Response::

    {
        "task": "/pulp/api/v3/tasks/09dca059-ec1b-42c3-ad1d-540b41c173fd/"
    }

Similarly, to add content, one can pass the list of content units to be added, like so::

    http ${BASE_ADDR}${REPO_HREF}modify/ add_content_units:=\[\"${REF_HREF}"\]

Response::

    {
        "task": "/pulp/api/v3/tasks/09dca333-ec1b-41c3-ac2d-540b41c1aafd/"
    }

The added content can be verified by inspecting the latest repository version::

    http ${BASE_ADDR}${REPO_HREF}version/1/

Response::

    {
        "base_version": null,
        "content_summary": {
            "added": {
                "ostree.commit": {
                    "count": 1,
                    "href": "/pulp/api/v3/content/ostree/commits/?repository_version_added=/pulp/api/v3/repositories/ostree/ostree/15c51595-9b59-42a5-8c67-7599ed2f3fe6/versions/1/"
                },
                "ostree.object": {
                    "count": 1,
                    "href": "/pulp/api/v3/content/ostree/objects/?repository_version_added=/pulp/api/v3/repositories/ostree/ostree/15c51595-9b59-42a5-8c67-7599ed2f3fe6/versions/1/"
                },
                "ostree.refs": {
                    "count": 1,
                    "href": "/pulp/api/v3/content/ostree/refs/?repository_version_added=/pulp/api/v3/repositories/ostree/ostree/15c51595-9b59-42a5-8c67-7599ed2f3fe6/versions/1/"
                }
            },
            "present": {
                "ostree.commit": {
                    "count": 1,
                    "href": "/pulp/api/v3/content/ostree/commits/?repository_version=/pulp/api/v3/repositories/ostree/ostree/15c51595-9b59-42a5-8c67-7599ed2f3fe6/versions/1/"
                },
                "ostree.object": {
                    "count": 1,
                    "href": "/pulp/api/v3/content/ostree/objects/?repository_version=/pulp/api/v3/repositories/ostree/ostree/15c51595-9b59-42a5-8c67-7599ed2f3fe6/versions/1/"
                },
                "ostree.refs": {
                    "count": 1,
                    "href": "/pulp/api/v3/content/ostree/refs/?repository_version=/pulp/api/v3/repositories/ostree/ostree/15c51595-9b59-42a5-8c67-7599ed2f3fe6/versions/1/"
                }
            },
            "removed": {}
        },
        "number": 1,
        "pulp_created": "2021-10-13T10:21:04.996445Z",
        "pulp_href": "/pulp/api/v3/repositories/ostree/ostree/15c51595-9b59-42a5-8c67-7599ed2f3fe6/versions/1/",
        "repository": "/pulp/api/v3/repositories/ostree/ostree/15c51595-9b59-42a5-8c67-7599ed2f3fe6/"
    }


.. note::

    Bear in mind that the ``ostree`` utility may require the ``config`` file to be present in the
    published repository as well. Otherwise, the ``pull`` operations may not be successful.
