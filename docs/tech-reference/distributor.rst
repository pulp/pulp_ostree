Distributor Configuration
=========================

Web Distributor
---------------

Type ID: ``ostree_web_distributor``

The global configuration file for the ostree_web_distributor plugin
can be found in ``/etc/pulp/server/plugin.conf.d/ostree_distributor.json``.

All values from the global configuration can be overridden on the local config.

Supported keys
^^^^^^^^^^^^^^

``auto_publish``
 Whether or not this distributor should automatically be published when the importer completes.
 The default value is ``True``.