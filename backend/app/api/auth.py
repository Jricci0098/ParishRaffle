from fastapi import APIRouter

from ..config import settings
from ..schemas import PinLogin
from ..services.errors import AuthError

router = APIRouter()


@router.post("/auth/login")
def login(body: PinLogin):
    """Validate a PIN and return the associated role."""
    if body.pin == settings.ADMIN_PIN:
        return {"role": "admin"}
    if body.pin == settings.VOLUNTEER_PIN:
        return {"role": "volunteer"}
    raise AuthError("Incorrect PIN")


@router.get("/config")
def public_config():
    """Non-sensitive configuration for the frontend."""
    return {
        "app_name": settings.APP_NAME,
        "demo_mode": settings.DEMO_MODE,
        "display_rotation_seconds": settings.DISPLAY_ROTATION_SECONDS,
        "new_winner_highlight_seconds": settings.NEW_WINNER_HIGHLIGHT_SECONDS,
        "winners_per_page": settings.WINNERS_PER_PAGE,
        "allow_repeat_ticket_winners": settings.ALLOW_REPEAT_TICKET_WINNERS,
    }
