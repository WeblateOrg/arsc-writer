# Copyright © Michal Čihař
#
# SPDX-License-Identifier: MIT

"""Placeholder checks for the installed package until the writer is implemented."""

from importlib.metadata import distribution
from importlib.resources import files

import arsc_writer


def test_package_installation() -> None:
    """The package can be imported and ships its typing marker."""
    assert arsc_writer.__doc__
    assert distribution("arsc-writer").metadata["Name"] == "arsc-writer"
    assert files(arsc_writer).joinpath("py.typed").is_file()
