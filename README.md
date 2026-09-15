<!--
Copyright © Michal Čihař

SPDX-License-Identifier: MIT
-->

<a href="https://weblate.org/"><img alt="Weblate" src="https://s.weblate.org/cdn/Logo-Darktext-borders.png" height="80px" /></a>

**Weblate is libre software web-based continuous localization system,
used by over 2500 libre projects and companies in more than 165 countries.**

# arsc-writer

A pure-Python library for generating Android resource tables (ARSC) with support
for strings, plurals, and styled text.

Python 3.12 or newer is required. The writer generates resource tables without
an Android toolchain; XML styled-text parsing uses `lxml`. The API is alpha.

## Usage

```python
from pathlib import Path

from arsc_writer import ResourceTable, Text, android_text, generate

resources: ResourceTable = {
    0x7F010000: ("welcome", android_text("Bonjour <b>monde</b>", markup=True)),
    0x7F020000: (
        "count",
        {"one": Text("Un objet"), "other": Text("Plusieurs objets")},
    ),
}
Path("fr.arsc").write_bytes(generate(resources, package="org.example.app", locale="fr"))
```

See the [user guide and API reference](https://arsc-writer.readthedocs.io/)
for resource IDs, text normalization, styles, locales, and validation.
The documentation sources are in [docs/](docs/).

## Development

Install the package and development tools from a checkout:

```sh
uv sync --locked --dev
uv run --locked python -c "import arsc_writer"
uv run --locked prek run --all-files
uv run --locked mypy --show-column-numbers
uv run --locked ty check --output-format=github
uv run --locked pytest
```

The package lives in `src/arsc_writer/`; installation is required before imports.
Tests live in `tests/` and use pytest's `importlib` import mode. They cover text
normalization, styles, locales, binary tables, validation, and package metadata.

Commit `uv.lock` to keep development and CI dependencies reproducible. After
changing dependency requirements, run `uv lock` and include the updated lockfile
in the change. Ruff is supplied by the pre-commit hook environment.

CI tests the built wheel and source distribution using the
[Python test matrix](.github/workflows/test.yml).
These checks run outside the checkout, without an editable installation or
`PYTHONPATH` override.

### Documentation

Build the English HTML documentation locally:

```sh
uv run --locked --group docs sphinx-build -n -W --keep-going -b html docs docs/_build/html
```

Open `docs/_build/html/index.html` to read the result. Sphinx imports the installed
package to build the API reference. The documentation dependencies are included
in the development group. Read the Docs and CI use the same locked dependencies.

## Android verification

The Python suite runs without an Android SDK, skipping compiler comparisons
unless `AAPT2` points to an executable:

```sh
AAPT2="/path/to/android-sdk/build-tools/<version>/aapt2" uv run --locked pytest
```

The instrumentation harness in `ci/android-arsc` verifies resource overrides,
plurals, styled Unicode, fallback, and provider replacement with Android's
`ResourcesLoader`. It requires Java, Gradle, the Android SDK platform and
build-tools, and a running emulator. Use the tool versions and emulator matrix
configured in the [Android workflow](.github/workflows/android.yml); the
[Gradle build](ci/android-arsc/build.gradle) defines the Android plugin and SDK
requirements:

```sh
uv run --locked python ci/android-arsc/generate-fixtures.py
gradle -p ci/android-arsc --no-daemon assembleDebug assembleDebugAndroidTest
gradle -p ci/android-arsc --no-daemon connectedDebugAndroidTest
```

CI runs the configured emulator matrix and AAPT2 comparisons against the built wheel,
then uploads instrumentation reports. The Android harness is repository-only;
Python tests are included in the source distribution.

## Distributions and releases

Build and validate the wheel and source distribution:

```sh
uv build --no-sources
uv run --locked twine check dist/*
uv run --locked pydistcheck --inspect dist/*
uv run --locked pyroma dist/*.tar.gz
uv run --locked check-wheel-contents dist/*.whl
uv run --locked check-manifest -v
```

The distribution workflow builds and validates packages on pushes to `main`, release tags, and pull
requests. `uv build` builds the wheel from the source distribution. Publishing
waits for all Python distribution tests and Android verification to pass. Tags must match the version in
`pyproject.toml`, optionally prefixed with `v`.

Tags in `WeblateOrg/arsc-writer` also publish to PyPI and create GitHub
releases with notes from the matching [changelog](docs/changes.rst) section.
Use the bare package version as the section heading, with a dashed underline,
and include a nonempty description of the changes. Missing, duplicate, or empty
release sections block publishing. Before tagging a release, update the
version in `pyproject.toml` and the [changelog](docs/changes.rst), and configure a PyPI trusted
publisher for owner `WeblateOrg`, repository `arsc-writer`, and workflow
`setup.yml` without an environment name.

## Shared project files

[WeblateOrg/meta](https://github.com/WeblateOrg/meta) maintains shared CI,
security guidance, funding links, issue and pull request templates, and editor
settings. Update canonical shared files there so subsequent synchronization
preserves the changes. Package-specific workflows, metadata, and this README
are maintained here. The repository is already registered for synchronization.

Report vulnerabilities according to [the security policy](SECURITY.md).
The package is licensed under the [MIT license](LICENSE); shared files retain
their own SPDX license declarations.
