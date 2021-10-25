=========
Changelog
=========

..
    You should *NOT* be adding new change log entries to this file, this
    file is managed by towncrier. You *may* edit previous change logs to
    fix problems like typo corrections or such.

    WARNING: Don't drop the next directive!

.. towncrier release notes start

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


