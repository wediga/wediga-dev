"""TOTP second factor for the admin login.

The admin secret is generated with :mod:`pyotp`, encrypted at rest with Fernet
from :mod:`cryptography` and turned into an ``otpauth`` URI plus an SVG QR code
for setup. The encryption key comes from the ``TOTP_ENC_KEY`` environment
variable and never ships in the repository; an unset key fails the setup and
verify paths cleanly instead of falling back to a predictable default.

The verify step uses pyotp's constant-time comparison and a one-step window, so
a small clock drift between the server and the authenticator app does not lock
out a valid code.
"""

import base64
import io
import os

import pyotp
import qrcode
from cryptography.fernet import Fernet, InvalidToken
from qrcode.image.svg import SvgPathFillImage

# One step before and after the current 30-second window is accepted, which
# covers clock drift without widening the guess space beyond three codes.
_VALID_WINDOW = 1

# Shown to the admin in the authenticator app entry and in the otpauth URI.
_ISSUER = "wediga.dev"
_ACCOUNT = "admin"


class TotpKeyError(RuntimeError):
    """Raised when ``TOTP_ENC_KEY`` is missing or not a valid Fernet key."""


def _fernet() -> Fernet:
    """Build the Fernet cipher from ``TOTP_ENC_KEY``.

    A missing or malformed key raises :class:`TotpKeyError`, so a
    misconfiguration surfaces as a handled error rather than a silent fallback
    to an insecure default.
    """
    key = os.environ.get("TOTP_ENC_KEY")
    if not key:
        raise TotpKeyError("TOTP_ENC_KEY is not set")
    try:
        return Fernet(key.encode("utf-8"))
    except (ValueError, TypeError) as exc:
        raise TotpKeyError("TOTP_ENC_KEY is not a valid Fernet key") from exc


def generate_secret() -> str:
    """Return a fresh base32 TOTP secret (160 bits of entropy)."""
    return pyotp.random_base32()


def encrypt_secret(secret: str) -> str:
    """Encrypt a plaintext secret for storage, returned as text."""
    return _fernet().encrypt(secret.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str) -> str:
    """Decrypt a stored secret.

    A tampered or wrongly keyed value raises :class:`TotpKeyError`, which the
    caller treats as a failed second factor rather than a server error.
    """
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise TotpKeyError("stored TOTP secret could not be decrypted") from exc


def provisioning_uri(secret: str) -> str:
    """Build the ``otpauth://`` URI for the authenticator app."""
    return pyotp.TOTP(secret).provisioning_uri(name=_ACCOUNT, issuer_name=_ISSUER)


def verify_code(secret: str, code: str) -> bool:
    """Return whether ``code`` is valid for ``secret`` within the drift window.

    pyotp compares in constant time. An empty code is rejected outright and any
    value that does not match, including a non-numeric one, returns ``False``
    instead of raising.
    """
    if not code:
        return False
    return pyotp.TOTP(secret).verify(code, valid_window=_VALID_WINDOW)


def qr_svg_data_url(uri: str) -> str:
    """Render ``uri`` as an SVG QR code returned as a ``data:`` URL.

    The SVG path factory needs no Pillow, so the image carries no raster
    dependency and the frontend only displays the returned string in an
    ``<img>`` tag. The fill variant paints a white background rect, so the code
    stays scannable on the dark admin surface where a transparent SVG would not.
    """
    image = qrcode.make(uri, image_factory=SvgPathFillImage)
    buffer = io.BytesIO()
    image.save(buffer)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"
