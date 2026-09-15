.. Copyright © Michal Čihař
..
.. SPDX-License-Identifier: MIT

arsc-writer
===========

arsc-writer is a pure-Python library for generating Android resource tables
(ARSC) with strings, plurals, and styled text. It requires Python 3.12 or newer
and uses lxml for XML styled-text parsing. The API is alpha.

The writer does not require an Android toolchain. You supply resource IDs
matching the consuming application's compiled resources; the library produces
ARSC bytes. It does not allocate IDs, generate APKs, or support other Android
resource types.

Installation
------------

Install the package into your Python environment:

.. code-block:: console

    python -m pip install arsc-writer

For development and documentation build instructions, see the
`repository README <https://github.com/WeblateOrg/arsc-writer#development>`_.

Quick start
-----------

The following example writes French strings and plurals to an ARSC file:

.. code-block:: python

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

See the :doc:`api` for resource constraints, text normalization, and supported
locale formats.

.. toctree::
   :maxdepth: 2

   api
   changes

* :ref:`genindex`
* :ref:`search`
