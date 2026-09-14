# Copyright © Michal Čihař
#
# SPDX-License-Identifier: MIT

"""Checks for the installed package and its public API."""

from importlib.metadata import distribution
from importlib.resources import files

import arsc_writer


def test_package_installation() -> None:
    """The package can be imported and ships its typing marker."""
    assert arsc_writer.__doc__
    assert distribution("arsc-writer").metadata["Name"] == "arsc-writer"
    assert files(arsc_writer).joinpath("py.typed").is_file()


def test_public_api() -> None:
    """Generate an ARSC table through the package-root API."""
    resources: arsc_writer.ResourceTable = {
        0x7F010000: (
            "greeting",
            arsc_writer.android_text("Hello <b>world</b>", markup=True),
        ),
    }
    value: arsc_writer.ResourceValue = arsc_writer.Text("Hello")
    assert isinstance(value, arsc_writer.Text)
    assert arsc_writer.generate("org.example.app", "en", resources).startswith(
        b"\x02\x00\x0c\x00"
    )
