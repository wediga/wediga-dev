"""CV routes: admin PDF upload and recruiter-gated download.

The CV is a single uploaded PDF. The admin replaces it through a multipart
upload behind ``require_admin`` for the session and ``require_csrf`` for the
synchronizer token, so a write without a session is 401 and one without a valid
token is 403. The recruiter downloads it behind ``require_recruiter_view``,
which an admin session also satisfies and which re-checks the link state on
every read, so a revoked or expired link loses access. A status endpoint
reports whether a PDF is present, used by the admin page and the recruiter view.

The upload is the real attack surface, so a file is accepted only when its
multipart part declares ``application/pdf`` and its bytes start with the
``%PDF-`` signature, and the size is capped while reading so an oversized body
never buffers whole. Stored under a fixed name, a client filename never reaches
the path.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.auth.csrf import require_csrf
from app.auth.dependencies import require_admin
from app.cv import storage
from app.errors import not_found
from app.recruiter.dependencies import require_recruiter_view

router = APIRouter(prefix="/cv", tags=["cv"])

WRITE_DEPS = [Depends(require_admin), Depends(require_csrf)]
RECRUITER_READ_DEPS = [Depends(require_recruiter_view)]

# A CV PDF is small; 10 MB is generous and caps a hostile upload.
MAX_PDF_BYTES = 10 * 1024 * 1024
_CHUNK = 64 * 1024
PDF_SIGNATURE = b"%PDF-"
# Neutral download name, so no personal data lives in committed code.
DOWNLOAD_FILENAME = "Lebenslauf.pdf"


# --- recruiter-gated reads ----------------------------------------------


@router.get("/status", dependencies=RECRUITER_READ_DEPS)
def cv_status() -> dict[str, bool]:
    """Report whether a CV PDF is currently stored."""
    return {"present": storage.has_cv()}


@router.get("/download", dependencies=RECRUITER_READ_DEPS)
def download_cv(inline: bool = False) -> FileResponse:
    """Return the stored CV PDF.

    By default it is sent as an attachment for the download link. With
    ``inline=true`` it is sent inline so the CV page can embed it in a preview
    pane instead of forcing a download.
    """
    path = storage.cv_path()
    if not path.is_file():
        raise not_found("No CV uploaded yet")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=DOWNLOAD_FILENAME,
        content_disposition_type="inline" if inline else "attachment",
        headers={
            # Gated personal content must not be kept in a shared cache.
            "Cache-Control": "private, no-store",
            # Pin the type so a polyglot upload is never sniffed as HTML, which
            # together with the %PDF signature check closes any inline-XSS path.
            "X-Content-Type-Options": "nosniff",
            # The PDF needs no resources of its own, so lock it all down.
            "Content-Security-Policy": "default-src 'none'",
        },
    )


# --- admin write --------------------------------------------------------


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=WRITE_DEPS)
async def upload_cv(file: UploadFile) -> dict[str, bool]:
    """Replace the stored CV PDF. PDF only, size-capped, fixed storage name."""
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only application/pdf is accepted",
        )
    data = await _read_capped(file)
    if not data.startswith(PDF_SIGNATURE):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The file is not a PDF",
        )
    storage.save_cv(data)
    return {"present": True}


async def _read_capped(file: UploadFile) -> bytes:
    """Read the upload in chunks, rejecting anything past the size cap.

    Reading in blocks and bailing at the cap means an oversized upload never
    sits whole in memory.
    """
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(_CHUNK)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_PDF_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="The file is too large",
            )
        chunks.append(chunk)
    return b"".join(chunks)
