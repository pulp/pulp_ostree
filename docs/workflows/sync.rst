Synchronize a Repository
========================

Users can populate their repositories with content from an external sources by syncing
their repository.

Create a Repository
-------------------

Start by creating a new repository named "foo"::

    $ http POST ${BASE_ADDR}/pulp/api/v3/repositories/ostree/ostree/ name=foo

Response::

    {
        ...
        "pulp_href": "/pulp/api/v3/repositories/ostree/ostree/dfca3ec4-b5cf-474f-b561-25a9cb58f260/",
        ...
    }


Create a Remote
---------------

Creating a remote object informs Pulp about an external content source::

    $ http POST ${BASE_ADDR}/pulp/api/v3/remotes/ostree/ostree/ name='bar' url='https://www.redhat.com/'

Response::

    {
        ...
        "pulp_href": "/pulp/api/v3/remotes/ostree/ostree/e54203d8-afd5-4091-9fae-dad6419f8bfd/",
        ...
    }


Sync repository foo with remote
-------------------------------

Use the remote object to kick off a synchronize task by specifying the repository to
sync with. You are telling pulp to fetch content from the remote and add to the repository::

    $ http POST ${BASE_ADDR}${REPO_HREF}sync/ remote=${REMOTE_HREF}

Response::

    {
        "task": "/pulp/api/v3/tasks/88071cc2-10a7-4544-83ec-15f272cc28b1/"
    }

You can follow the progress of the task with a GET request to the task href. Notice that when the
synchroinze task completes, it creates a new version, which is specified in ``created_resources``::

    $  http GET ${BASE_ADDR}${TASK_HREF}

Response::

    {
        "child_tasks": [],
        "created_resources": [],
        "error": null,
        "finished_at": "2021-07-20T10:27:16.922875Z",
        "logging_cid": "014ba45a05514fb798b8475cd0c53c39",
        "name": "pulp_ostree.app.tasks.synchronizing.synchronize",
        "parent_task": null,
        "progress_reports": [
            {
                "code": "sync.downloading.artifacts",
                "done": 0,
                "message": "Downloading Artifacts",
                "state": "completed",
                "suffix": null,
                "total": null
            },
            {
                "code": "associating.content",
                "done": 0,
                "message": "Associating Content",
                "state": "completed",
                "suffix": null,
                "total": null
            }
        ],
        "pulp_created": "2021-07-20T10:27:14.874408Z",
        "pulp_href": "/pulp/api/v3/tasks/88071cc2-10a7-4544-83ec-15f272cc28b1/",
        "reserved_resources_record": [
            "/pulp/api/v3/repositories/ostree/ostree/dfca3ec4-b5cf-474f-b561-25a9cb58f260/",
            "/pulp/api/v3/remotes/ostree/ostree/e54203d8-afd5-4091-9fae-dad6419f8bfd/"
        ],
        "started_at": "2021-07-20T10:27:14.937455Z",
        "state": "completed",
        "task_group": null,
        "worker": "/pulp/api/v3/workers/32cdd2a4-40a0-4b36-872d-4209cdfd1aef/"
    }
