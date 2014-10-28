Recipes
=======

Create A Repository
-------------------

A repository may be created using pulp-admin::

  $ pulp-admin ostree repo create --repo-id=f21 \
      --feed=http://dl.fedoraproject.org/pub/alt/fedora-atomic/repo/ \
      -b fedora-atomic/rawhide/x86_64/server/docker-host \
      -b fedora-atomic/rawhide/x86_64/docker-host

Update Branches
---------------
A repository may be updated to add/remove branches. Each update replaces the list
of branches::

  $ pulp-admin ostree repo update --repo-id=f21 -b fedora-atomic/rawhide/x86_64/docker-host

Synchronize Repository
----------------------

A repository may be synchronized with its remote::

  $ pulp-admin ostree repo sync run --repo-id=f21

List Content
------------
The content contained within a repository may be listed::

  $ pulp-admin ostree repo search --repo-id=f21
  +----------------------------------------------------------------------+
                               Content Units
  +----------------------------------------------------------------------+

  Id:        54465eafe138231f61748822
  Created:   2014-10-21T13:25:03Z
  Updated:   2014-10-21T13:25:03Z
  Timestamp: 2014-10-21T13:25:03Z
  Remote Id: fe3150788b0d5f396a4834c7be7ec4f83d47fda8b3f9ff8404a789c28d4d22e7
  Digest:    e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
  Refs:
    Heads:

  Id:        544673d0e138231f61748824
  Created:   2014-10-21T14:55:12Z
  Updated:   2014-10-21T14:55:12Z
  Timestamp: 2014-10-21T14:55:12Z
  Remote Id: fe3150788b0d5f396a4834c7be7ec4f83d47fda8b3f9ff8404a789c28d4d22e7
  Digest:    7f2343063a9daa18b062507980da0b3718a28bf3b31d1286e8ef8655821f42f7
  Refs:
    Heads:
      Commit Id: 005d4caafc862853b920b9a0ab2f5af2b197cc13024a49a6add85bae4a8a40ee
      Path:      fedora-atomic/rawhide/x86_64/docker-host

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

