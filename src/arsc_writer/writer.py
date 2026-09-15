# Copyright © Michal Čihař <michal@weblate.org>
#
# SPDX-License-Identifier: MIT

"""Write Android resource tables without an Android toolchain."""

# Binary-format field widths and sentinels are kept beside their encodings.

from __future__ import annotations

import re
import struct
from dataclasses import dataclass

from lxml import etree

QUANTITIES = {
    name: 0x01000004 + index
    for index, name in enumerate(("other", "zero", "one", "two", "few", "many"))
}
SPAN_TAGS = frozenset(
    {
        "b",
        "i",
        "u",
        "tt",
        "big",
        "small",
        "sup",
        "sub",
        "strike",
        "li",
        "marquee",
        "font",
        "a",
        "annotation",
    }
)
ANDROID_WHITESPACE = " \t\n\r\f\v"


@dataclass(frozen=True)
class Text:
    """Decoded text with style tags and inclusive UTF-16 span offsets."""

    value: str
    spans: tuple[tuple[str, int, int], ...] = ()


type ResourceValue = Text | dict[str, Text]
type ResourceTable = dict[int, tuple[str, ResourceValue]]


def utf16_length(value: str) -> int:
    """
    Return the number of UTF-16 code units in text.

    Returns:
        Number of UTF-16 code units.

    """
    return len(value.encode("utf-16-le", errors="surrogatepass")) // 2


def _validate_no_nul(value: str) -> None:
    """
    Reject NULs to avoid AAPT2's truncation of UTF-8 string-pool contents.

    Raises:
        ValueError: The value contains a NUL character.

    """
    if "\0" in value:
        msg = "Android strings cannot contain NUL characters"
        raise ValueError(msg)


# Escaping and nested spans share the whitespace/quoting state.
def android_text(value: str, *, markup: bool = False) -> Text:  # ruff: ignore[complex-structure, too-many-statements]
    """
    Decode Android quoting/escapes and retain actual XML spans.

    Escaped HTML and CDATA are passed with markup=False, as literal text.
    Malformed markup propagates lxml.etree.XMLSyntaxError from the XML parser.
    Unlike AAPT2, unfinished quotes, trailing backslashes, and Unicode escapes
    with fewer than four hexadecimal digits are rejected.
    Literal and escaped NUL characters are also rejected.

    Returns:
        Decoded text and inclusive UTF-16 style spans.

    Raises:
        ValueError: An escape, quote, Unicode sequence, or span is invalid,
            or the text contains a NUL character.

    """
    _validate_no_nul(value)
    output: list[str] = []
    spans: list[tuple[str, int, int]] = []
    quoted = False
    last_space = False
    output_length = 0

    def append(text: str) -> None:  # ruff: ignore[complex-structure]
        nonlocal quoted, last_space, output_length
        index = 0
        while index < len(text):
            char = text[index]
            index += 1
            if char == "\\":
                last_space = False
                if index == len(text):
                    msg = "Trailing Android string escape"
                    raise ValueError(msg)
                char = text[index]
                index += 1
                if char == "u":
                    digits = text[index : index + 4]
                    if not re.fullmatch(r"[0-9a-fA-F]{4}", digits):
                        msg = "Invalid Android Unicode escape"
                        raise ValueError(msg)
                    char = chr(int(digits, 16))
                    index += 4
                    # AAPT2 encodes each escape independently and drops surrogates.
                    if 0xD800 <= ord(char) <= 0xDFFF:
                        continue
                else:
                    char = {"n": "\n", "t": "\t"}.get(char, char)
            elif char == '"':
                last_space = False
                quoted = not quoted
                continue
            elif char == "'" and not quoted:
                msg = "Unescaped Android string apostrophe"
                raise ValueError(msg)
            elif char in ANDROID_WHITESPACE and not quoted:
                if not last_space:
                    output.append(" ")
                    output_length += 1
                last_space = True
                continue
            else:
                last_space = False
            output.append(char)
            output_length += 2 if ord(char) > 0xFFFF else 1

    def visit(node: etree._Element, *, in_xliff: bool = False) -> None:
        nonlocal quoted, last_space
        append(node.text or "")
        for child in node:
            name = etree.QName(child).localname
            namespace = etree.QName(child).namespace
            is_xliff = (
                namespace == "urn:oasis:names:tc:xliff:document:1.2" and name == "g"
            )
            if is_xliff and in_xliff:
                msg = "Illegal nested XLIFF g element"
                raise ValueError(msg)
            if not is_xliff and (namespace or name not in SPAN_TAGS):
                msg = f"Unsupported Android span: {name}"
                raise ValueError(msg)
            start = output_length
            span_index = len(spans)
            tag = name + "".join(
                f";{localname}={val}"
                for _, localname, val in sorted(
                    (etree.QName(key).namespace or "", etree.QName(key).localname, val)
                    for key, val in child.attrib.items()
                )
            )
            if not is_xliff:
                quoted = last_space = False
                spans.append((tag, start, start - 1))
            visit(child, in_xliff=in_xliff or is_xliff)
            end = output_length - 1
            if not is_xliff:
                if end < start:
                    msg = f"Empty Android span: {name}"
                    raise ValueError(msg)
                spans[span_index] = (tag, start, end)
                quoted = last_space = False
            append(child.tail or "")

    if markup:
        parser = etree.XMLParser(
            resolve_entities=False,
            no_network=True,
            remove_comments=True,
            remove_pis=True,
        )
        root = etree.fromstring(
            f'<resources xmlns:xliff="urn:oasis:names:tc:xliff:document:1.2">{value}</resources>'.encode(),
            parser,
        )
        # AAPT2 trims raw boundary text only for resources without styling.
        if not any(
            etree.QName(node).namespace is None for node in root.iterdescendants()
        ):
            # AAPT2 skips empty text segments, including empty CDATA nodes.
            texts = [text for text in root.xpath(".//text()") if text]
            if texts:
                for text, side in ((texts[0], "left"), (texts[-1], "right")):
                    parent = text.getparent()
                    attribute = "tail" if text.is_tail else "text"
                    raw = getattr(parent, attribute) or ""
                    setattr(
                        parent,
                        attribute,
                        raw.lstrip(ANDROID_WHITESPACE)
                        if side == "left"
                        else raw.rstrip(ANDROID_WHITESPACE),
                    )
        visit(root)
    else:
        append(value.strip(ANDROID_WHITESPACE))
    if quoted:
        msg = "Unterminated Android string quote"
        raise ValueError(msg)
    normalized = "".join(output)
    _validate_no_nul(normalized)
    return Text(normalized, tuple(spans))


