Glossary
========

.. Please keep glossary entries in alphabetical order

.. glossary::

  local
    A ``local`` ostree repository is stored in Pulp's content storage location.

  storage
    The :term:`local` ostree repository used for content storage.

  remote
    A ``remote`` repository is external to Pulp and is identified by its URL.

  remote_id
    Uniquely identifies an external ostree repository.  It is the :term:`digest`
    of its URL.

  digest
    A SHA256 HEX digest of an object.

  refs
    The *references* section of an ostree repository defines branches and
    commit (hash) that defines the branch head::

     -rw-rw-r--   1 root pulp  124 Sep 11 15:25 config
     drwxrwxr-x   1 root pulp 4096 Aug 27 16:02 objects
     drwxrwxr-x   4 root pulp 4096 Aug 27 15:55 refs  <------------- HERE
     drwxrwxr-x   2 root pulp 4096 Aug 27 15:55 remote-cache
     drwxrwxr-x   2 root pulp 4096 Sep  2 13:04 tmp
     drwxrwxr-x   2 root pulp 4096 Aug 27 15:55 uncompressed-objects-cache

  tree
    An named ostree branch

  branch
    A specific version of a filesystem tree.

  snapshot
    After all branches have been pulled during repository synchronization
    with a remote, a unit is created containing the :term:`refs`.