"""Shared API dependencies: DB session and PIN-based authorisation."""
from fastapi import Header

from ..config import settings
from ..database import get_db
from ..security import pin_matches
from ..services.errors import AuthError

__all__ = ["get_db", "require_admin", "require_write_access"]


def require_admin(x_admin_pin: str | None = Header(default=None)) -> str:
    """Require the admin PIN in the ``X-Admin-Pin`` header (constant-time)."""
    if not pin_matches(x_admin_pin, settings.ADMIN_PIN):
        raise AuthError("Admin authorisation required")
    return "admin"


def require_write_access(
    x_pin: str | None = Header(default=None),
    x_admin_pin: str | None = Header(default=None),
) -> str:
    """Gate the volunteer write endpoints (sale / draw / claim).

    A no-op when ``REQUIRE_PIN_FOR_WRITES`` is off (the trusted-LAN default).
    When on, the volunteer PIN (``X-Pin``) or the admin PIN (``X-Pin`` or
    ``X-Admin-Pin``) is required — see the README security model.
    """
    if not settings.REQUIRE_PIN_FOR_WRITES:
        return "open"
    if (
        pin_matches(x_pin, settings.VOLUNTEER_PIN)
        or pin_matches(x_pin, settings.ADMIN_PIN)
        or pin_matches(x_admin_pin, settings.ADMIN_PIN)
    ):
        return "authorised"
    raise AuthError("A PIN is required to record changes on this deployment")
