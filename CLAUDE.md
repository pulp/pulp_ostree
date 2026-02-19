# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`pulp_ostree` is a [Pulp](https://pulpproject.org/) plugin that enables hosting and managing OSTree repositories. It integrates with `pulpcore` (the Pulp framework) using Django and Django REST Framework.

## Development Commands

### Linting
```bash
# Format check
black --check --diff .

# Auto-format
black .

# Lint
flake8

# Lint YAML workflow files
yamllint -s -d '{extends: relaxed, rules: {line-length: disable}}' .github/workflows
```

Install lint dependencies: `pip install -r lint_requirements.txt`

### Unit Tests
```bash
# Run unit tests
pytest pulp_ostree/tests/unit/

# Run a single test file
pytest pulp_ostree/tests/unit/test_models.py

# Run a single test
pytest pulp_ostree/tests/unit/test_models.py::TestNothing::test_nothing_at_all
```

Install test dependencies: `pip install -r unittest_requirements.txt`

### Functional Tests
Functional tests (`pulp_ostree/tests/functional/`) require a running Pulp instance and use `pulp-smash`. They are typically run in CI via Ansible/Docker.

### Changelog
Uses [towncrier](https://towncrier.readthedocs.io/). Add changelog fragments to `CHANGES/` with type subdirectories: `feature/`, `bugfix/`, `doc/`, `removal/`, `deprecation/`, `misc/`.

## Code Style

- Line length: **100 characters** (enforced by black and flake8)
- All imports from pulpcore must go through `pulpcore.plugin.*` — direct pulpcore internal imports are forbidden (enforced by CI check)
- Uses `gettext as _` for i18n of user-facing strings

## Architecture

### Plugin Structure

The plugin follows the standard Pulp plugin pattern:

- **`pulp_ostree/app/models.py`** — Django models extending pulpcore base classes
- **`pulp_ostree/app/serializers.py`** — DRF serializers
- **`pulp_ostree/app/viewsets.py`** — DRF viewsets with RBAC access policies
- **`pulp_ostree/app/tasks/`** — Async task implementations dispatched via Pulp's task queue

### Content Models

The plugin defines these content types, all extending `pulpcore.plugin.models.Content`:

| Model | TYPE | Description |
|-------|------|-------------|
| `OstreeObject` | `object` | Generic OSTree objects (dirtree, dirmeta, file) |
| `OstreeCommit` | `commit` | OSTree commits; linked to parent commit and `OstreeObject`s via M2M through `OstreeCommitObject` |
| `OstreeRef` | `refs` | Head/branch refs pointing to a commit |
| `OstreeConfig` | `config` | Repository config file |
| `OstreeSummary` | `summary` | Repository summary file |
| `OstreeContent` | *(none)* | Uncategorized content, used for static delta files |

All content models carry a `_pulp_domain` FK for multi-domain support.

### OSTree Integration

The plugin uses **PyGObject** (`gi.repository`) to bind to the native OSTree GLib library. All task files include:
```python
import gi
gi.require_version("OSTree", "1.0")
from gi.repository import Gio, GLib, OSTree
```
This requires `PyGObject` and `libostree` to be installed on the system.

### Task Pipeline (Declarative Version)

Sync and import operations use pulpcore's **Declarative Version** pipeline pattern:

- **Sync** (`tasks/synchronizing.py`): `OstreeFirstStage` → standard pulpcore stages → `OstreeAssociateContent`
- **Import all refs** (`tasks/importing.py`): `OstreeImportAllRefsFirstStage` → custom `QueryExistingArtifactsOstree` → standard stages → `OstreeAssociateContent`
- **Import child commits** (`tasks/importing.py`): `OstreeImportSingleRefFirstStage` → same pipeline
- **Modify** (`tasks/modifying.py`): Direct repository version manipulation (not a pipeline)

The shared logic for creating `DeclarativeContent` objects lives in `tasks/stages.py`:
- `DeclarativeContentCreatorMixin` — base mixin used by both sync and import first stages
- `OstreeAssociateContent` — final pipeline stage that bulk-creates parent-child commit links and commit-object associations

### RBAC

All viewsets define `DEFAULT_ACCESS_POLICY` (inline) and `LOCKED_ROLES`. The plugin uses pulpcore's RBAC framework with roles like `ostree.ostreerepository_owner`, `ostree.ostreerepository_viewer`, etc.

### Key Repository Features

- `OstreeRepository.compute_delta` — controls static delta generation during sync/import
- `OstreeRemote.depth` — controls how many parent commits to sync
- `OstreeRemote.include_refs` / `exclude_refs` — fnmatch patterns to filter refs during sync
- `OstreeRepository.finalize_new_version()` — removes duplicate content on new repository versions
