# Copyright © Michal Čihař <michal@weblate.org>
#
# SPDX-License-Identifier: MIT

"""Generate assets for the standalone Android resource-loader tests."""

from __future__ import annotations

from pathlib import Path

from arsc_writer import ResourceTable, Text, android_text, generate


def main() -> None:
    """Write initial and replacement ARSC tables for the Android harness."""
    output = Path(__file__).resolve().parent / "build/generated/assets"
    output.mkdir(parents=True, exist_ok=True)
    package = "org.weblate.arsctest"
    resources: ResourceTable = {
        0x7F090003: ("welcome", android_text(" Bonjour <b> 😀 </b> ", markup=True)),
        0x7F080012: (
            "count",
            {
                "one": android_text("Un\u00a0objet"),
                "other": android_text(" Plusieurs <b> articles </b> ", markup=True),
            },
        ),
    }
    (output / "fr.arsc").write_bytes(generate(resources, package=package, locale="fr"))
    (output / "fr-updated.arsc").write_bytes(
        generate({0x7F090003: ("welcome", Text("Salut"))}, package=package, locale="fr")
    )
    for filename in ("fr.arsc", "fr-updated.arsc"):
        (output / f"{filename}.license").write_text(
            "SPDX-FileCopyrightText: Michal Čihař <michal@weblate.org>\nSPDX-License-Identifier: MIT\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
