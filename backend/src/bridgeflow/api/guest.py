"""Boundaries for the shared, sample-only guest instance."""

from fastapi import HTTPException

from bridgeflow.config import settings


def require_user_file_uploads() -> None:
    """Refuse visitor files before parsing or saving them in the shared guest store."""
    if settings.bridgeflow_guest_mode:
        raise HTTPException(403, "Guest mode accepts built-in samples only; file uploads are unavailable")
