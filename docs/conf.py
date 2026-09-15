# Copyright © Michal Čihař
#
# SPDX-License-Identifier: MIT

"""Sphinx configuration for the arsc-writer user documentation."""

from __future__ import annotations

import os
from importlib.metadata import version as package_version
from typing import TYPE_CHECKING, TypeAliasType

from sphinx.util.typing import stringify_annotation

if TYPE_CHECKING:
    from sphinx.application import Sphinx

project = "arsc-writer"
author = "Michal Čihař"
project_copyright = "Michal Čihař"
release = package_version("arsc-writer")

extensions = ["sphinx.ext.autodoc", "sphinx.ext.napoleon"]
exclude_patterns = ["_build"]
language = "en"
nitpicky = True
# lxml does not publish a Sphinx inventory for its exception classes.
nitpick_ignore = [("py:exc", "lxml.etree.XMLSyntaxError")]
autodoc_typehints = "description"
autodoc_typehints_format = "short"
autodoc_type_aliases = {
    "ResourceTable": "arsc_writer.ResourceTable",
    "ResourceValue": "arsc_writer.ResourceValue",
}
html_theme = "furo"
html_baseurl = os.environ.get("READTHEDOCS_CANONICAL_URL", "")
html_theme_options = {
    "source_repository": "https://github.com/WeblateOrg/arsc-writer/",
    "source_branch": "main",
    "source_directory": "docs/",
}


# The positional signature is defined by Sphinx's autodoc event.
def document_type_alias(
    _app: Sphinx,
    _what: str,
    _name: str,
    obj: object,
    _options: object,
    lines: list[str],
) -> None:
    """Render Python 3.12 aliases instead of the generic TypeAliasType docstring."""
    if isinstance(obj, TypeAliasType):
        definition = stringify_annotation(obj.__value__).replace(
            "arsc_writer.writer.", "arsc_writer."
        )
        lines[:] = [f"Alias of ``{definition}``.", ""]


def setup(app: Sphinx) -> None:
    """Add type-alias rendering for Sphinx 8.2 autodoc."""
    app.connect("autodoc-process-docstring", document_type_alias)
