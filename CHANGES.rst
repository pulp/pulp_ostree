=========
Changelog
=========

..
    You should *NOT* be adding new change log entries to this file, this
    file is managed by towncrier. You *may* edit previous change logs to
    fix problems like typo corrections or such.

    WARNING: Don't drop the next directive!

.. towncrier release notes start

2.1.1 (2023-07-12)
==================

Bugfixes
--------

- Started re-generating summary files and publishing them during the import.
  `#269 <https://github.com/pulp/pulp_ostree/issues/269>`_


----


2.1.0 (2023-05-28)
==================

Features
--------

- Made the plugin compatible with Django 4.2 and pulpcore 3.25.
  `#258 <https://github.com/pulp/pulp_ostree/issues/258>`_


Bugfixes
--------

- Fixed the path resolution when a user specifies absolute paths when importing repositories.
  `#226 <https://github.com/pulp/pulp_ostree/issues/226>`_
- Fixed a bug that disallowed users to pull re-synced content locally.
  `#257 <https://github.com/pulp/pulp_ostree/issues/257>`_
- Fixed a bug which prevented users from assigning remotes to repositories in advance.
  `#262 <https://github.com/pulp/pulp_ostree/issues/262>`_


----


2.0.0 (2023-03-30)
==================

Features
--------

- Added support for third-party storage backends (i.e., S3, Azure).
  `#172 <https://github.com/pulp/pulp_ostree/issues/172>`_
- Added support for static deltas. The static deltas are automatically computed for synced and
  imported repositories. This behaviour is enabled by default. Set ``compute_delta`` to ``False``
  in a corresponding repository if there is no need to compute the static deltas between the last
  two commits.
  `#230 <https://github.com/pulp/pulp_ostree/issues/230>`_


----


2.0.0a6 (2022-06-24)
====================

Features
--------

- Added support for filtering refs during synchronization. Users can now use the flags
  ``include_refs`` or ``exclude_refs`` to include or exclude refs from a remote repository.
  `#163 <https://github.com/pulp/pulp_ostree/issues/163>`_
- The old endpoint for importing a whole OSTree repository, including refs, was renamed to
  ``import_all``. The endpoint ``import_commits`` shall be now used to import commits to an existing
  ref.
  `#170 <https://github.com/pulp/pulp_ostree/issues/170>`_


Improved Documentation
----------------------

- Added a new paragraph about filtering remote content by refs.
  `#179 <https://github.com/pulp/pulp_ostree/issues/179>`_


----


2.0.0a5 (2022-02-12)
====================

No significant changes.


----


2.0.0a4 (2022-01-12)
====================

No significant changes.


----


2.0.0a3 (2022-01-11)
====================

Features
--------

- The reference to a parent commit is now retrieved from a child commit automatically.
  `#140 <https://github.com/pulp/pulp_ostree/issues/140>`_


Bugfixes
--------

- Fixed content paths for published distributions.
  `#143 <https://github.com/pulp/pulp_ostree/issues/143>`_


----


2.0.0a2 (2021-10-25)
====================

Features
--------

- Added support for modifying repository content via the Pulp API.
  `#8929 <https://pulp.plan.io/issues/8929>`_
- Added support for filtering refs and commits by names and checksums, respectively.
  `#9493 <https://pulp.plan.io/issues/9493>`_


Bugfixes
--------

- Fixed a bug that disallowed users from publishing the same content in different repositories.
  `#9431 <https://pulp.plan.io/issues/9431>`_
- Fixed an issue that disallowed users from saving imported content.
  `#9490 <https://pulp.plan.io/issues/9490>`_


----


2.0.0a1 (2021-09-08)
====================

Features
--------

- Added support for uploading and publishing OSTree commits.
  `#8918 <https://pulp.plan.io/issues/8918>`_
- Added support for adding new commits to an existing repository.
  `#8919 <https://pulp.plan.io/issues/8919>`_
- Added support for syncing from remote OSTree repositories.
  `#8921 <https://pulp.plan.io/issues/8921>`_
- Verified support for deleting repository versions.
  `#8922 <https://pulp.plan.io/issues/8922>`_


