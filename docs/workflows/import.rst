.. _import-workflow:

Import Content
==============

Create a Repository
-------------------

Create a new repository by running::

    pulp ostree repository create --name fedora-iot

Import a Commit
---------------

First, build an image representing one OSTree commit and wait until the process finishes::

    echo """
    name = "fishy-commit"
    description = "Fishy OSTree commit"
    version = "0.0.1"

    [[packages]]
    name = "fish"
    version = "*"
    """ > fishy.toml

    sudo composer-cli blueprints push fishy.toml
    sudo composer-cli compose start-ostree fishy-commit fedora-iot-commit --ref fedora/stable/x86_64/iot
    sudo composer-cli compose status

Download the result from the server by issuing::

    sudo composer-cli compose image ${TASK_UUID}

Import the downloaded tarball into Pulp::

    pulp ostree repository import-commits --name fedora-iot --file ${IMAGE_TARBALL_C1} --repository_name repo

.. note::
    The argument ``repository_name`` describes the name of an OSTree repository that is contained
    within the tarball.

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
    sudo composer-cli compose start-ostree vim-commit fedora-iot-commit --ref fedora/stable/x86_64/iot --parent ${PARENT_COMMIT_CHECKSUM}
    sudo composer-cli compose status

.. note::
    The checksum of a parent commit can be seen either from the Pulp API endpoint that lists all refs
    or from the extracted ref that was archived in a tarball.

Download the result from the server by issuing::

    composer-cli compose image ${TASK_UUID}

Import the downloaded tarball into Pulp::

    pulp ostree repository import-commits --name fedora-iot --file ${IMAGE_TARBALL_C2} --repository_name repo --ref fedora/stable/x86_64/iot

.. note::

    The OSTree plugin currently supports only repositories with the modern ``archive`` format. The
    repository's config file still uses the historical term ``archive-z2`` to signify such a format.
