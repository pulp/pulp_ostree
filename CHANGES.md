# Changelog

[//]: # (You should *NOT* be adding new change log entries to this file, this)
[//]: # (file is managed by towncrier. You *may* edit previous change logs to)
[//]: # (fix problems like typo corrections or such.)
[//]: # (To add a new change log entry, please see the contributing docs.)
[//]: # (WARNING: Don't drop the towncrier directive!)

[//]: # (towncrier release notes start)

## 2.4.3 (2024-07-09) {: #2.4.3 }


No significant changes.

---

## 2.4.2 (2024-07-09) {: #2.4.2 }


No significant changes.

---

## 2.4.1 (2024-06-26) {: #2.4.1 }


#### Bugfixes {: #2.4.1-bugfix }

- Fixed an issue when trying to use import-all as a non-admin user.
  [#373](https://github.com/pulp/pulp_ostree/issues/373)

---

## 2.4.0 (2024-06-20) {: #2.4.0 }


#### Bugfixes {: #2.4.0-bugfix }

- Fixed an issue with `rpm-ostree` having multiples commits in the same tar file and breaking
  Pulp `import-commits`.
  [#366](https://github.com/pulp/pulp_ostree/issues/366)

#### Improved Documentation {: #2.4.0-doc }

- Migrated the whole documentation to staging. The documentation should be now consumed from the
  unified docs site.
  [#347](https://github.com/pulp/pulp_ostree/issues/347)

#### Misc {: #2.4.0-misc }

- 

---

## 2.3.1 (2024-06-18) {: #2.3.1 }


#### Bugfixes {: #2.3.1-bugfix }

- Fixed an issue with `rpm-ostree` having multiples commits in the same tar file and breaking
  Pulp `import-commits`.
  [#366](https://github.com/pulp/pulp_ostree/issues/366)

---

## 2.3.0 (2024-02-19) {: #2.3.0 }

### Features

-   Added support for domains.
    [#321](https://github.com/pulp/pulp_ostree/issues/321)
-   Added role-based access control.
    [#331](https://github.com/pulp/pulp_ostree/issues/331)

### Bugfixes

-   Improved the performance of subsequent imports.
    [#289](https://github.com/pulp/pulp_ostree/issues/289)

### Misc

-   [#324](https://github.com/pulp/pulp_ostree/issues/324), [#325](https://github.com/pulp/pulp_ostree/issues/325), [#326](https://github.com/pulp/pulp_ostree/issues/326), [#327](https://github.com/pulp/pulp_ostree/issues/327)

---

## 2.2.1 (2023-11-16) {: #2.2.1 }

### Bugfixes

-   Improved the performance of subsequent imports.
    [#289](https://github.com/pulp/pulp_ostree/issues/289)

---

## 2.2.0 (2023-11-03) {: #2.2.0 }

### Features

-   Made plugin compatible with pulpcore 3.40.1+.
    [#303](https://github.com/pulp/pulp_ostree/issues/303)

### Bugfixes

-   Started re-generating summary files and publishing them during the import.
    [#269](https://github.com/pulp/pulp_ostree/issues/269)
-   Fixed a bug that led to ignoring already imported refs in a repository when generating a summary.
    [#277](https://github.com/pulp/pulp_ostree/issues/277)
-   Made the import facility to accept tarballs with already imported parent commits.
    [#279](https://github.com/pulp/pulp_ostree/issues/279)
-   Fixed the procedure of regenerating summaries by using the relevant refs only.
    [#288](https://github.com/pulp/pulp_ostree/issues/288)

---

## 2.1.3 (2023-09-18) {: #2.1.3 }

### Bugfixes

-   Fixed the procedure of regenerating summaries by using the relevant refs only.
    [#288](https://github.com/pulp/pulp_ostree/issues/288)

---

## 2.1.2 (2023-09-11) {: #2.1.2 }

### Bugfixes

-   Fixed a bug that led to ignoring already imported refs in a repository when generating a summary.
    [#277](https://github.com/pulp/pulp_ostree/issues/277)
-   Made the import facility to accept tarballs with already imported parent commits.
    [#279](https://github.com/pulp/pulp_ostree/issues/279)

---

## 2.1.1 (2023-07-12) {: #2.1.1 }

### Bugfixes

-   Started re-generating summary files and publishing them during the import.
    [#269](https://github.com/pulp/pulp_ostree/issues/269)

---

## 2.1.0 (2023-05-28) {: #2.1.0 }

### Features

-   Made the plugin compatible with Django 4.2 and pulpcore 3.25.
    [#258](https://github.com/pulp/pulp_ostree/issues/258)

### Bugfixes

-   Fixed the path resolution when a user specifies absolute paths when importing repositories.
    [#226](https://github.com/pulp/pulp_ostree/issues/226)
-   Fixed a bug that disallowed users to pull re-synced content locally.
    [#257](https://github.com/pulp/pulp_ostree/issues/257)
-   Fixed a bug which prevented users from assigning remotes to repositories in advance.
    [#262](https://github.com/pulp/pulp_ostree/issues/262)

---

## 2.0.0 (2023-03-30) {: #2.0.0 }

### Features

-   Added support for third-party storage backends (i.e., S3, Azure).
    [#172](https://github.com/pulp/pulp_ostree/issues/172)
-   Added support for static deltas. The static deltas are automatically computed for synced and
    imported repositories. This behaviour is enabled by default. Set `compute_delta` to `False`
    in a corresponding repository if there is no need to compute the static deltas between the last
    two commits.
    [#230](https://github.com/pulp/pulp_ostree/issues/230)

---

## 2.0.0a6 (2022-06-24)

### Features

-   Added support for filtering refs during synchronization. Users can now use the flags
    `include_refs` or `exclude_refs` to include or exclude refs from a remote repository.
    [#163](https://github.com/pulp/pulp_ostree/issues/163)
-   The old endpoint for importing a whole OSTree repository, including refs, was renamed to
    `import_all`. The endpoint `import_commits` shall be now used to import commits to an existing
    ref.
    [#170](https://github.com/pulp/pulp_ostree/issues/170)

### Improved Documentation

-   Added a new paragraph about filtering remote content by refs.
    [#179](https://github.com/pulp/pulp_ostree/issues/179)

---

## 2.0.0a5 (2022-02-12)

No significant changes.

---

## 2.0.0a4 (2022-01-12)

No significant changes.

---

## 2.0.0a3 (2022-01-11)

### Features

-   The reference to a parent commit is now retrieved from a child commit automatically.
    [#140](https://github.com/pulp/pulp_ostree/issues/140)

### Bugfixes

-   Fixed content paths for published distributions.
    [#143](https://github.com/pulp/pulp_ostree/issues/143)

---

## 2.0.0a2 (2021-10-25)

### Features

-   Added support for modifying repository content via the Pulp API.
    [#8929](https://pulp.plan.io/issues/8929)
-   Added support for filtering refs and commits by names and checksums, respectively.
    [#9493](https://pulp.plan.io/issues/9493)

### Bugfixes

-   Fixed a bug that disallowed users from publishing the same content in different repositories.
    [#9431](https://pulp.plan.io/issues/9431)
-   Fixed an issue that disallowed users from saving imported content.
    [#9490](https://pulp.plan.io/issues/9490)

---

## 2.0.0a1 (2021-09-08)

### Features

-   Added support for uploading and publishing OSTree commits.
    [#8918](https://pulp.plan.io/issues/8918)
-   Added support for adding new commits to an existing repository.
    [#8919](https://pulp.plan.io/issues/8919)
-   Added support for syncing from remote OSTree repositories.
    [#8921](https://pulp.plan.io/issues/8921)
-   Verified support for deleting repository versions.
    [#8922](https://pulp.plan.io/issues/8922)
