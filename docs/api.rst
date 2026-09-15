.. Copyright © Michal Čihař
..
.. SPDX-License-Identifier: MIT

API reference
=============

Import the public interface from :mod:`arsc_writer`. Binary-format helpers in
``arsc_writer.writer`` are internal.

.. automodule:: arsc_writer

Text
----

.. autoclass:: arsc_writer.Text
   :members: value, spans

Resource types
--------------

.. autodata:: arsc_writer.ResourceValue
   :no-value:

   A decoded string or a mapping from plural quantities to decoded strings.
   Plurals require ``other`` and also accept ``zero``, ``one``, ``two``, ``few``,
   and ``many``.

.. autodata:: arsc_writer.ResourceTable
   :no-value:

   A mapping from caller-assigned resource IDs to ``(name, value)`` pairs.
   See :func:`arsc_writer.generate` for resource ID and name constraints.

Functions
---------

.. autofunction:: arsc_writer.android_text

.. autofunction:: arsc_writer.generate
