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
    SPAN_TAGS,
    ResourceTable,
    ResourceValue,
    Text,
    android_text,
    generate,
    locale_config,
)

COMPATIBLE_TEXT_CASES = [
    ('a "" b', Text("a  b")),
    ('a "" <b>b</b>', Text("a  b", (("b", 3, 3),))),
    ("<![CDATA[]]><xliff:g> x </xliff:g>", Text("x")),
    ("<xliff:g> x </xliff:g><![CDATA[]]>", Text("x")),
    ("<![CDATA[]]><xliff:g> x </xliff:g><![CDATA[]]>", Text("x")),
    ("<![CDATA[]]>", Text("")),
    (" <![CDATA[]]><xliff:g> x </xliff:g>", Text(" x")),
    ("<xliff:g> x </xliff:g><![CDATA[]]> ", Text("x ")),
    (" <![CDATA[]]><xliff:g> x </xliff:g><![CDATA[]]> ", Text(" x ")),
    ("a<!-- comment -->b", Text("ab")),
    ("<b>a<!-- comment -->b</b>", Text("ab", (("b", 0, 1),))),
    ("<!-- before --> a <!-- after -->", Text("a")),
    (r"\u00<!-- split -->e9", Text("é")),
    (r"\<!-- split -->n", Text("\n")),
    ("a<?instruction ignored?>b", Text("ab")),
    ("<?before ignored?> a <?after ignored?>", Text("a")),
    (r"\u00<?instruction ignored?>e9", Text("é")),
    ("<b>😀<!-- comment -->x</b>", Text("😀x", (("b", 0, 2),))),
    ("<b>😀<?instruction ignored?>x</b>", Text("😀x", (("b", 0, 2),))),
    (r"don\'t", Text("don't")),
    ('"don\'t"', Text("don't")),
    (r"don\u0027t", Text("don't")),
    (r"A\ud800B", Text("AB")),
    (r"A\udfffB", Text("AB")),
    (r"A\ud83d\ude00B", Text("AB")),
    (r"\ud83d\ude00", Text("")),
    (r"A \ud800 B", Text("A  B")),
    (r"<b>A\ud83d\ude00B</b>", Text("AB", (("b", 0, 1),))),
    ('<xliff:g id="a">a</xliff:g><xliff:g id="b">b</xliff:g>', Text("ab")),
    ('<xliff:g id="a"><b>x</b></xliff:g>', Text("x", (("b", 0, 0),))),
    (
        '<font xmlns:x="urn:test" x:color="red">word</font>',
        Text("word", (("font;color=red", 0, 3),)),
    ),
    (
        '<a xmlns:x="urn:test" x:href="https://example.com/">😀</a>',
        Text("😀", (("a;href=https://example.com/", 0, 1),)),
    ),
    (
        (
            '<font xmlns:x="urn:a" xmlns:y="urn:aa" y:color="blue" '
            'x:size="12" x:color="red" color="green">word</font>'
        ),
        Text("word", (("font;color=green;color=red;size=12;color=blue", 0, 3),)),
    ),
]
INVALID_TEXT_CASES = [
    ("don't", "apostrophe"),
    ('"a"don\'t', "apostrophe"),
    ('<xliff:g id="a"><xliff:g id="b">x</xliff:g></xliff:g>', "nested XLIFF"),
    ('<xliff:g id="a"><b><xliff:g id="b">x</xliff:g></b></xliff:g>', "nested XLIFF"),
]


def run_aapt2(*args: str) -> str:
    """
    Run AAPT2, raising on compiler errors.

    Returns:
        Captured compiler output.

    """
    return subprocess.run(
        [os.environ["AAPT2"], *args], check=True, capture_output=True, text=True
    ).stdout


def compile_resources(root: Path, raw: str, locale: str = "fr") -> Path:
    """
    Compile strings and plurals with AAPT2.

    Returns:
        Path to the compiled APK.

    """
    values = root / "res" / f"values-{locale}"
    values.mkdir(parents=True)
    manifest = root / "AndroidManifest.xml"
    manifest.write_text('<manifest package="org.weblate.sample"/>', encoding="utf-8")
    (values / "strings.xml").write_text(
        f'<resources xmlns:xliff="urn:oasis:names:tc:xliff:document:1.2"><string name="sample">{raw}</string><plurals name="count"><item quantity="other">{raw}</item></plurals></resources>',
        encoding="utf-8",
    )
    compiled = root / "compiled.zip"
    apk = root / "compiled.apk"
    run_aapt2("compile", "--dir", str(root / "res"), "-o", str(compiled))
    run_aapt2(
        "link",
        "--no-resource-removal",
        "--manifest",
        str(manifest),
        "-o",
        str(apk),
        str(compiled),
    )
    return apk


