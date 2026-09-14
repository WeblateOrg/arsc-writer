# Copyright © Michal Čihař <michal@weblate.org>
#
# SPDX-License-Identifier: MIT

"""ARSC writer tests, including optional comparisons against Android AAPT2."""

# AAPT2 is explicitly supplied by the developer or CI, never resource input.

from __future__ import annotations

import os
import struct
import subprocess  # ruff: ignore[suspicious-subprocess-import]
import tempfile
import zipfile
from pathlib import Path

import pytest

from arsc_writer.writer import (
    ResourceTable,
    Text,
    android_text,
    generate,
    locale_config,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (" a <b> b </b> ", Text(" a  b  ", (("b", 3, 5),))),
        ("  a   <b>  b   </b>   c  ", Text(" a  b  c ", (("b", 3, 5),))),
        (" a\t\n b ", Text("a b")),
        ("\xa0a\u202fb\u2003", Text("\xa0a\u202fb\u2003")),
        (' <xliff:g id="x"> a </xliff:g> b ', Text(" a b")),
        ("\\u0020a\\u0020", Text(" a ")),
    ],
)
def test_whitespace(raw: str, expected: Text) -> None:
    """Whitespace."""
    assert android_text(raw, markup=True) == expected


@pytest.mark.skipif(
    not os.environ.get("AAPT2"), reason="Set AAPT2 for Android compiler comparisons"
)
@pytest.mark.parametrize(
    "raw",
    [
        " a <b> b </b> ",
        "  a   <b>  b   </b>   c  ",
        " a\t\n b ",
        "\xa0a\u202fb\u2003",
        "\\u0020a\\u0020",
        ' " a  b " ',
        ' <xliff:g id="x"> a </xliff:g> b ',
        ' a <b> <xliff:g id="x"> b </xliff:g> </b> c ',
        " <b> a <i> b </i> c </b> ",
        " <b>a </b><i> b</i> ",
        " 😀 <b> b </b> ",
        " a\\n <b> b\\t </b> ",
    ],
)
def test_aapt2_whitespace(raw: str) -> None:
    """Aapt2 whitespace."""
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        values = root / "res" / "values-fr"
        values.mkdir(parents=True)
        manifest = root / "AndroidManifest.xml"
        manifest.write_text(
            '<manifest package="org.weblate.sample"/>', encoding="utf-8"
        )

        def run(*args: str) -> str:
            """
            Run AAPT2.

            Returns:
                Captured compiler output.

            """
            return subprocess.run(
                [os.environ["AAPT2"], *args], check=True, capture_output=True, text=True
            ).stdout

        (values / "strings.xml").write_text(
            f'<resources xmlns:xliff="urn:oasis:names:tc:xliff:document:1.2"><string name="sample">{raw}</string><plurals name="count"><item quantity="other">{raw}</item></plurals></resources>',
            encoding="utf-8",
        )
        compiled = root / "compiled.zip"
        apk = root / "compiled.apk"
        run("compile", "--dir", str(root / "res"), "-o", str(compiled))
        run(
            "link",
            "--no-resource-removal",
            "--manifest",
            str(manifest),
            "-o",
            str(apk),
            str(compiled),
        )
        expected = run("dump", "resources", str(apk))
        with zipfile.ZipFile(apk) as archive:
            binary_manifest = archive.read("AndroidManifest.xml")
        with zipfile.ZipFile(apk, "w") as archive:
            archive.writestr("AndroidManifest.xml", binary_manifest)
            text = android_text(raw, markup=True)
            archive.writestr(
                "resources.arsc",
                generate(
                    "org.weblate.sample",
                    "fr",
                    {
                        0x7F010000: ("count", {"other": text}),
                        0x7F020000: ("sample", text),
                    },
                ),
            )
        actual = run("dump", "resources", str(apk))
        assert [
            line.strip()
            for line in actual.splitlines()
            if line.lstrip().startswith(("(fr)", "other="))
        ] == [
            line.strip()
            for line in expected.splitlines()
            if line.lstrip().startswith(("(fr)", "other="))
        ]


def test_unicode_spans() -> None:
    """Unicode spans."""
    text = android_text("Hello <b>😀<i>!</i></b>", markup=True)
    assert text.value == "Hello 😀!"
    assert text.spans == (("b", 6, 8), ("i", 8, 8))


def test_many_surrogate_spans() -> None:
    """Many surrogate spans."""
    text = android_text("<b>\\ud83d\\ude00<i>!</i></b> " * 2000, markup=True)
    assert text.value == "😀! " * 2000
    assert text.spans == tuple(
        span
        for index in range(2000)
        for span in (
            ("b", 4 * index, 4 * index + 2),
            ("i", 4 * index + 2, 4 * index + 2),
        )
    )


def test_literal_markup() -> None:
    """Literal markup."""
    assert android_text("<b>literal</b>") == Text("<b>literal</b>")


