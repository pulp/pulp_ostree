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
 An array of branch names from the upstream repository that should be pulled
 during a sync. If an empty array is provided, the list of branches will be
 populated on the repository scratchpad, but no branches will be retrieved. The
 default is to retrieve all branches.

``depth``
 The tree traversal depth. This determines how much history is pulled from the remote.
 A value of ``-1`` indicates infinite. The default is: ``0``.

``gpg_keys``
 An array of keys that can be used to validate signed branches.