@pytest.mark.parametrize(("raw", "expected"), COMPATIBLE_TEXT_CASES)
def test_android_text_compatibility(raw: str, expected: Text) -> None:
    """Normalize fragments with the same text and offsets as Android."""
    assert android_text(raw, markup=True) == expected


@pytest.mark.parametrize("markup", [False, True])
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ('a "" b', Text("a  b")),
        (r"A\ud83d\ude00B", Text("AB")),
        (r"don\'t", Text("don't")),
        ('"don\'t"', Text("don't")),
        (r"\\u0000", Text(r"\u0000")),
    ],
)
def test_plain_text_compatibility(raw: str, expected: Text, *, markup: bool) -> None:
    """Apply escape and quote rules with either parsing mode."""
    assert android_text(raw, markup=markup) == expected


@pytest.mark.parametrize(("raw", "message"), INVALID_TEXT_CASES)
def test_invalid_android_text(raw: str, message: str) -> None:
    """Reject apostrophes and placeholder nesting rejected by Android."""
    with pytest.raises(ValueError, match=message):
        android_text(raw, markup=True)


@pytest.mark.parametrize("markup", [False, True])
@pytest.mark.parametrize("nul", ["\0", r"\u0000"])
@pytest.mark.parametrize("template", ["{}", "{}ab", "a{}b", "ab{}", "<b>a{}b</b>"])
def test_android_text_rejects_nul(template: str, nul: str, *, markup: bool) -> None:
    """Reject NULs before XML parsing and after decoding Android escapes."""
    with pytest.raises(
        ValueError, match="Android strings cannot contain NUL characters"
    ):
        android_text(template.format(nul), markup=markup)


@pytest.mark.parametrize("tag", sorted(SPAN_TAGS))
@pytest.mark.parametrize("contents", ["", '""', r"\ud800", "<!-- empty -->"])
def test_empty_android_style(tag: str, contents: str) -> None:
    """Reject styles emptied by parsing or Android text normalization."""
    with pytest.raises(ValueError, match=f"Empty Android span: {tag}"):
        android_text(f"a<{tag}>{contents}</{tag}>b", markup=True)


@pytest.mark.parametrize("raw", ["a<li/>b", "<b/>", "<b>a<i/>b</b>"])
def test_self_closing_android_style(raw: str) -> None:
    """Reject empty spans before consuming their tails or closing their parents."""
    with pytest.raises(ValueError, match="Empty Android span"):
        android_text(raw, markup=True)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("", Text("")),
        ("<xliff:g/>", Text("")),
        ("a<xliff:g/>b", Text("ab")),
        ("<b> </b>", Text(" ", (("b", 0, 0),))),
        ("<b><xliff:g/>x</b>", Text("x", (("b", 0, 0),))),
    ],
)
def test_empty_text_and_nonempty_styles(raw: str, expected: Text) -> None:
    """Allow empty unstyled text and styles with actual output characters."""
    assert android_text(raw, markup=True) == expected


@pytest.mark.skipif(
    not os.environ.get("AAPT2"), reason="Set AAPT2 for Android compiler comparisons"
)
def test_aapt2_empty_paragraph_style(tmp_path: Path) -> None:
    """Android retains empty paragraph styles that this writer cannot represent."""
    raw = "a<li/>b"
    apk = compile_resources(tmp_path, raw)
    assert '"ab" li:1,0' in run_aapt2("dump", "resources", str(apk))
    with pytest.raises(ValueError, match="Empty Android span: li"):
        android_text(raw, markup=True)


def test_unescaped_plain_apostrophe() -> None:
    """Reject unescaped apostrophes in plain text as well as XML fragments."""
    with pytest.raises(ValueError, match="apostrophe"):
        android_text("don't")


@pytest.mark.skipif(
    not os.environ.get("AAPT2"), reason="Set AAPT2 for Android compiler comparisons"
)
@pytest.mark.parametrize(("raw", "message"), INVALID_TEXT_CASES)
def test_aapt2_invalid_text(tmp_path: Path, raw: str, message: str) -> None:
    """Verify invalid-fragment regressions against Android's compiler."""
    with pytest.raises(subprocess.CalledProcessError) as error:
        compile_resources(tmp_path, raw)
    assert message in error.value.stderr


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
        *(raw for raw, _ in COMPATIBLE_TEXT_CASES),
    ],
)
def test_aapt2_whitespace(raw: str) -> None:
    """Aapt2 whitespace."""
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        apk = compile_resources(root, raw)
        expected = run_aapt2("dump", "resources", str(apk))
        with zipfile.ZipFile(apk) as archive:
            binary_manifest = archive.read("AndroidManifest.xml")
        with zipfile.ZipFile(apk, "w") as archive:
            archive.writestr("AndroidManifest.xml", binary_manifest)
            text = android_text(raw, markup=True)
            archive.writestr(
                "resources.arsc",
                generate(
                    {
                        0x7F010000: ("count", {"other": text}),
                        0x7F020000: ("sample", text),
                    },
                    package="org.weblate.sample",
                    locale="fr",
                ),
            )
        actual = run_aapt2("dump", "resources", str(apk))
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


