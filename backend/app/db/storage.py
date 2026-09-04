"""Supabase Storage client for original resume PDF objects.

Uses the Storage REST API directly over httpx (already a dependency) rather than the
full supabase-py SDK, to avoid pulling in its heavier transitive dependency set for
what is, here, a single upload operation against a private bucket.
"""

from __future__ import annotations

import logging

import httpx

from app.core.config import SUPABASE_RESUME_BUCKET, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL


logger = logging.getLogger(__name__)


class StorageUploadError(Exception):
    """Raised when a resume PDF cannot be stored in Supabase Storage."""


class StorageNotConfiguredError(StorageUploadError):
    """Raised when this deployment has no Supabase Storage credentials at all.

    Separate from a failed upload: nothing is wrong upstream, the server is
    simply missing configuration, and the caller cannot fix that by retrying.
    """


def is_configured() -> bool:
    """Whether resume PDFs can be stored at all in this environment."""
    return bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)


def resume_storage_path(candidate_id: str, resume_id: str) -> str:
    """Build the deterministic, collision-free object path for one resume's PDF.

    Keyed by candidate_id and resume_id (both server-generated UUIDs, never
    client-supplied filenames), so the path can never collide or be manipulated.
    """
    return f"{candidate_id}/{resume_id}.pdf"


def upload_resume_pdf(path: str, pdf_bytes: bytes) -> None:
    """Upload a resume PDF to the private Supabase Storage bucket.

    Raises StorageUploadError if Storage is not configured or the upload fails,
    so the caller can avoid persisting a resume record for a file that was never
    actually stored.
    """
    if not is_configured():
        raise StorageNotConfiguredError(
            "Supabase Storage is not configured: set SUPABASE_URL and "
            "SUPABASE_SERVICE_ROLE_KEY."
        )

    url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_RESUME_BUCKET}/{path}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Content-Type": "application/pdf",
        "x-upsert": "false",
    }

    try:
        response = httpx.post(url, headers=headers, content=pdf_bytes, timeout=30)
    except httpx.HTTPError as exc:
        raise StorageUploadError(f"Failed to reach Supabase Storage: {exc}") from exc

    if response.status_code >= 400:
        raise StorageUploadError(
            f"Supabase Storage upload failed with status {response.status_code}"
        )


def delete_resume_pdf(path: str) -> bool:
    """Best-effort removal of a stored resume PDF. Returns whether it was deleted.

    Used to compensate when the database write that should have recorded an
    upload fails: the object is already in the bucket at that point, and without
    this it would be orphaned with no row referencing it.

    Deliberately never raises. It runs while another exception is propagating,
    and a failure to clean up must not replace the error that caused it -- the
    worst case is the orphan that would have been left anyway.
    """
    if not is_configured():
        return False

    url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_RESUME_BUCKET}/{path}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
    }

    try:
        response = httpx.delete(url, headers=headers, timeout=15)
    except httpx.HTTPError as exc:
        logger.warning("Could not remove orphaned resume object %s: %s", path, exc)
        return False

    if response.status_code >= 400:
        logger.warning(
            "Could not remove orphaned resume object %s: storage returned %s",
            path,
            response.status_code,
        )
        return False
    return True
