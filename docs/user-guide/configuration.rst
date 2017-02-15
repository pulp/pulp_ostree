Configuration
=============

Importer Configuration
----------------------

The OSTree importer is configured by editing
``/etc/pulp/server/plugins.conf.d/ostree_importer.json``. This file must be valid `JSON`_.

.. _JSON: http://json.org/

The importer supports the settings documented in Pulp's `importer config docs`_ with the addition
of a the following OSTree specific properties:

- ``branches`` - A list of branch names to be pulled during repository synchronization.
  When the value is ``nil`` (or not specified), all branches will be pulled.
- ``gpg_keys`` - An (optional) list of GPG keys used to validate signed commits.
- ``repair`` - An (optional) boolean that requests the importer repair corrupted :term:`storage`.
  The repair may require that the importer delete and recreated the storage. Repositories
  configured with limited tree traversal depth or a subset of branches to be pulled should use
  caution. If the local repository needs to be recreated, it will be done so using the current
  configuration.  Branches or commits pulled previously based on earlier configuration will not
  be included and may result in broken publishes. Defaults to ``false`` when not passed.


.. _importer config docs: https://docs.pulpproject.org/en/latest/server.html#importers