def test_many_supplementary_spans() -> None:
    """Count literal supplementary characters as two UTF-16 units."""
    text = android_text("<b>😀<i>!</i></b> " * 2000, markup=True)
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


@pytest.mark.parametrize(
    ("locale", "canonical"),
    [
        ("EN", "en"),
        ("b+sr+latn+rs", "b+sr+Latn+RS"),
        ("b+SR+LATN+RS", "b+sr+Latn+RS"),
        ("b+en+us", "en-US"),
        ("sR-lAtN-rS", "b+sr+Latn+RS"),
        ("SR_latn_rs", "b+sr+Latn+RS"),
        ("PT-rbr", "pt-BR"),
        ("pt-RbR", "pt-BR"),
        ("b+ES+419", "es-419"),
        ("b+FIL+latn+ph", "b+fil+Latn+PH"),
        ("b+EN+us+PoSiX", "b+en+US+posix"),
    ],
)
def test_locale_case(locale: str, canonical: str) -> None:
    """Normalize ASCII casing across all supported locale syntaxes."""
    assert locale_config(locale) == locale_config(canonical)


@pytest.mark.parametrize("locale", ["b+en+US+POSIX", "en-US-PoSiX", "en_US_posix"])
def test_locale_variant_case(locale: str) -> None:
    """Canonicalize variants for Android's case-sensitive locale selection."""
    assert locale_config(locale) == locale_config("b+en+US+posix")
    assert locale_config(locale)[40:48] == b"posix\0\0\0"


def type_configs(data: bytes) -> list[bytes]:
    """
    Read configurations from the type chunks in a resource table.

    Returns:
        Raw configuration bytes for each type chunk.

    """
    configs: list[bytes] = []
    offset = 0
    while offset < len(data):
        kind, header_size, size = struct.unpack_from("<HHI", data, offset)
        if kind in {2, 0x0200}:
            configs.extend(type_configs(data[offset + header_size : offset + size]))
        elif kind == 0x0201:  # ruff: ignore[magic-value-comparison]
            config_size = struct.unpack_from("<I", data, offset + 20)[0]
            configs.append(data[offset + 20 : offset + 20 + config_size])
        offset += size
    return configs


@pytest.mark.skipif(
    not os.environ.get("AAPT2"), reason="Set AAPT2 for Android compiler comparisons"
)
@pytest.mark.parametrize("variant", ["POSIX", "PoSiX", "posix"])
def test_aapt2_locale_variant(tmp_path: Path, variant: str) -> None:
    """Compare encoded variant bytes with the compiler, not just its dump."""
    locale = f"b+en+US+{variant}"
    apk = compile_resources(tmp_path, "sample", locale)
    with zipfile.ZipFile(apk) as archive:
        expected = type_configs(archive.read("resources.arsc"))
    actual = type_configs(
        generate(
            {0x7F010000: ("sample", Text("sample"))},
            package="org.weblate.sample",
            locale=locale,
        )
    )
    assert expected
    assert actual
    assert {config[40:48] for config in expected} == {
        config[40:48] for config in actual
    }


@pytest.mark.skipif(
    not os.environ.get("AAPT2"), reason="Set AAPT2 for Android compiler comparisons"
)
@pytest.mark.parametrize(
    "locale",
    ["b+sr+latn+rs", "b+SR+LATN+RS", "b+en+us", "b+ES+419", "b+FIL+latn+ph"],
)
def test_aapt2_locale_case(tmp_path: Path, locale: str) -> None:
    """Match Android's encoded language, region, script, and variant fields."""
    apk = compile_resources(tmp_path, "sample", locale)
    with zipfile.ZipFile(apk) as archive:
        expected = type_configs(archive.read("resources.arsc"))
    actual = type_configs(
        generate(
            {0x7F010000: ("sample", Text("sample"))},
            package="org.weblate.sample",
            locale=locale,
        )
    )
    assert expected
    assert actual
    assert {(config[8:12], config[36:48]) for config in actual} == {
        (config[8:12], config[36:48]) for config in expected
    }


