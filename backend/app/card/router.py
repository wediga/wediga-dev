"""Card routes: the public contact card for /hi and its vCard download."""

from fastapi import APIRouter, Response

from app.card.schemas import CardContent
from app.card.vcard import build_vcard
from app.content import repository
from app.errors import not_found
from app.portrait import storage

router = APIRouter(prefix="/card", tags=["card"])

# Neutral name, so no personal data lives in committed code.
VCARD_FILENAME = "Kontakt.vcf"


def _card() -> CardContent | None:
    profile = repository.get_profile()

    if profile is None:
        return None

    return CardContent(
        name=profile.name, email=profile.email, phone=profile.phone, links=profile.links
    )


@router.get("")
def read_card() -> CardContent | None:
    return _card()


@router.get("/vcard")
def download_vcard() -> Response:
    card = _card()

    if card is None:
        raise not_found("No profile yet")

    return Response(
        build_vcard(card, storage.load_portrait()),
        media_type="text/vcard",
        headers={
            "Content-Disposition": f'attachment; filename="{VCARD_FILENAME}"',
            "Cache-Control": "no-cache",
            "X-Content-Type-Options": "nosniff",
        },
    )
