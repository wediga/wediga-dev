"""Tests for the contact card: the public view and its vCard.

The card shows name, email, phone and links to every visitor, never the
address. The vCard carries the same and the portrait, when it is a JPEG or a
PNG, in the form every phone imports.
"""

import base64
import importlib
import re

import pytest
from fastapi.testclient import TestClient

from app.card.schemas import CardContent
from app.card.vcard import FOLD_AT, LINK_LABELS, build_vcard
from app.content import repository
from app.content.schemas import LinkKind, ProfileAddress, ProfileContent
from app.portrait import storage
from tests.conftest import REPO_ROOT

LINKS: dict[LinkKind, str] = {
    "github": "https://github.com/example",
    "linkedin": "https://linkedin.com/in/example",
    "website": "https://example.com",
}
PROFILE = ProfileContent(
    name="Alexander Wedig",
    email="a@example.com",
    phone="+49 151 2345-678",
    about_md="# Hi",
    links=LINKS,
    address=ProfileAddress(street="Street 1", postal_code="12345", city="City"),
)
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"j" * 200
WEBP_BYTES = b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"w" * 20


@pytest.fixture()
def client(migrated_db):
    main = importlib.import_module("app.main")

    return TestClient(main.app, base_url="https://testserver")


def _unfolded(vcard: str) -> list[str]:
    return vcard.replace("\r\n ", "").split("\r\n")


def _card(**changes) -> CardContent:
    return CardContent(
        name=PROFILE.name,
        email=PROFILE.email,
        phone=PROFILE.phone,
        links=PROFILE.links,
    ).model_copy(update=changes)


# --- public routes ---------------------------------------------------------


def test_card_is_public_and_leaves_out_the_address(client) -> None:
    repository.set_profile(PROFILE)

    assert client.get("/card").json() == {
        "name": PROFILE.name,
        "email": PROFILE.email,
        "phone": PROFILE.phone,
        "links": LINKS,
    }


def test_without_profile_card_is_empty_and_vcard_404(client) -> None:
    assert client.get("/card").json() is None
    assert client.get("/card/vcard").status_code == 404


def test_vcard_download_carries_profile_and_portrait(client) -> None:
    repository.set_profile(PROFILE)
    storage.save_portrait(JPEG_BYTES)
    response = client.get("/card/vcard")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/vcard")
    assert response.headers["content-disposition"] == (
        'attachment; filename="Kontakt.vcf"'
    )

    lines = _unfolded(response.text)

    assert "FN:Alexander Wedig" in lines
    assert "TEL;TYPE=CELL:+49 151 2345-678" in lines
    assert "Street 1" not in response.text
    assert (
        "PHOTO;ENCODING=b;TYPE=JPEG:" + base64.b64encode(JPEG_BYTES).decode()
    ) in lines


# --- the vCard itself --------------------------------------------------------


def test_vcard_lists_every_field_in_order() -> None:
    assert _unfolded(build_vcard(_card(), None)) == [
        "BEGIN:VCARD",
        "VERSION:3.0",
        "N:Wedig;Alexander;;;",
        "FN:Alexander Wedig",
        "EMAIL;TYPE=INTERNET:a@example.com",
        "TEL;TYPE=CELL:+49 151 2345-678",
        "item1.URL:https://example.com",
        "item1.X-ABLabel:Website",
        "item2.URL:https://linkedin.com/in/example",
        "item2.X-ABLabel:LinkedIn",
        "item3.URL:https://github.com/example",
        "item3.X-ABLabel:GitHub",
        "END:VCARD",
        "",
    ]


def test_vcard_leaves_out_what_is_missing() -> None:
    lines = _unfolded(build_vcard(_card(phone="", links={}), WEBP_BYTES))

    assert not any(line.startswith(("TEL", "item", "PHOTO")) for line in lines)


def test_vcard_escapes_text_values() -> None:
    lines = _unfolded(build_vcard(_card(name="Ann, Jr; Doe\\X"), None))

    assert "FN:Ann\\, Jr\\; Doe\\\\X" in lines
    assert "N:Doe\\\\X;Ann\\, Jr\\;;;;" in lines


def test_vcard_drops_line_breaks_in_addresses() -> None:
    card = _card(
        phone="",
        email="a@example.com\r\nTEL:0",
        links={"github": "https://github.com/x\nPHOTO:y"},
    )
    lines = _unfolded(build_vcard(card, None))

    assert "EMAIL;TYPE=INTERNET:a@example.comTEL:0" in lines
    assert "item3.URL:https://github.com/xPHOTO:y" in lines
    assert not any(line.startswith(("TEL", "PHOTO")) for line in lines)


def test_vcard_link_labels_match_the_frontend() -> None:
    source = (REPO_ROOT / "frontend" / "lib" / "types.ts").read_text(encoding="utf-8")
    block = re.search(r"export const LINK_LABELS = \{(.*?)}", source, re.DOTALL)

    assert block is not None
    assert dict(re.findall(r'(\w+): "([^"]+)"', block.group(1))) == LINK_LABELS


def test_vcard_folds_long_lines_without_splitting_a_character() -> None:
    vcard = build_vcard(_card(name="Jürgen " + "ä" * 100), JPEG_BYTES)

    for line in vcard.split("\r\n"):
        assert len(line.encode("utf-8")) <= FOLD_AT

    assert f"FN:Jürgen {'ä' * 100}" in _unfolded(vcard)
