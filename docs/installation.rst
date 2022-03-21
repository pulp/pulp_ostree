User Setup
==========

Install ``pulpcore``
--------------------

Follow the `installation instructions <https://docs.pulpproject.org/pulpcore/installation/instructions.html>`_
provided with pulpcore.

Install plugin
--------------

The following sections assume that ``pulpcore`` is `installed <https://docs.pulpproject.org/pulpcore/installation/instructions.html>`_
into the virtual environment ``pulpvenv``.

Users should install the plugin **either** from PyPI or source. The plugin utilizes some of the
features provided by `libostree <https://github.com/ostreedev/ostree>`_. Please, install it on the
system as well.

From PyPI
*********

.. code-block:: bash

    sudo -u pulp -i
    source ~/pulpvenv/bin/activate
    pip install pulp-ostree

From Source
***********

.. code-block:: bash

   sudo -u pulp -i
   source ~/pulpvenv/bin/activate
   git clone https://github.com/pulp/pulp_ostree
   cd pulp_ostree
   pip install -e .
   django-admin runserver 24817

Make and Run Migrations
-----------------------

.. code-block:: bash

   pulp-manager makemigrations pulp_ostree
   pulp-manager migrate pulp_ostree


Run Services
------------

.. code-block:: bash

   pulp-manager runserver
   gunicorn pulpcore.content:server --bind 'localhost:24816' --worker-class 'aiohttp.GunicornWebWorker' -w 2
   sudo systemctl restart pulpcore
   sudo systemctl restart pulpcore-content
   sudo systemctl restart pulpcore-api
   sudo systemctl restart pulpcore-worker@1
   sudo systemctl restart pulpcore-worker@2
