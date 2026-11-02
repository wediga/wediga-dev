"""The texts of a portfolio tile from fixed sections of a README.

A section starts at its ``##`` heading and reaches up to the next heading of
the first or second level. Its Markdown becomes plain text with paragraphs:
bold, links and inline code turn into their text, images and HTML tags go,
code blocks, tables and rules are left out, a deeper heading stays as its own
paragraph and every list item gets its own line.
"""

import re

from app.github.schemas import TextFieldKey

# The README heading of each text field that comes from a README.
SECTIONS: dict[TextFieldKey, str] = {
    "problem": "Why This Exists",
    "solution": "What It Does",
    "learning": "What I Learned",
    "ending": "Why It Ended",
}

_SECTION_HEADING = re.compile(r"^(#{1,2})\s+(.*?)\s*#*\s*$")
_DEEPER_HEADING = re.compile(r"^#{3,6}\s+(.*?)\s*#*\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")
_RULE = re.compile(r"^\s*([-*_])(\s*\1){2,}\s*$")
_LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
_QUOTE = re.compile(r"^\s*>\s?")

# In this order: images go before their brackets read as a link.
_INLINE = (
    (re.compile(r"!\[[^]]*]\([^)]*\)"), ""),
    (re.compile(r"\[([^]]*)](?:\([^)]*\)|\[[^]]*])"), r"\1"),
    (re.compile(r"<[^>]+>"), ""),
    (re.compile(r"`([^`]*)`"), r"\1"),
    (re.compile(r"(\*\*|__)(.+?)\1"), r"\2"),
    (re.compile(r"(?<!\w)([*_])(.+?)\1(?!\w)"), r"\2"),
)


def _inline(text: str) -> str:
    for pattern, replacement in _INLINE:
        text = pattern.sub(replacement, text)

    return text.strip()


def _split(markdown: str) -> dict[str, list[str]]:
    """Return the lines under each ``##`` heading, by its text."""
    sections: dict[str, list[str]] = {}
    current: list[str] | None = None
    in_code = False

    for line in markdown.splitlines():
        if _FENCE.match(line):
            in_code = not in_code
        heading = None if in_code else _SECTION_HEADING.match(line)

        if heading:
            current = (
                sections.setdefault(heading[2], []) if heading[1] == "##" else None
            )
        elif current is not None:
            current.append(line)

    return sections


def _blocks(lines: list[str]) -> list[str]:
    """Return the plain paragraphs of a section, without code and tables."""
    blocks: list[list[str]] = [[]]
    in_code = False

    for line in lines:
        if _FENCE.match(line):
            in_code = not in_code

            continue

        stripped = _QUOTE.sub("", line).strip()

        if in_code or stripped.startswith("|") or _RULE.match(stripped):
            continue

        heading = _DEEPER_HEADING.match(stripped)

        if not stripped or heading:
            blocks.append([_inline(heading[1])] if heading else [])
            blocks.append([])
        elif _LIST_ITEM.match(stripped):
            blocks[-1].append("\n- " + _inline(_LIST_ITEM.sub("", stripped)))
        else:
            blocks[-1].append(" " + _inline(stripped))

    paragraphs = ("".join(block).strip() for block in blocks)

    return [paragraph for paragraph in paragraphs if paragraph]


def sections(markdown: str) -> dict[TextFieldKey, str]:
    """Return the text of each README section that is present and not empty."""
    by_heading = _split(markdown)
    texts: dict[TextFieldKey, str] = {
        field: "\n\n".join(_blocks(by_heading.get(heading, [])))
        for field, heading in SECTIONS.items()
    }

    return {field: text for field, text in texts.items() if text}