def chunk(kind: int, header: bytes, data: bytes = b"") -> bytes:
    """
    Build a resource chunk with its size and header length.

    Returns:
        The serialized chunk, including its header.

    """
    return (
        struct.pack("<HHI", kind, 8 + len(header), 8 + len(header) + len(data))
        + header
        + data
    )


def padded(data: bytes) -> bytes:
    """
    Align data to a four-byte boundary.

    Returns:
        Input bytes followed by zero padding.

    """
    return data + b"\0" * (-len(data) % 4)


def string_pool(values: list[Text]) -> bytes:
    """
    Encode UTF-16 strings and their styles into a resource string pool.

    Returns:
        An Android UTF-16 string pool chunk.

    Raises:
        ValueError: A string contains a NUL, exceeds the Android length limit,
            or a span is invalid.

    """
    strings = list(values)
    known = set(strings)
    for text in values:
        for tag, _, _ in text.spans:
            if Text(tag) not in known:
                strings.append(Text(tag))
                known.add(Text(tag))
    indexes = {text: index for index, text in enumerate(strings)}
    data = bytearray()
    offsets = []
    for text in strings:
        _validate_no_nul(text.value)
        offsets.append(len(data))
        encoded = text.value.encode("utf-16-le")
        size = len(encoded) // 2
        if size > 0x7FFFFFFF:
            msg = "Android string is too long"
            raise ValueError(msg)
        if any(not 0 <= first <= last < size for _, first, last in text.spans):
            msg = f"Invalid Android span range for {size} UTF-16 code units"
            raise ValueError(msg)
        data.extend(
            struct.pack("<HH", (size >> 16) | 0x8000, size & 0xFFFF)
            if size > 0x7FFF
            else struct.pack("<H", size)
        )
        data.extend(encoded + b"\0\0")
    styles = bytearray()
    style_offsets = []
    if any(text.spans for text in strings):
        for text in strings:
            style_offsets.append(len(styles))
            for tag, start, end in text.spans:
                styles.extend(struct.pack("<III", indexes[Text(tag)], start, end))
            styles.extend(struct.pack("<III", 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF))
    start = 28 + 4 * (len(offsets) + len(style_offsets))
    payload = struct.pack(
        f"<{len(offsets) + len(style_offsets)}I", *offsets, *style_offsets
    ) + padded(bytes(data))
    header = struct.pack(
        "<IIIII",
        len(strings),
        len(style_offsets),
        0,
        start,
        28 + len(payload) if styles else 0,
    )
    return chunk(1, header, payload + bytes(styles))