@pytest.mark.parametrize("plural", [False, True])
@pytest.mark.parametrize(
    "text",
    [
        Text("\0"),
        Text("\0ab"),
        Text("a\0b"),
        Text("ab\0"),
        Text("a\0b", (("b", 0, 2),)),
        Text("ab", (("font;color=red\0blue", 0, 1),)),
    ],
)
def test_generate_rejects_nul(text: Text, *, plural: bool) -> None:
    """Prevent direct text and span tags from bypassing NUL validation."""
    resource: ResourceValue = {"other": text} if plural else text
    with pytest.raises(
        ValueError, match="Android strings cannot contain NUL characters"
    ):
        generate(
            {0x7F010000: ("sample", resource)},
            package="org.weblate.sample",
            locale="en",
        )


@pytest.mark.parametrize("plural", [False, True])
@pytest.mark.parametrize(
    ("value", "first", "last"),
    [
        ("x", -1, 0),
        ("ab", 1, 0),
        ("x", 0, 1),
        ("x", 1, 1),
        ("x", 0, 100),
        ("", 0, 0),
        ("😀", 0, 2),
    ],
)
def test_invalid_span_range(value: str, first: int, last: int, *, plural: bool) -> None:
    """Reject ranges outside the writer's supported nonempty span model."""
    text = Text(value, (("i", first, last),))
    resource: ResourceValue = {"other": text} if plural else text
    with pytest.raises(ValueError, match="Invalid Android span range"):
        generate(
            {0x7F010000: ("sample", resource)},
            package="org.weblate.sample",
            locale="en",
        )


@pytest.mark.parametrize("plural", [False, True])
@pytest.mark.parametrize(
    "text",
    [
        Text(""),
        Text("x", (("i", 0, 0),)),
        Text("😀", (("i", 0, 1),)),
        Text("a😀b", (("b", 0, 3), ("i", 1, 2), ("u", 2, 3))),
    ],
)
def test_valid_span_range(text: Text, *, plural: bool) -> None:
    """Serialize valid UTF-16 boundaries, nesting, and overlapping spans."""
    resource: ResourceValue = {"other": text} if plural else text
    assert generate(
        {0x7F010000: ("sample", resource)}, package="org.weblate.sample", locale="en"
    )


@pytest.mark.parametrize("value", [Text("sample"), {"other": Text("sample")}])
def test_entry_index_limit(value: ResourceValue) -> None:
    """Reject entry counts Android cannot load, while accepting the boundary."""
    data = generate(
        {0x7F01FFFE: ("sample", value)}, package="org.weblate.sample", locale="en"
    )
    assert type_configs(data) == [locale_config("en")]
    with pytest.raises(ValueError, match="entry index"):
        generate(
            {0x7F01FFFF: ("sample", value)}, package="org.weblate.sample", locale="en"
        )


def test_container_lengths_and_determinism() -> None:
    """Container lengths and determinism."""
    resources: ResourceTable = {
        0x7F090003: ("welcome", Text("Hello")),
        0x7F080012: ("count", {"one": Text("One"), "other": Text("Many")}),
    }
    data = generate(resources, package="org.weblate.sample", locale="cs")
    assert struct.unpack_from("<HHII", data) == (2, 12, len(data), 1)
    assert data == generate(resources, package="org.weblate.sample", locale="cs")
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
                "resources.arsc",
                generate(resources, package="org.weblate.sample", locale="fr"),
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


@pytest.mark.parametrize("markup", [False, True])
@pytest.mark.parametrize("value", ["trailing\\", r"\u", r"\u123", r"\uXXXX", '"open'])
def test_invalid_escaping(value: str, *, markup: bool) -> None:
    """Reject malformed Android escapes and quotes."""
    with pytest.raises(ValueError, match=r"escape|quote"):
        android_text(value, markup=markup)


@pytest.mark.skipif(
    not os.environ.get("AAPT2"), reason="Set AAPT2 for Android compiler comparisons"
)
@pytest.mark.parametrize(
    ("raw", "expected"),
    [('"open', "open"), ("trailing\\", "trailing"), (r"\u123", "ģ")],
)
def test_aapt2_lenient_escaping(tmp_path: Path, raw: str, expected: str) -> None:
    """Document compiler leniency intentionally rejected by android_text."""
    apk = compile_resources(tmp_path, raw)
    dumped = run_aapt2("dump", "resources", str(apk))
    assert f'(fr) "{expected}"' in dumped
    assert f'other="{expected}"' in dumped
    with pytest.raises(ValueError, match=r"escape|quote"):
        android_text(raw, markup=True)


