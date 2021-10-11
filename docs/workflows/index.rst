Workflows
=========

If you have not yet installed the OSTree plugin on your Pulp installation, please, follow our
:doc:`../installation` guide. These documents will assume you have the environment installed and
ready to go.

The REST API examples in the workflows use `httpie <https://httpie.org/doc>`_ to send HTTP requests.
Through all examples, there is an assumption that the user executing the commands has the ``.netrc``
file configured in the home directory. The ``.netrc`` file should have the following configuration:

.. code-block:: bash

    machine localhost
    login admin
    password admin

If you configured the ``admin`` user with a different password, adjust the configuration
accordingly. If you prefer to specify the username and password with each request, please see
``httpie`` documentation on how to do that.

To make these workflows copy/pastable, we make use of environment variables. The first variable to
set is the hostname and port::

   export BASE_ADDR=http://<hostname>:24817


Furthermore, it is recommended to install the following utilities for managing local copies of
OSTree repositories:

* `ostree <https://manpages.debian.org/testing/ostree/ostree.1.en.html>`_ - a CLI tool for managing
  versioned filesystem trees
* `osbuild-composer <https://github.com/osbuild/osbuild-composer>`_ - an HTTP service for building
  bootable OS images
* `composer-cli <https://www.osbuild.org/guides/user-guide/building-ostree-images.html>`_ - a tool
  for use with a WELDR API server, managing blueprints, or building new images

The utilities are used to demonstrate the way how to create and consume OSTree content. Also, for
the best user experience, some workflows utilize `Pulp CLI <https://docs.pulpproject.org/pulp_cli/>`_.


.. toctree::
   :maxdepth: 2

   sync
   import
   modify
   publish
