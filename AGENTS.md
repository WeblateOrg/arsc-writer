<!--
Copyright © Michal Čihař

SPDX-License-Identifier: MIT
-->

# Repository Guidelines

## Project structure

See [README.md](README.md) for the public API, project layout, development
commands, [Android verification](README.md#android-verification), and
[distribution and release instructions](README.md#distributions-and-releases).
Keep setup instructions there rather than duplicating them here.

## Code expectations

Follow `.editorconfig`: four spaces for Python, two for YAML/TOML, UTF-8,
and final newlines. Use configured Ruff formatting and linting. Prefer
human-readable Ruff rule names in overrides.

Use `snake_case` for functions and modules, `PascalCase` for classes, and
`UPPER_CASE` for constants. Prefer type hints and
`from __future__ import annotations`; use `TYPE_CHECKING` imports where
needed to avoid runtime import cycles.

Include the usual copyright and MIT SPDX header in new project code.
Preserve existing license declarations in shared files.

## Testing guidelines

Use pytest, placing new tests in `tests/test_*.py` with `test_*` functions.
Cover new behavior and add regression tests for fixes. There is no coverage
threshold. Run tests against the installed package; do not add `src/` to
`PYTHONPATH`.

Keep strict typing checks enabled and include `py.typed` in the wheel.

Keep generated Android assets and Gradle output untracked. Preserve AAPT2 and
device behavior when changing normalization or binary encoding.

## Commits and pull requests

Use Conventional Commits, following Weblate: `fix(writer): handle empty strings`. Explain motivation
and include `Fixes #123` when applicable.

Keep pull requests focused. Describe changes and addressed issues, report
validation, and document new behavior in `README.md` and relevant release
changes in `docs/changes.rst`.

## Shared files and security

Update files marked as maintained by `WeblateOrg/meta` upstream so
synchronization preserves changes. Follow `SECURITY.md` for private
vulnerability reporting.
