.. _modify-workflow:

Add or Remove Content
=====================

Users are allowed to copy and remove content within repositories. When a new ref is being added or
removed from a repository, all the referenced commits and file objects will be added or removed as
well in order to preserve the integrity of the repository.

Users add existing content to a repository by issuing the following commands:

.. code-block:: bash

    pulp ostree repository ref add --repository foo --name ${REF_NAME} --checksum ${COMMIT_CHECKSUM1}
    pulp ostree repository commit add --repository foo --checksum ${COMMIT_CHECKSUM2}
    pulp ostree repository config add --repository foo --pulp_href ${PULP_HREF_CONFIG}

The added content can be listed by inspecting the latest repository version:

.. code-block:: bash

    pulp ostree repository ref list --repository foo
    pulp ostree repository config list --repository foo --version 1

Similarly, to remove content, one specifies refs and commits that should be removed, like so:

.. code-block:: bash

    pulp ostree repository ref remove --repository foo --name ${REF_NAME} --checksum ${COMMIT_CHECKSUM1}
    pulp ostree repository commit remove --repository foo --checksum ${COMMIT_CHECKSUM2}

.. note::

    Bear in mind that the ``ostree`` utility may require the ``config`` file to be present in the
    published repository as well. Otherwise, the ``pull`` operations may not be successful.
