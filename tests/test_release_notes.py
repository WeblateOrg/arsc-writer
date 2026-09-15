# Copyright © Michal Čihař
#
# SPDX-License-Identifier: MIT

"""Tests for the release changelog tooling."""

from __future__ import annotations

import runpy
import shutil
import subprocess  # ruff: ignore[suspicious-subprocess-import]
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

SCRIPT = Path(__file__).resolve().parents[1] / "ci" / "release_notes.py"
CHANGELOG = """Changelog
=========

Unreleased
----------

* Future changes.

1.2.0
-----

* Support **bold**, *emphasis*, and ``code``.
* See `documentation <https://example.com/>`_.

1.1.0
-----

* Older changes.
"""


@pytest.fixture
def extract_release() -> Callable[[str, str], str]:
    """
    Load the standalone CI helper.

    Returns:
        The extraction function, without modifying the package import path.

    """
    return cast(
        "Callable[[str, str], str]", runpy.run_path(str(SCRIPT))["extract_release"]
    )


@pytest.mark.parametrize("tag", ["1.2.0", "v1.2.0"])
def test_extract_release(extract_release: Callable[[str, str], str], tag: str) -> None:
    """Select only the requested release, preserving its reStructuredText."""
    assert extract_release(CHANGELOG, tag) == (
        "* Support **bold**, *emphasis*, and ``code``.\n"
        "* See `documentation <https://example.com/>`_.\n"
    )


def test_last_release(extract_release: Callable[[str, str], str]) -> None:
    """The final section extends to the end of the changelog."""
    assert extract_release(CHANGELOG, "1.1.0") == "* Older changes.\n"


@pytest.mark.parametrize(
    ("changelog", "tag", "message"),
    [
        (CHANGELOG, "1.0.0", "exactly one"),
        (CHANGELOG, "Unreleased", "exactly one"),
        (CHANGELOG + "\n1.2.0\n-----\n\nDuplicate.\n", "1.2.0", "exactly one"),
        ("1.2.0\n-----\n\n", "1.2.0", "empty"),
        ("1.2.0\n-----\n\n1.1.0\n-----\nOlder.\n", "1.2.0", "empty"),
    ],
)
def test_invalid_release(
    extract_release: Callable[[str, str], str],
    changelog: str,
    tag: str,
    message: str,
) -> None:
    """Invalid sections fail rather than selecting unrelated changes."""
    with pytest.raises(ValueError, match=message):
        extract_release(changelog, tag)


@pytest.mark.skipif(shutil.which("pandoc") is None, reason="Pandoc is not installed")
@pytest.mark.parametrize("body", [CHANGELOG, "1.2.0\n-----\n\n.. Only a comment.\n"])
def test_convert_release(tmp_path: Path, body: str) -> None:
    """Convert real RST formatting and reject sections with no rendered content."""
    changelog = tmp_path / "changes.rst"
    output = tmp_path / "notes.md"
    changelog.write_text(body, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "v1.2.0", str(changelog), str(output)],
        capture_output=True,
        text=True,
        check=False,
    )
    if body != CHANGELOG:
        assert result.returncode != 0
        assert "empty release notes" in result.stderr
        assert not output.exists()
        return
    assert result.returncode == 0, result.stderr
    notes = output.read_text(encoding="utf-8")
    assert "**bold**" in notes
    assert "*emphasis*" in notes
    assert "`code`" in notes
    assert "[documentation](https://example.com/)" in notes
    assert "Future changes" not in notes
    assert "Older changes" not in notes
