Recipes
=======

Create A Repository
-------------------

A repository may be created using pulp-admin::

  $ pulp-admin ostree repo create --repo-id=f25 \
      --feed=http://dl.fedoraproject.org/pub/fedora/linux/atomic/25/ \
      -b fedora-atomic/25/x86_64/docker-host

Update Branches
---------------
A repository may be updated to add/remove branches. Each update replaces the list
of branches::

  $ pulp-admin ostree repo update --repo-id=f25 -b fedora-atomic/25/x86_64/docker-host

Synchronize Repository
----------------------

A repository may be synchronized with its remote::

  $ pulp-admin ostree repo sync run --repo-id=f25

List Content
------------
The content contained within a repository may be listed::

  $ pulp-admin ostree repo search --repo-id=f25
  +----------------------------------------------------------------------+
                               Content Units
  +----------------------------------------------------------------------+

  Id:        9ebf36e4-1f01-4064-a151-c60e9c256a40
  Created:   2017-01-24T21:42:41Z
  Updated:   2017-01-24T21:42:41Z
  Remote Id: d9680ea424e704ad20d57011c054adb7e3f4ad43f8849c0e1eb9efd4f0ba9bf1
  Branch:    fedora-atomic/25/x86_64/docker-host
  Commit:    27b1ae24686697235c35b793b5c8ab0822b8427e892d3659f0cb300c400979fa
  Version:   25.46


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

 +----------------------------------------------------------------------+
                          OSTree Repositories
 +----------------------------------------------------------------------+

 Id:                  f25
 Display Name:        None
 Description:         None
 Content Unit Counts:
   Ostree: 1
 Notes:
 Scratchpad:
   Remote:
     Summary:
       Commit:   27b1ae24686697235c35b793b5c8ab0822b8427e892d3659f0cb300c400979fa
       Metadata:
         Rpmostree-inputhash: 960578ee113bce7ce7213e7b487db2534cb3ffb33d6055b7e86
                              7dfe44a2e8f94
         Version:             25.46
       Name:     fedora-atomic/25/x86_64/docker-host
 Importers:
   Config:
     Branches: fedora-atomic/25/x86_64/docker-host
     Feed:     https://kojipkgs.fedoraproject.org/atomic/25/
   Id:                   ostree_web_importer
   Importer Type Id:     ostree_web_importer
   Last Override Config:
   Last Sync:            2017-01-24T21:53:16Z
   Last Updated:         2017-01-24T21:53:45Z
   Repo Id:              f25
   Scratchpad:           None
 Distributors:
   Auto Publish:         True
   Config:
     Relative Path: /atomic/25/
   Distributor Type Id:  ostree_web_distributor
   Id:                   ostree_web_distributor_name_cli
   Last Override Config:
   Last Publish:         2017-01-24T21:53:22Z
   Last Updated:         2017-01-24T21:34:57Z
   Repo Id:              f25
   Scratchpad:




This information is included in the repository ``scratchpad`` and provides a list of branches
contained within the remote repository.

Fields:

 Name
   The branch name.

 Commit
   The branch head commit hash.

 Metadata
   The commit metadata which by convention may include an optional ``version`` property.


Copy
----

To copy a specific branch from one repository to another, first create the new repository::

	$ pulp-admin ostree repo create --repo-id=f25-test

Then run a copy command::

	$ pulp-admin ostree repo copy -f f25 -t f25-test --str-eq='branch=fedora-atomic/25/x86_64/testing/docker-host'
	This command may be exited via ctrl+c without affecting the request.


	[\]
	Running...

	Copied:
	  remote_id:d9680ea424e704ad20d57011c054adb7e3f4ad43f8849c0e1eb9efd4f0ba9bf1
	branch:fedora-atomic/25/x86_64/testing/docker-host
	commit:35c51948ffdc01c7f235796efcd2b34c7d14b3f1feb417a2ce849ecf2ec13bb2
