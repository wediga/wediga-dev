"""Reading an uploaded file under a size cap."""

from fastapi import HTTPException, UploadFile, status

_CHUNK = 64 * 1024


async def read_capped(file: UploadFile, max_bytes: int) -> bytes:
    """Read the upload in chunks, bailing at the cap so an oversized upload
    never sits whole in memory.
    """
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(_CHUNK)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="The file is too large",
            )
        chunks.append(chunk)
    return b"".join(chunks)
