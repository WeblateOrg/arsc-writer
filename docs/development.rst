.. Copyright © Michal Čihař
..
.. SPDX-License-Identifier: MIT

Developer guide
===============

This guide covers development, testing, and releases from a repository checkout.
For usage and the public API, see the :doc:`index` and :doc:`api`.
Keep development and contributor instructions here rather than duplicating them
in the repository entry points.

Setup and project layout
------------------------

Install the package and development tools from a checkout:

.. code-block:: console

    uv sync --locked --dev
    uv run --locked python -c "import arsc_writer"
    uv run --locked prek run --all-files
    uv run --locked mypy --show-column-numbers
    uv run --locked ty check --output-format=github
    uv run --locked pytest

The package lives in ``src/arsc_writer/``; installation is required before imports.
Tests live in ``tests/`` and use pytest's ``importlib`` import mode. They cover text
normalization, styles, locales, binary tables, validation, and package metadata.

Commit ``uv.lock`` to keep development and CI dependencies reproducible. After
changing dependency requirements, run ``uv lock`` and include the updated lockfile
in the change. Ruff is supplied by the pre-commit hook environment.

Code expectations
-----------------

Follow ``.editorconfig``: four spaces for Python, two for YAML/TOML, UTF-8,
and final newlines. Use configured Ruff formatting and linting. Prefer
human-readable Ruff rule names in overrides.

Use ``snake_case`` for functions and modules, ``PascalCase`` for classes, and
``UPPER_CASE`` for constants. Prefer type hints and
``from __future__ import annotations``; use ``TYPE_CHECKING`` imports where
needed to avoid runtime import cycles.

Include the usual copyright and MIT SPDX header in new project code.
Preserve existing license declarations in shared files.

Testing guidelines
------------------

Use pytest, placing new tests in ``tests/test_*.py`` with ``test_*`` functions.
Cover new behavior and add regression tests for fixes. There is no coverage
threshold. Run tests against the installed package; do not add ``src/`` to
``PYTHONPATH``.

Keep strict typing checks enabled and include ``py.typed`` in the wheel.

CI tests the built wheel and source distribution using the
`Python test matrix <https://github.com/WeblateOrg/arsc-writer/blob/main/.github/workflows/test.yml>`_.
These checks run outside the checkout, without an editable installation or
``PYTHONPATH`` override.

Documentation
-------------

Build the English HTML documentation locally:

.. code-block:: console

    uv run --locked --group docs sphinx-build -n -W --keep-going -b html docs docs/_build/html

Open ``docs/_build/html/index.html`` to read the result. Sphinx imports the installed
package to build the API reference. The documentation dependencies are included
in the development group. Read the Docs and CI use the same locked dependencies.

Android verification
--------------------

The Python suite runs without an Android SDK, skipping compiler comparisons
unless ``AAPT2`` points to an executable:

.. code-block:: console

    AAPT2="/path/to/android-sdk/build-tools/<version>/aapt2" uv run --locked pytest

The instrumentation harness in ``ci/android-arsc`` verifies resource overrides,
plurals, styled Unicode, fallback, and provider replacement with Android's
``ResourcesLoader``. It requires Java, Gradle, the Android SDK platform and
build-tools, and a running emulator. Use the tool versions and emulator matrix
configured in the
`Android workflow <https://github.com/WeblateOrg/arsc-writer/blob/main/.github/workflows/android.yml>`_;
the `Gradle build <https://github.com/WeblateOrg/arsc-writer/blob/main/ci/android-arsc/build.gradle>`_
defines the Android plugin and SDK requirements:

.. code-block:: console

    uv run --locked python ci/android-arsc/generate-fixtures.py
    gradle -p ci/android-arsc --no-daemon assembleDebug assembleDebugAndroidTest
    gradle -p ci/android-arsc --no-daemon connectedDebugAndroidTest

CI runs the configured emulator matrix and AAPT2 comparisons against the built
wheel, then uploads instrumentation reports. The Android harness is
repository-only; Python tests are included in the source distribution.

Keep generated Android assets and Gradle output untracked. Preserve AAPT2 and
device behavior when changing normalization or binary encoding.

Commits and pull requests
-------------------------

Use Conventional Commits, following Weblate: ``fix(writer): handle empty strings``.
Explain motivation and include ``Fixes #123`` when applicable.

Keep pull requests focused. Describe changes and addressed issues, report
validation, and document new behavior in the appropriate page in ``docs/`` and
relevant release changes in the :doc:`changes`.

Distributions and releases
--------------------------

Build and validate the wheel and source distribution:

.. code-block:: console

    uv build --no-sources
    uv run --locked twine check dist/*
    uv run --locked pydistcheck --inspect dist/*
    uv run --locked pyroma dist/*.tar.gz
    uv run --locked check-wheel-contents dist/*.whl
    uv run --locked check-manifest -v

The distribution workflow builds and validates packages on pushes to ``main``,
release tags, and pull requests. ``uv build`` builds the wheel from the source
distribution. Publishing waits for all Python distribution tests and Android
verification to pass. Tags must match the version in ``pyproject.toml``,
optionally prefixed with ``v``.

Tags in ``WeblateOrg/arsc-writer`` also publish to PyPI and create GitHub
releases with notes from the matching :doc:`changes` section.
Use the bare package version as the section heading, with a dashed underline,
and include a nonempty description of the changes. Missing, duplicate, or empty
release sections block publishing. Before tagging a release, update the
version in ``pyproject.toml`` and the :doc:`changes`, and configure a PyPI trusted
publisher for owner ``WeblateOrg``, repository ``arsc-writer``, and workflow
``setup.yml`` without an environment name.

Shared project files and security
---------------------------------

`WeblateOrg/meta <https://github.com/WeblateOrg/meta>`_ maintains shared CI,
security guidance, funding links, issue and pull request templates, and editor
settings. Update canonical shared files there so subsequent synchronization
preserves the changes. Package-specific workflows, metadata, and documentation
are maintained here. The repository is already registered for synchronization.

Report vulnerabilities privately according to the
`security policy <https://github.com/WeblateOrg/arsc-writer/blob/main/SECURITY.md>`_.
The package is licensed under the
`MIT license <https://github.com/WeblateOrg/arsc-writer/blob/main/LICENSE>`_;
shared files retain their own SPDX license declarations.