def locale_config(locale: str) -> bytes:  # ruff: ignore[complex-structure]
    """
    Encode language/region/script qualifiers in a 64-byte ResTable_config.

    Returns:
        A 64-byte Android resource configuration.

    Raises:
        ValueError: A language or locale qualifier is unsupported.

    """
    config = bytearray(64)
    struct.pack_into("<I", config, 0, 64)
    parts = locale.replace("_", "-").split("-")
    if locale.startswith("b+"):
        parts = locale.split("+")[1:]
    language = parts.pop(0)

    def packed(value: str, base: str) -> bytes:
        if len(value) == 2:
            return value.encode("ascii")
        if len(value) != 3:
            msg = f"Unsupported Android locale: {locale}"
            raise ValueError(msg)
        a, b, c = (ord(char) - ord(base) for char in value)
        if not all(0 <= item < 32 for item in (a, b, c)):
            msg = f"Invalid Android locale: {locale}"
            raise ValueError(msg)
        return bytes((0x80 | (c << 2) | (b >> 3), (b << 5 & 0xFF) | a))

    if not re.fullmatch(r"[a-zA-Z]{2,3}", language):
        msg = f"Invalid Android language: {locale}"
        raise ValueError(msg)
    config[8:10] = packed(language.lower(), "a")
    for part in parts:
        if re.fullmatch(r"[rR]?[a-zA-Z]{2}|[0-9]{3}", part):
            if config[10]:
                msg = f"Repeated Android locale region: {locale}"
                raise ValueError(msg)
            region = part[1:] if len(part) == 3 and part[0] in "rR" else part
            config[10:12] = packed(region.upper(), "0")
        elif re.fullmatch(r"[a-zA-Z]{4}", part):
            if config[36]:
                msg = f"Repeated Android locale script: {locale}"
                raise ValueError(msg)
            config[36:40] = part.title().encode("ascii")
        elif re.fullmatch(r"[a-zA-Z0-9]{5,8}|[0-9][a-zA-Z0-9]{3}", part):
            if config[40]:
                msg = f"Repeated Android locale variant: {locale}"
                raise ValueError(msg)
            config[40:48] = part.lower().encode("ascii").ljust(8, b"\0")
        else:
            msg = f"Unsupported Android locale qualifier: {part}"
            raise ValueError(msg)
    return bytes(config)


def _encode_entry(key: int, value: ResourceValue, value_ids: dict[Text, int]) -> bytes:
    """
    Encode a string entry or a plural bag, validating its quantities.

    Returns:
        The serialized entry and its value or plural maps.

    Raises:
        ValueError: Plural quantities are invalid or omit other.

    """
    if not isinstance(value, dict):
        return struct.pack("<HHIHBBI", 8, 0, key, 8, 0, 3, value_ids[value])
    if "other" not in value or value.keys() - QUANTITIES.keys():
        msg = "Invalid plural quantities"
        raise ValueError(msg)
    data = bytearray(struct.pack("<HHIII", 16, 1, key, 0, len(value)))
    for quantity, text in sorted(value.items(), key=lambda item: QUANTITIES[item[0]]):
        data.extend(
            struct.pack("<IHBBI", QUANTITIES[quantity], 8, 0, 3, value_ids[text])
        )
    return bytes(data)


def _encode_type(
    type_id: int,
    locale: str,
    entries: ResourceTable,
    keys: dict[str, int],
    value_ids: dict[Text, int],
) -> tuple[Text, bytes]:
    """
    Encode one resource type using entry indices as the entries mapping keys.

    Returns:
        The type name and concatenated specification and type chunks.

    Raises:
        ValueError: Resource kinds are mixed, names repeat, or the entry count
            exceeds Android's limit.

    """
    kinds = {isinstance(value, dict) for _, value in entries.values()}
    if len(kinds) != 1:
        msg = "Strings and plurals need distinct resource types"
        raise ValueError(msg)
    if len({name for name, _ in entries.values()}) != len(entries):
        msg = "Duplicate Android resource name within a type"
        raise ValueError(msg)
    count = max(entries) + 1
    if count > 0xFFFF:
        msg = "Android resource entry index must not exceed 0xfffe"
        raise ValueError(msg)
    spec = chunk(
        0x0202,
        struct.pack("<BBHI", type_id, 0, 0, count),
        struct.pack(
            f"<{count}I", *[4 if index in entries else 0 for index in range(count)]
        ),
    )
    offsets = [0xFFFFFFFF] * count
    data = bytearray()
    for index, (name, value) in sorted(entries.items()):
        offsets[index] = len(data)
        data.extend(_encode_entry(keys[name], value, value_ids))
    header = struct.pack(
        "<BBHII", type_id, 0, 0, count, 84 + count * 4
    ) + locale_config(locale)
    return Text("plurals" if True in kinds else "string"), spec + chunk(
        0x0201, header, struct.pack(f"<{count}I", *offsets) + bytes(data)
    )


