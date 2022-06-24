Workflows
=========

.. note::

    If the OSTree plugin has not yet been configured, please, follow the :doc:`../installation` guide.
    These documents assume that users have their environment configured and ready to go.

For managing local copies of OSTree repositories, it is recommended to instal the following utilities:

* `ostree <https://manpages.debian.org/testing/ostree/ostree.1.en.html>`_ - a CLI tool for managing
  versioned filesystem trees
* `osbuild-composer <https://github.com/osbuild/osbuild-composer>`_ - an HTTP service for building
  bootable OS images
* `composer-cli <https://www.osbuild.org/guides/user-guide/building-ostree-images.html>`_ - a tool
  for use with a WELDR API server, managing blueprints, or building new images

The utilities are used to demonstrate the way how to create and consume OSTree content.

For the best user experience, the workflows utilize `Pulp CLI <https://docs.pulpproject.org/pulp_cli/>`_.
Install the CLI for the OSTree plugin by running:

.. code-block:: bash

    pip install pulp-cli-ostree

`Configure <https://docs.pulpproject.org/pulp_cli/configuration/>`_ the reference to the Pulp server
for the CLI by running:

.. code-block:: bash

    pulp config create && pulp config edit


.. toctree::
   :maxdepth: 2

   sync
   publish
   import
   modify
