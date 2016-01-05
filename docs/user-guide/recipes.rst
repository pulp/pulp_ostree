Recipes
=======

Create A Repository
-------------------

A repository may be created using pulp-admin::

  $ pulp-admin ostree repo create --repo-id=f23 \
      --feed=http://dl.fedoraproject.org/pub/fedora/linux/atomic/23/ \
      -b fedora-atomic/f23/x86_64/docker-host

Update Branches
---------------
A repository may be updated to add/remove branches. Each update replaces the list
of branches::

  $ pulp-admin ostree repo update --repo-id=f23 -b fedora-atomic/f23/x86_64/docker-host

Synchronize Repository
----------------------

A repository may be synchronized with its remote::

  $ pulp-admin ostree repo sync run --repo-id=f23

List Content
------------
The content contained within a repository may be listed::

  $ pulp-admin ostree repo search --repo-id=f23
  +----------------------------------------------------------------------+
                               Content Units
  +----------------------------------------------------------------------+

  Id:        a80df750-7b21-4b90-9171-f743bd04fafb
  Created:   2015-12-22T20:49:25Z
  Updated:   2015-12-22T20:49:25Z
  Remote Id: d2f04e37db9caadb59f8f227b0ec6e5fa4128feda4c048ad2ebcb3e1d925d773
  Branch:    fedora-atomic/f23/x86_64/docker-host
  Commit:    aab6ef55dd4287de725c42f03bae52deaced986ca62a988f7c795501951dbf8f
  Version:   23.38


Fields:

 Id
   The unit identifier.

 Created
   Indicates when the unit was first associated to the repository.

 Updated
   Indicates when the unit associated was last updated.

 Timestamp
   Indicates when the ostree repository :term:`snapshot` was taken.

 Remote Id
   Indicates which :term:`remote` this unit is a snapshot of.

 Digest
   The :term:`digest` of the :term:`refs` metadata.

 Refs
   The unit's :term:`refs` metadata.

