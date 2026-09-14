<!--
Copyright © Michal Čihař

SPDX-License-Identifier: MIT
-->

# Repository Guidelines

## Project structure

This Python 3.12+ library generates Android resource tables (ARSC) for strings,
plurals, and styled text. It uses lxml for XML text fragments, without requiring
an Android toolchain at runtime.

- `src/arsc_writer/`: typed package; `writer.py` implements the writer and
  `__init__.py` explicitly re-exports the public API.
- `ci/android-arsc/`: standalone Android instrumentation harness.
- `tests/`: pytest tests using `importlib` import mode.
- `uv.lock`: committed development and CI dependency lockfile.
- `pyproject.toml`: package metadata, dependencies, and tool configuration.
- `.github/`: CI workflows and contribution templates.
- `README.md`: development and distribution instructions.
- `CHANGES.md`: release history.

Tests cover the writer and package metadata. Set `AAPT2` to run compiler
comparisons; Android CI also runs instrumentation on API 30 and 36.

## Development commands

- `uv sync --locked --dev`: install the package and development tools.
- `uv run --locked python -c "import arsc_writer"`: verify installation.
- `uv run --locked prek run --all-files`: run configured linting and formatting hooks;
  some hooks modify files.
- `uv run --locked mypy --show-column-numbers`: check Python types.
- `uv run --locked ty check --output-format=github`: run the additional type checker.
- `uv build --no-sources`: create wheel and source distributions in `dist/`.
- `uv run --locked pytest`: run the test suite.

Prefer `uv run --locked` after syncing. Update `uv.lock` with `uv lock` when
dependencies change; include it in the same change. Run Ruff through `prek`; Ruff is supplied by
the hook environment rather than the development dependency group.

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
threshold. CI installs the built wheel and source distribution into environments
containing locked runtime dependencies and test tools. Run tests against the installed package;
do not add `src/` to `PYTHONPATH`. Artifact tests run outside the checkout.

Mypy uses strict checking and targets Python 3.12. Keep `py.typed` in the wheel.
Distribution validators are pinned in the `dist` dependency group. Releases wait
for Python artifact tests and Android verification, and reject tags that differ from the package version (an
optional `v` prefix is accepted).

## Android verification

- `AAPT2="$ANDROID_HOME/build-tools/35.0.0/aapt2" uv run --locked pytest` runs compiler comparisons.
- `uv run --locked python ci/android-arsc/generate-fixtures.py` creates test assets.
- `gradle -p ci/android-arsc --no-daemon connectedDebugAndroidTest` runs instrumentation with a connected emulator.

The harness uses Java 17, Gradle 8.7, Android Gradle Plugin 8.6.1, SDK/build-tools
35, and API 30/36 emulators. Keep generated assets and Gradle output untracked.
Preserve AAPT2 and device behavior when changing normalization or binary encoding.

## Commits and pull requests

Use Conventional Commits, following Weblate: `fix(writer): handle empty strings`. Explain motivation
and include `Fixes #123` when applicable.

Keep pull requests focused. Describe changes and addressed issues, report
validation, and document new behavior in `README.md` and relevant release
changes in `CHANGES.md`.

## Shared files and security

Update files marked as maintained by `WeblateOrg/meta` upstream so
synchronization preserves changes. Follow `SECURITY.md` for private
vulnerability reporting.
