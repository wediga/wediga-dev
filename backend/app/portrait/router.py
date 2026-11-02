"""Portrait routes: admin upload and crop, public image and crop.

The upload is the attack surface, so an image is accepted only when the
declared type of its multipart part matches the type its first bytes show,
and the size is capped while reading. The type is not stored, it is read from
the bytes again when the image is served.
"""

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status

from app.auth.csrf import require_csrf
from app.auth.dependencies import require_admin
from app.errors import not_found
from app.portrait import storage
from app.portrait.schemas import PortraitCrop
from app.uploads import read_capped

router = APIRouter(prefix="/portrait", tags=["portrait"])

WRITE_DEPS = [Depends(require_admin), Depends(require_csrf)]

# A portrait for a page and a contact card, 5 MB caps a hostile upload.
MAX_IMAGE_BYTES = 5 * 1024 * 1024
NO_PORTRAIT = "No portrait uploaded yet"

JPEG = "image/jpeg"
PNG = "image/png"
WEBP = "image/webp"
ACCEPTED_TYPES = (JPEG, PNG, WEBP)
JPEG_SIGNATURE = b"\xff\xd8\xff"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
# A WebP file is a RIFF container: "RIFF", four bytes of length, then "WEBP".
RIFF_SIGNATURE = b"RIFF"
WEBP_MARK = b"WEBP"
WEBP_MARK_AT = slice(8, 12)


def image_type(data: bytes) -> str | None:
    """The media type the first bytes show, or None for anything else."""
    if data.startswith(JPEG_SIGNATURE):
        return JPEG

    if data.startswith(PNG_SIGNATURE):
        return PNG

    if data.startswith(RIFF_SIGNATURE) and data[WEBP_MARK_AT] == WEBP_MARK:
        return WEBP

    return None


# --- public reads ---------------------------------------------------------


@router.get("")
def read_portrait() -> Response:
    content = storage.load_portrait()

    if content is None:
        raise not_found(NO_PORTRAIT)

    return Response(
        content,
        media_type=image_type(content),
        headers={
            # Revalidated on every view, so a new upload shows at once.
            "Cache-Control": "no-cache",
            # nosniff plus the signature check stops a polyglot upload being
            # sniffed as HTML.
            "X-Content-Type-Options": "nosniff",
            # The image loads no resources of its own.
            "Content-Security-Policy": "default-src 'none'",
        },
    )


@router.get("/crop")
def read_crop() -> PortraitCrop | None:
    return storage.load_crop()


# --- admin writes ---------------------------------------------------------


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=WRITE_DEPS)
async def upload_portrait(file: UploadFile) -> PortraitCrop:
    """Replace the stored portrait. JPEG, PNG or WebP only, size-capped."""
    if file.content_type not in ACCEPTED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only JPEG, PNG or WebP is accepted",
        )

    data = await read_capped(file, MAX_IMAGE_BYTES)

    if image_type(data) != file.content_type:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The file is not the image it claims to be",
        )

    return storage.save_portrait(data)


@router.put("/crop", dependencies=WRITE_DEPS)
def write_crop(body: PortraitCrop) -> PortraitCrop:
    if not storage.save_crop(body):
        raise not_found(NO_PORTRAIT)

    return body
