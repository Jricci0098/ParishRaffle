from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..schemas import ConfirmWinner, LookupRequest
from ..services import draws as draws_service
from ..services.errors import AuthError
from ..websocket import manager

router = APIRouter()


@router.post("/draws/lookup")
def lookup(body: LookupRequest, db: Session = Depends(get_db)):
    """Validate a ticket for drawing without changing anything."""
    return draws_service.lookup(db, body.ticket_number)


@router.post("/draws")
def confirm_winner(
    body: ConfirmWinner,
    db: Session = Depends(get_db),
    x_admin_pin: str | None = Header(default=None),
):
    """Confirm a winning ticket for a prize.

    Overrides (unsold ticket, already-won, manual off-list winner) require the
    admin PIN.
    """
    needs_admin = (
        body.allow_unsold
        or body.allow_already_won
        or bool(body.manual_first_name or body.manual_last_name)
    )
    if needs_admin and x_admin_pin != settings.ADMIN_PIN:
        raise AuthError("Admin authorisation required for override")

    prize = draws_service.confirm_winner(
        db,
        prize_id=body.prize_id,
        ticket_number=body.ticket_number,
        allow_unsold=body.allow_unsold,
        allow_already_won=body.allow_already_won,
        manual_first_name=body.manual_first_name,
        manual_last_name=body.manual_last_name,
        device=body.device,
    )
    view = draws_service.prize_public_view(db, prize)
    manager.broadcast_sync("winner.created", view)
    return view
