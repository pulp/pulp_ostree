.. _sync-workflow:

Synchronize a Repository
========================

Users can populate their repositories with content from an external sources by syncing
their repository.

Create a Repository
-------------------

Start by creating a new repository named "foo"::

    http POST ${BASE_ADDR}/pulp/api/v3/repositories/ostree/ostree/ name=foo

Response::

    {
        ...
        "pulp_href": "/pulp/api/v3/repositories/ostree/ostree/dfca3ec4-b5cf-474f-b561-25a9cb58f260/",
        ...
    }


Create a Remote
---------------

Creating a remote object informs Pulp about an external content source::

    http POST ${BASE_ADDR}/pulp/api/v3/remotes/ostree/ostree/ name='bar' url='https://www.redhat.com/ostree/repo'

Response::

    {
        ...
        "pulp_href": "/pulp/api/v3/remotes/ostree/ostree/e54203d8-afd5-4091-9fae-dad6419f8bfd/",
        ...
    }


Sync the Repository
-------------------

Use the remote object to kick off a synchronization task by specifying a repository to sync with.
This tells Pulp to fetch content from the remote and add it to the repository::

    http POST ${BASE_ADDR}${REPO_HREF}sync/ remote=${REMOTE_HREF}

Response::

    {
        "task": "/pulp/api/v3/tasks/88071cc2-10a7-4544-83ec-15f272cc28b1/"
    }

You can follow the progress of the task with a GET request to the task href. Notice that when the
synchronization task completes, it creates a new version, which is specified in
``created_resources``::

    http GET ${BASE_ADDR}${TASK_HREF}

Response::

    {
        "child_tasks": [],
        "created_resources": [],
        "error": null,
        "finished_at": null,
        "logging_cid": "856ea79a05db41c58a56606f92ac1e92",
        "name": "pulp_ostree.app.tasks.synchronizing.synchronize",
        "parent_task": null,
        "progress_reports": [
            {
                "code": "sync.parsing_metadata",
                "done": 0,
                "message": "Parsing Metadata",
                "state": "running",
                "suffix": null,
                "total": 1
            },
            {
                "code": "sync.downloading.artifacts",
                "done": 0,
                "message": "Downloading Artifacts",
                "state": "running",
                "suffix": null,
                "total": null
            },
            {
                "code": "associating.content",
                "done": 0,
                "message": "Associating Content",
                "state": "running",
                "suffix": null,
                "total": null
            }
        ],
        "pulp_created": "2021-09-03T13:21:44.580189Z",
        "pulp_href": "/pulp/api/v3/tasks/20f9d413-17f4-4e47-8255-a2aa4546c140/",
        "reserved_resources_record": [
            "/pulp/api/v3/repositories/ostree/ostree/92a6e331-7064-49eb-907b-93bcd0d137e1/",
            "/pulp/api/v3/remotes/ostree/ostree/0845b49b-4aba-4d26-870c-bae5d6da58e8/"
        ],
        "started_at": "2021-09-03T13:21:44.620293Z",
        "state": "running",
        "task_group": null,
        "worker": "/pulp/api/v3/workers/f2b26fd7-7fb6-4501-8a5e-98b71397e0bc/"
    }


.. note::

    The OSTree plugin currently supports only repositories with the modern ``archive`` format. The
    repository's config file still uses the historical term ``archive-z2`` to signify such a format.
