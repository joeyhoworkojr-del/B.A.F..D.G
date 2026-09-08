"""
Profile photos.

Stored as bytes in the document store and served from their own endpoint,
rather than inlined into every API response. A leaderboard of fifty analysts
would otherwise carry fifty base64 images — several megabytes of JSON to render
a page of names.

Uploads are cropped and resized in the browser before they arrive, so what
lands here is already a small square. This module's job is to refuse anything
that is not: the declared content type is ignored in favour of the file's own
magic bytes, because a caller controls the former and not the latter.

There is deliberately no image processing on the server. Decoding arbitrary
user-supplied images is a large attack surface for a feature whose entire
requirement is "a small square picture", and the browser has already done it.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
from dataclasses import dataclass
from typing import Optional

from src.store.documents import get_docs

COLLECTION = "avatars"

# A 256x256 JPEG lands around 20-40 KB. The cap leaves room for a PNG with
# transparency without letting anyone park a megabyte in the row store.
MAX_BYTES = 400 * 1024

# Only formats every browser renders, and none that can carry script. SVG is
# excluded on purpose: it is a document, it can contain script, and serving one
# from our own origin would be a stored-XSS hole.
_MAGIC: tuple[tuple[bytes, str], ...] = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
)
_WEBP_PREFIX = b"RIFF"
_WEBP_TAG = b"WEBP"


class InvalidImage(ValueError):
    """Rejected with a reason the upload form can display."""


@dataclass
class Avatar:
    user_id: str
    content_type: str
    data: bytes
    etag: str

    @property
    def size(self) -> int:
        return len(self.data)


def sniff_content_type(data: bytes) -> Optional[str]:
    """
    The image format, read from the bytes themselves.

    A declared content type is caller-controlled and therefore worthless as a
    safety check; the file's own header is not.
    """
    for magic, mime in _MAGIC:
        if data.startswith(magic):
            return mime
    if len(data) >= 12 and data.startswith(_WEBP_PREFIX) and data[8:12] == _WEBP_TAG:
        return "image/webp"
    return None


def decode_upload(data_url_or_b64: str) -> tuple[bytes, str]:
    """
    Turn what the browser sent into validated bytes.

    Accepts a bare base64 payload or a full `data:` URL, since a canvas gives
    the latter and it is friendlier than making the client strip it.
    """
    raw = (data_url_or_b64 or "").strip()
    if not raw:
        raise InvalidImage("No image was uploaded.")
    if raw.startswith("data:"):
        _, _, tail = raw.partition(",")
        raw = tail
    # Reject before decoding: base64 is 4/3 the size of what it encodes, so
    # this bounds the work done on an oversized payload.
    if len(raw) > MAX_BYTES * 4 // 3 + 1024:
        raise InvalidImage(f"Image is too large. The limit is {MAX_BYTES // 1024} KB.")
    try:
        data = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise InvalidImage("That upload could not be read as an image.") from exc

    if not data:
        raise InvalidImage("No image was uploaded.")
    if len(data) > MAX_BYTES:
        raise InvalidImage(f"Image is too large. The limit is {MAX_BYTES // 1024} KB.")

    content_type = sniff_content_type(data)
    if content_type is None:
        raise InvalidImage("Only JPEG, PNG, GIF and WebP images are supported.")
    return data, content_type


def save(user_id: str, data_url_or_b64: str) -> Avatar:
    """Validate and store one user's photo, replacing any previous one."""
    data, content_type = decode_upload(data_url_or_b64)
    etag = hashlib.sha256(data).hexdigest()[:32]
    get_docs().put(COLLECTION, user_id, {
        "user_id": user_id,
        "content_type": content_type,
        "data": base64.b64encode(data).decode("ascii"),
        "etag": etag,
    })
    return Avatar(user_id=user_id, content_type=content_type, data=data, etag=etag)


def load(user_id: str) -> Optional[Avatar]:
    """One user's photo, or None. Never raises on a malformed stored row."""
    doc = get_docs().get(COLLECTION, user_id)
    if not doc:
        return None
    try:
        data = base64.b64decode(doc.get("data") or "", validate=True)
    except (binascii.Error, ValueError):
        return None
    if not data:
        return None
    # Re-sniff on the way out: a row written by an older, laxer version must not
    # be served as whatever it claims to be.
    content_type = sniff_content_type(data)
    if content_type is None:
        return None
    return Avatar(
        user_id=user_id,
        content_type=content_type,
        data=data,
        etag=doc.get("etag") or hashlib.sha256(data).hexdigest()[:32],
    )


def remove(user_id: str) -> None:
    get_docs().delete(COLLECTION, user_id)


def url_for(user_id: str, etag: str = "") -> str:
    """
    Where the photo is served from.

    The etag rides along as a query parameter so a new upload busts any cached
    copy immediately, rather than leaving the old face on screen until a
    cache expires.
    """
    suffix = f"?v={etag[:12]}" if etag else ""
    return f"/api/v1/avatars/{user_id}{suffix}"
