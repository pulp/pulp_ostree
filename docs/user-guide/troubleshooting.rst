Troubleshooting
===============


Corrupted Local Repository
--------------------------

The :term:`storage` repository can be corrupted when the Pulp worker terminates
abnormally during a pull operation. One indicator of corruption is the logging of this
exception during publishing::

 GLib.Error('No such file or directory', 'g-io-error-quark', 1)

The recommended remedy is to pass the `repair` option to the sync API call. Or, when using
CLI, the `--repair|-r` option may be specified::

 pulp-admin ostree sync run -r --repo-id=f25

The repair may require that the importer delete and recreated the storage. Repositories configured
with limited tree traversal depth or a subset of branches to be pulled should use caution. If the
local repository needs to be recreated, it will be done so using the current configuration.
Branches or commits pulled previously based on earlier configuration will not be included and may
result in broken publishes.
