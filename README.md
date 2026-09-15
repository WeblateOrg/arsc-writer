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

See the [documentation](https://arsc-writer.readthedocs.io/) for installation,
usage, and the API reference, and the
[developer guide](https://arsc-writer.readthedocs.io/en/latest/development.html)
for contributing, testing, and releases. Documentation sources are in [docs/](docs/).
