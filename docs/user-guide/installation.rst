Installation
============

.. _Pulp User Guide: https://docs.pulpproject.org

Prerequisites
-------------

The only requirement is to meet the prerequisites of the Pulp Platform. Please
see the `Pulp User Guide`_ for prerequisites including repository setup.

Development
-----------

The only way to install ostree support currently is to setup a development
environment. Installation through RPMs will come at a later time.

::

    git clone https://github.com/pulp/pulp_ostree.git
    cd pulp_ostree
    sudo ./manage_setup_pys.sh develop
    sudo ./pulp-dev.py -I
    sudo -u apache pulp-manage-db

Then restart each pulp component, as documented in the `Pulp User Guide`_.
