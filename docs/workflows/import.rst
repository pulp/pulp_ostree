.. _import-workflow:

Import Content
==============

Create a Repository
-------------------

If you don't already have a repository, create one::

    http POST ${BASE_ADDR}/pulp/api/v3/repositories/ostree/ostree/ name=foo

Response::

    {
        ...
        "pulp_href": "/pulp/api/v3/repositories/ostree/ostree/9b19ceb7-11e1-4309-9f97-bcbab2ae38b6/",
        ...
    }


Import a Commit
---------------

First, build an OSTree commit and wait until the process finishes::

    echo """
    name = "fishy-commit"
    description = "Fishy OSTree commit"
    version = "0.0.1"

    [[packages]]
    name = "fish"
    version = "*"
    """ > fishy.toml

    sudo composer-cli blueprints push fishy.toml
    sudo composer-cli compose start fishy-commit fedora-iot-commit
    sudo composer-cli compose status

Download the result from the server by issuing::

    composer-cli compose image ${TASK_UUID}

Upload the downloaded tarball to Pulp::

    pulp artifact upload --file ${COMMIT1_TARBALL_FILE}

Response::

    {
        ...
        "pulp_href": "/pulp/api/v3/artifacts/9baea722-68bb-4d0b-aefb-b9101914727e/",
        ...
    }

Import the uploaded file to the repository and wait until the task finishes::

    http ${BASE_ADDR}${REPO_HREF}import_commits/ artifact=${COMMIT1_ARTIFACT_HREF} repository_name=repo

Response::

    {
        "task": "/pulp/api/v3/tasks/f71f9caa-82bb-463c-8ca4-1f81e5113747/"
    }

Add more Commits
----------------

If there is a need to import additional commits, one can do so by attaching new commits to the last
commit in the existing repository::

    echo """
    name = "vim-commit"
    description = "Vim OSTree commit"
    version = "0.0.2"

    [[packages]]
    name = "vim"
    version = "*"
    """ > vim.toml

    sudo composer-cli blueprints push vim.toml
    sudo composer-cli compose start vim-commit fedora-iot-commit
    sudo composer-cli compose status

Download the result from the server by issuing::

    composer-cli compose image ${TASK_UUID}

Upload the downloaded tarball to Pulp::

    pulp artifact upload --file ${COMMIT2_TARBALL_FILE}

Response::

    {
        ...
        "pulp_href": "/pulp/api/v3/artifacts/9baea722-68bb-4d0b-aefb-b91019147444/",
        ...
    }

Import the uploaded file to the repository and wait until the task finishes::

    http ${BASE_ADDR}${REPO_HREF}import_commits/ artifact=${COMMIT2_ARTIFACT_HREF} repository_name=repo ref=fedora/33/x86_64/iot parent_commit=50aeff7f74c66041ffc9e197887bfd5e427248ff1405e0e61e2cff4d3a1cecc7

Response::

    {
        "task": "/pulp/api/v3/tasks/f71f9caa-82bb-463c-8ca4-1f81e5113747/"
    }


.. note::

    The OSTree plugin currently supports only repositories with the modern ``archive`` format. The
    repository's config file still uses the historical term ``archive-z2`` to signify such a format.
