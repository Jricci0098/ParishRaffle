"""Shared API dependencies: DB session and PIN-based authorisation."""
from fastapi import Header

from ..config import settings
from ..database import get_db
from ..services.errors import AuthError

__all__ = ["get_db", "require_admin", "require_volunteer"]


def require_admin(x_admin_pin: str | None = Header(default=None)) -> str:
    """Require the admin PIN in the ``X-Admin-Pin`` header."""
    if not x_admin_pin or x_admin_pin != settings.ADMIN_PIN:
        raise AuthError("Admin authorisation required")
    return "admin"


def require_volunteer(x_pin: str | None = Header(default=None)) -> str:
    """Require the volunteer or admin PIN in the ``X-Pin`` header.

    Volunteer screens are used on a trusted local network, so this is a light
    guard rather than real security.
    """
    if x_pin in (settings.VOLUNTEER_PIN, settings.ADMIN_PIN):
        return "volunteer"
    raise AuthError("Volunteer authorisation required")
