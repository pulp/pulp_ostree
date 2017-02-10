Installation
============

.. _Pulp User Guide: https://docs.pulpproject.org

Prerequisites
-------------

``libostree`` is required for this plugin. As of this writing, both Fedora and
RHEL package it as part of the ``ostree`` RPM. On RHEL, you may need to enable
an Atomic-related channel to access the ``ostree`` package.

The other requirement is to meet the prerequisites of the Pulp Platform. Please
see the `Pulp User Guide`_ for prerequisites including repository setup.

Server
------

First stop all Pulp services on your servers, the same as if doing an upgrade.

Then install the new RPM.

::

    $ sudo yum install pulp-ostree-plugins

Then run ``pulp-manage-db`` to initialize the new type in Pulp's database.

::

    $ sudo -u apache pulp-manage-db


Then restart each pulp component, as documented in the `Pulp User Guide`_.

Admin Client
------------

::

    $ sudo yum install pulp-ostree-admin-extensions