def test_nested_span_order() -> None:
    """Nested span order."""
    text = android_text(
        '<font color="red"><font color="blue">word</font></font>', markup=True
    )
    assert text.spans == (("font;color=red", 0, 3), ("font;color=blue", 0, 3))


def test_escaping() -> None:
    """Escaping."""
    assert android_text('"  a  b "\\n\\u00e9') == Text("  a  b \né")
    assert android_text(" a   b ") == Text("a b")


def test_invalid_markup() -> None:
    """Invalid markup."""
    with pytest.raises(ValueError, match="Unsupported Android span"):
        android_text("<unknown>value</unknown>", markup=True)


def test_locale() -> None:
    """Locale."""
    config = locale_config("b+sr+Latn+RS")
    assert config[8:12] == b"srRS"
    assert config[36:40] == b"Latn"
    assert locale_config("pt-rBR")[8:12] == b"ptBR"


def test_container_lengths_and_determinism() -> None:
    """Container lengths and determinism."""
    resources: ResourceTable = {
        0x7F090003: ("welcome", Text("Hello")),
        0x7F080012: ("count", {"one": Text("One"), "other": Text("Many")}),
    }
    data = generate("org.weblate.sample", "cs", resources)
    assert struct.unpack_from("<HHII", data) == (2, 12, len(data), 1)
    assert data == generate("org.weblate.sample", "cs", resources)
    offset = 12
    while offset < len(data):
        _, header_size, size = struct.unpack_from("<HHI", data, offset)
        assert size >= header_size
        assert size % 4 == 0
        offset += size
    assert offset == len(data)


@pytest.mark.skipif(
    not os.environ.get("AAPT2"), reason="Set AAPT2 for Android compiler comparisons"
)
def test_android_parser() -> None:
    """Android parser."""
    resources: ResourceTable = {
        0x7F090003: ("welcome", android_text("Hello <b>world</b>", markup=True)),
        0x7F080012: ("count", {"one": Text("One"), "other": Text("Many")}),
    }
    with tempfile.TemporaryDirectory() as directory:
        apk = Path(directory) / "resources.apk"
        manifest = Path(directory) / "AndroidManifest.xml"
        manifest.write_text(
            '<manifest package="org.weblate.sample"/>', encoding="utf-8"
        )
        subprocess.run(
            [os.environ["AAPT2"], "link", "--manifest", str(manifest), "-o", str(apk)],
            check=True,
            capture_output=True,
        )
        with zipfile.ZipFile(apk) as archive:
            manifest_bytes = archive.read("AndroidManifest.xml")
        with zipfile.ZipFile(apk, "w") as archive:
            archive.writestr("AndroidManifest.xml", manifest_bytes)
            archive.writestr(
                "resources.arsc", generate("org.weblate.sample", "fr", resources)
            )
        result = subprocess.run(
            [os.environ["AAPT2"], "dump", "resources", str(apk)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert "0x7f090003" in result.stdout
        assert "0x7f080012" in result.stdout
        assert "welcome" in result.stdout
        assert "Many" in result.stdout


@pytest.mark.parametrize("value", ["trailing\\", r"\u123", r"\uXXXX", '"open'])
def test_invalid_escaping(value: str) -> None:
    """Reject malformed Android escapes and quotes."""
    with pytest.raises(ValueError, match=r"escape|quote"):
        android_text(value)


@pytest.mark.parametrize("locale", ["", "EN", "english", "en-invalid!"])
def test_invalid_locale(locale: str) -> None:
    """Reject unsupported language and qualifier syntax."""
    with pytest.raises(ValueError, match="Android"):
        locale_config(locale)


@pytest.mark.parametrize(
    ("resources", "message"),
    [
        ({}, "No translated resources"),
        ({0x7F010000: ("a", Text("a")), 0x80010000: ("b", Text("b"))}, "one package"),
        ({0x7F000000: ("a", Text("a"))}, "Invalid resource type"),
        (
            {0x7F010000: ("a", Text("a")), 0x7F010001: ("b", {"other": Text("b")})},
            "distinct resource types",
        ),
        ({0x7F010000: ("a", {"one": Text("a")})}, "Invalid plural quantities"),
        (
            {0x7F010000: ("a", {"other": Text("a"), "unknown": Text("b")})},
            "Invalid plural quantities",
        ),
    ],
)
def test_invalid_resources(resources: ResourceTable, message: str) -> None:
    """Reject tables that cannot be represented by this writer."""
    with pytest.raises(ValueError, match=message):
        generate("org.weblate.sample", "en", resources)


def test_package_name_limit() -> None:
    """Reject package names longer than the resource header allows."""
    with pytest.raises(ValueError, match="package name is too long"):
        generate("a" * 128, "en", {0x7F010000: ("a", Text("a"))})
