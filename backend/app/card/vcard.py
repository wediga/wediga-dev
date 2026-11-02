"""Build the contact card as a vCard 3.0, the version every phone imports.

Lines end in CRLF and are folded after 75 octets, a folded line goes on with
a single space. Text values escape backslash, comma, semicolon and line
breaks. Addresses (email and links) are not escaped, so a line break in one
is dropped instead, it could otherwise start a line of its own.
"""

import base64

from app.card.schemas import CardContent
from app.content.schemas import LinkKind
from app.portrait.router import JPEG, PNG, image_type

CRLF = "\r\n"
FOLD_AT = 75
# The photo types phones read in a vCard, WebP is left out.
PHOTO_TYPES = {JPEG: "JPEG", PNG: "PNG"}
# A label per link, so a phone names each one instead of listing bare URLs.
LINK_LABELS: dict[LinkKind, str] = {
    "website": "Website",
    "linkedin": "LinkedIn",
    "github": "GitHub",
}


def _escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(",", r"\,")
        .replace(";", r"\;")
        .replace("\n", r"\n")
    )


def _single_line(value: str) -> str:
    return value.replace("\r", "").replace("\n", "")


def _fold(line: str) -> str:
    """Split a line into chunks of at most 75 octets, never inside a character."""
    chunks: list[str] = []
    current = ""

    for char in line:
        limit = FOLD_AT if not chunks else FOLD_AT - 1

        if len((current + char).encode("utf-8")) > limit:
            chunks.append(current)
            current = ""

        current += char

    chunks.append(current)

    return (CRLF + " ").join(chunks)


def _name(full_name: str) -> str:
    """The structured name: the last word as family name, the rest as given."""
    given, _, family = full_name.strip().rpartition(" ")

    return f"{_escape(family)};{_escape(given)};;;"


def _photo(photo: bytes | None) -> list[str]:
    if photo is None:
        return []

    kind = PHOTO_TYPES.get(image_type(photo) or "")

    if kind is None:
        return []

    data = base64.b64encode(photo).decode("ascii")

    return [f"PHOTO;ENCODING=b;TYPE={kind}:{data}"]


def build_vcard(card: CardContent, photo: bytes | None) -> str:
    lines = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"N:{_name(card.name)}",
        f"FN:{_escape(card.name)}",
        f"EMAIL;TYPE=INTERNET:{_single_line(card.email)}",
    ]

    if card.phone:
        lines.append(f"TEL;TYPE=CELL:{card.phone}")

    for number, (kind, label) in enumerate(LINK_LABELS.items(), start=1):
        url = card.links.get(kind)

        if url:
            lines += [
                f"item{number}.URL:{_single_line(url)}",
                f"item{number}.X-ABLabel:{label}",
            ]

    lines += _photo(photo)
    lines.append("END:VCARD")

    return "".join(_fold(line) + CRLF for line in lines)
