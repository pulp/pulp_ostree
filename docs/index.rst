Pulp OSTree Plugin
==================

The OSTree plugin extends `pulpcore <https://pypi.python.org/pypi/pulpcore/>`__ to support
hosting OSTree packages. This plugin is a part of the `Pulp Project <http://www.pulpproject.org>`_,
and assumes some familiarity with the `pulpcore documentation
<https://docs.pulpproject.org/pulpcore/>`_.

If you are just getting started, we recommend getting to know the :doc:`basic
workflows<workflows/index>`.

Features
--------

* :ref:`Synchronize <sync-workflow>` a remote OSTree repository and serve it via Pulp.
* :ref:`Import <import-workflow>` new OSTree commits to an existing repository.
* :ref:`Modify <modify-workflow>` commits and refs within a published repository.
* :ref:`Consume <publish-workflow>` OSTree content imported to Pulp by leveraging the
  `ostree` utility.

Table of Contents
-----------------

.. toctree::
   :maxdepth: 1

   installation
   workflows/index
   restapi
   changes
   contributing


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

