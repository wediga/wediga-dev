"""The public contact card: name, email, phone and links, never the address."""

from app.content.schemas import ContactContent


class CardContent(ContactContent):
    phone: str
