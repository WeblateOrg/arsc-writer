<!--
Copyright © Michal Čihař

SPDX-License-Identifier: MIT
-->

# arsc-writer

A pure-Python library for generating Android resource tables (ARSC) with support
for strings, plurals, and styled text.

This project is currently scaffolding only. Resource table generation and a
public API have not been implemented yet. Python 3.11 or newer is required.

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
Tests live in `tests/` and use pytest's `importlib` import mode. The placeholder
test checks package installation and the bundled `py.typed` marker.

Commit `uv.lock` to keep development and CI dependencies reproducible. After
changing dependency requirements, run `uv lock` and include the updated lockfile
in the change. Ruff is supplied by the pre-commit hook environment.

CI tests the built wheel on supported Python versions and operating systems,
and installs the source distribution separately on Python 3.11 and 3.14.
These checks run outside the checkout, without an editable installation or
`PYTHONPATH` override.

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

The distribution workflow builds and validates packages on pushes and pull
requests. `uv build` builds the wheel from the source distribution. Publishing
waits for all distribution tests to pass. Tags must match the version in
`pyproject.toml`, optionally prefixed with `v`.

Tags in `WeblateOrg/arsc-writer` also publish to PyPI and create GitHub
releases with generated release notes. Before tagging a release, update the
version in `pyproject.toml` and the changelog, and configure a PyPI trusted
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