def _encode_types(
    locale: str,
    resources: ResourceTable,
    keys: dict[str, int],
    value_ids: dict[Text, int],
) -> tuple[list[Text], bytes]:
    """
    Group resources by type and encode their names and chunks in ID order.

    Returns:
        Type names with empty slots for missing IDs, and concatenated type chunks.

    Raises:
        ValueError: A resource has type ID zero or a resource kind uses multiple IDs.

    """
    type_ids = sorted({resource_id >> 16 & 0xFF for resource_id in resources})
    if not type_ids[0]:
        msg = "Invalid resource type ID"
        raise ValueError(msg)
    types = [Text("") for _ in range(max(type_ids))]
    type_chunks: list[bytes] = []
    for type_id in type_ids:
        entries = {
            resource_id & 0xFFFF: value
            for resource_id, value in resources.items()
            if resource_id >> 16 & 0xFF == type_id
        }
        type_name, encoded = _encode_type(type_id, locale, entries, keys, value_ids)
        if type_name in types:
            msg = f"Android resource kind {type_name.value} uses multiple type IDs"
            raise ValueError(msg)
        types[type_id - 1] = type_name
        type_chunks.append(encoded)
    return types, b"".join(type_chunks)


def _encode_package(
    package: str,
    locale: str,
    resources: ResourceTable,
    value_ids: dict[Text, int],
) -> bytes:
    """
    Assemble the package header, name pools, and resource type chunks.

    Returns:
        The complete package chunk for sorted, validated resource IDs.

    Raises:
        ValueError: The package name contains a NUL or exceeds the header's capacity.

    """
    names = sorted({name for name, _ in resources.values()})
    keys = {name: index for index, name in enumerate(names)}
    types, type_chunks = _encode_types(locale, resources, keys, value_ids)
    type_pool = string_pool(types)
    key_pool = string_pool([Text(name) for name in names])
    _validate_no_nul(package)
    package_name = package.encode("utf-16-le")
    if len(package_name) > 254:
        msg = "Android resource package name is too long"
        raise ValueError(msg)
    package_header = (
        struct.pack("<I", next(iter(resources)) >> 24)
        + package_name.ljust(256, b"\0")
        + struct.pack("<IIIII", 288, len(types), 288 + len(type_pool), len(names), 0)
    )
    return chunk(0x0200, package_header, type_pool + key_pool + type_chunks)


def generate(resources: ResourceTable, *, package: str, locale: str) -> bytes:
    """
    Serialize self-contained strings and plural bags with caller-assigned IDs.

    Returns:
        A complete binary Android resource table.

    Raises:
        ValueError: Resources are empty or inconsistent, plural quantities are invalid,
        a span is invalid, a string contains a NUL, the locale is unsupported,
        or the package name contains a NUL or is too long.

    """
    if not resources:
        msg = "No translated resources"
        raise ValueError(msg)
    if any(not 0 <= resource_id <= 0xFFFFFFFF for resource_id in resources):
        msg = "Android resource IDs must be unsigned 32-bit values"
        raise ValueError(msg)
    resources = dict(sorted(resources.items()))
    package_ids = {resource_id >> 24 for resource_id in resources}
    if len(package_ids) != 1:
        msg = "Resource IDs must belong to one package"
        raise ValueError(msg)
    values = list(
        dict.fromkeys(
            text
            for _, value in resources.values()
            for text in (value.values() if isinstance(value, dict) else [value])
        )
    )
    value_ids = {text: index for index, text in enumerate(values)}
    package_chunk = _encode_package(package, locale, resources, value_ids)
    return chunk(2, struct.pack("<I", 1), string_pool(values) + package_chunk)
