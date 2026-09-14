<!--
Copyright © Michal Čihař

SPDX-License-Identifier: MIT
-->

# Changelog

## Unreleased

- Integrate the ARSC writer, Python tests, and Android SDK verification from Weblate
  commit `0ee7f3bb93f8e7f8fe25c161c7b08557b8580278`, relicensed to MIT by Michal Čihař.
- Require Python 3.12+, add lxml, and expose the typed writer API.
- Gate releases on Android API 30/36 verification and avoid duplicate PR builds.