@pytest.mark.parametrize(
    "locale",
    [
        "",
        "b",
        "b-en",
        "b+",
        "english",
        "en-invalid!",
        "e\u212a",
        "en-u\u017f",
        "en-\u212aatn",
    ],
)
def test_invalid_locale(locale: str) -> None:
    """Reject unsupported language and qualifier syntax."""
    with pytest.raises(ValueError, match="Android"):
        locale_config(locale)
    with pytest.raises(ValueError, match="Android"):
        generate(
            {0x7F010000: ("sample", Text("sample"))},
            package="org.weblate.sample",
            locale=locale,
        )


@pytest.mark.parametrize(
    ("locale", "field"),
    [
        ("en-US-GB", "region"),
        ("en_US_US", "region"),
        ("b+en+419+419", "region"),
        ("en-Latn-Cyrl", "script"),
        ("b+en+Latn+latn", "script"),
        ("b+sl+rozaj+biske", "variant"),
        ("b+en+Latn+US+posix+extra", "variant"),
        ("en-posix-POSIX", "variant"),
    ],
)
def test_repeated_locale_qualifiers(locale: str, field: str) -> None:
    """Reject qualifiers that would overwrite a previously supplied field."""
    message = f"Repeated Android locale {field}"
    with pytest.raises(ValueError, match=message):
        locale_config(locale)
    with pytest.raises(ValueError, match=message):
        generate(
            {0x7F010000: ("sample", Text("sample"))},
            package="org.weblate.sample",
            locale=locale,
        )


@pytest.mark.parametrize("resource_id", [-1, -0x7F010000, 0x100000000, 0x17F010000])
def test_resource_id_bounds(resource_id: int) -> None:
    """Reject IDs that cannot fit in an Android resource identifier."""
    with pytest.raises(ValueError, match="unsigned 32-bit"):
        generate(
            {resource_id: ("sample", Text("sample"))},
            package="org.weblate.sample",
            locale="en",
        )


@pytest.mark.parametrize("package_id", [0, 1, 0x7F, 0xFF])
def test_valid_package_id_bounds(package_id: int) -> None:
    """Preserve the complete package byte, including dynamic package ID zero."""
    resource_id = package_id << 24 | 0x010000
    data = generate(
        {resource_id: ("sample", Text("sample"))},
        package="org.weblate.sample",
        locale="en",
    )
    string_pool_size = struct.unpack_from("<I", data, 16)[0]
    assert struct.unpack_from("<I", data, 12 + string_pool_size + 8)[0] == package_id


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
        generate(resources, package="org.weblate.sample", locale="en")


@pytest.mark.parametrize("value", [Text("sample"), {"other": Text("sample")}])
def test_resource_kind_multiple_type_ids(value: ResourceValue) -> None:
    """Reject type names that Android cannot resolve unambiguously."""
    with pytest.raises(ValueError, match="uses multiple type IDs"):
        generate(
            {0x7F010000: ("first", value), 0x7F090003: ("second", value)},
            package="org.weblate.sample",
            locale="en",
        )


@pytest.mark.parametrize("value", [Text("sample"), {"other": Text("sample")}])
def test_duplicate_resource_names(value: ResourceValue) -> None:
    """Reject two IDs for the same resource name within one type."""
    with pytest.raises(ValueError, match="Duplicate Android resource name"):
        generate(
            {0x7F090000: ("same", value), 0x7F090003: ("same", value)},
            package="org.weblate.sample",
            locale="en",
        )


def test_shared_resource_names_across_types() -> None:
    """Keep names scoped to their kind and allow sparse caller-assigned IDs."""
    data = generate(
        {
            0x7F080003: ("same", Text("first")),
            0x7F080012: ("different", Text("second")),
            0x7F090003: ("same", {"other": Text("items")}),
        },
        package="org.weblate.sample",
        locale="en",
    )
    assert type_configs(data) == [locale_config("en"), locale_config("en")]


@pytest.mark.parametrize(
    "package", ["\0org.example", "org.example\0.other", "org.example\0"]
)
def test_package_name_nul(package: str) -> None:
    """Reject NULs so Android cannot silently truncate the package name."""
    with pytest.raises(ValueError, match="NUL"):
        generate({0x7F010000: ("a", Text("a"))}, package=package, locale="en")


def test_package_name_limit() -> None:
    """Reject package names longer than the resource header allows."""
    with pytest.raises(ValueError, match="package name is too long"):
        generate({0x7F010000: ("a", Text("a"))}, package="a" * 128, locale="en")
