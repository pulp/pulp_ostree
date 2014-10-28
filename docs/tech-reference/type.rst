Type
====

The programmatic identifier for this type is ``ostree``.

Unit Key
--------

Each unit represents a *snapshot* of an ostree repository. The key identifies
each snapshot uniquely using a combination of the remote's URL and the digest
of the :term:`refs` contained with the unit itself.

``remote_id``
 The :term:`digest` of the URL to a remote ostree repository.

``digest``
 The :term:`digest` of the ostree :term:`refs` information.

Metadata
--------

``timestamp``
 The UTC timestamp of when the unit was created.

``refs``
 The :term:`refs` information::

   refs: {
      heads [
        {path: <path>, commit_id: <commit>},
        {path: <path>, commit_id: <commit>}
      ]
    }
