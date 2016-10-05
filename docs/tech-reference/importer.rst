Importer Configuration
======================

Web Importer
------------

TYPE ID: ``ostree_web_importer``

Properties
^^^^^^^^^^

``feed``
 The URL for the upstream ostree repository to sync.

``branches``
 A list of branches from the upstream repo that should be pulled during a sync.

``depth``
 The tree traversal depth. This determines how much history is pulled from the remote.
 A value of ``-1`` indicates infinite. The default is: ``0``.
