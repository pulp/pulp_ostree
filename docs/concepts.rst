Concepts
========

Repositories
------------

An ostree content unit represents a snapshot of an ostree repository. Pulp repositories
are created and synchronized with :term:`remote` repositories. Each unit created
during synchronization with the same remote is stored in the same :term:`local`
ostree repository. Each unit is uniquely identified by the :term:`remote_id` and the
:term:`digest` of the local repository's :term:`refs`. The unit metadata stores the
content of the repository's ``refs``.

A Pulp ostree repository is configured with a list of branches (or trees). This
list determines which branches are pulled each time it is synchronized
with its remote.  The list of branches may be modified.

Repository ``refs`` can be added, updated and deleted.  But, content objects stored
in ``local`` repositories are immutable and cannot be deleted.  An orphaned
local repository is removed during orphan removal.
