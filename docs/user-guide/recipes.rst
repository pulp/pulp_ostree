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

 Remote Id
   Indicates which :term:`remote` this unit (branch) was pulled from.

 Branch
   The branch reference. Each reference is a path to a file containing the branch head commit.

 Commit
   The branch head commit hash.

 Version
   The (optional) version property contained in the commit metadata.


View Summary Information
------------------------

The summary information fetched from the remote repository can be viewed by listing
OSTree repositories and including the ``--details`` option::

 $ pulp-admin ostree repo list --details
 +----------------------------------------------------------------------+
                          OSTree Repositories
 +----------------------------------------------------------------------+

 Id:                  f23
 Display Name:        None
 Description:         None
 Content Unit Counts:
   Ostree: 1
 Notes:
 Scratchpad:
   Remote:
     Summary:
       Commit:   099d0138bef28bde23e0bb8cf5377fe549e90f9fe0d28d6c2956fdf86b63e1aa
       Metadata:
         Rpmostree-inputhash: 52f47deff0333b5f7c2a950c13d1902f98b3610e11ec1900950
                              9a775d180ac90
         Version:             23.44
       Name:     fedora-atomic/f23/x86_64/docker-host
       Commit:   8def7a3c424c8439e9807d464255ebabd7798dd649d0f0a6850bab0e18dbcadc
       Metadata:
         Rpmostree-inputhash: 5e38595e838c601be3cb8ff8afa574bbd152ea1cccef6605178
                              45d456cda1edc
         Version:             23.41
       Name:     fedora-atomic/f23/x86_64/testing/docker-host

This information is included in the repository ``scratchpad`` and provides a list of branches
contained within the remote repository.

Fields:

 Name
   The branch name.

 Commit
   The branch head commit hash.

 Metadata
   The commit metadata which by convention may include an optional ``version`` property.
