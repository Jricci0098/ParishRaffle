from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Prize
from ..models import prize as prize_model
from ..schemas import ClaimRequest, RedrawRequest
from ..services import claims as claims_service
from ..services import draws as draws_service
from ..websocket import manager
from .deps import require_admin

router = APIRouter()


@router.get("/winners")
def winners(session: int | None = None, db: Session = Depends(get_db)):
    q = db.query(Prize).filter(Prize.winning_ticket_id.isnot(None))
    if session is not None:
        q = q.filter(Prize.session_number == session)
    prizes = q.order_by(Prize.prize_number).all()
    return [draws_service.prize_public_view(db, p) for p in prizes]


@router.get("/winners/unclaimed")
def unclaimed(db: Session = Depends(get_db)):
    prizes = (
        db.query(Prize)
        .filter(
            Prize.winning_ticket_id.isnot(None),
            Prize.status != prize_model.STATUS_CLAIMED,
        )
        .order_by(Prize.prize_number)
        .all()
    )
    return [draws_service.prize_public_view(db, p) for p in prizes]


@router.get("/winners/search")
def search(q: str = "", db: Session = Depends(get_db)):
    return claims_service.search_winners(db, q)


@router.post("/prizes/{prize_id}/claim")
def claim(
    prize_id: int,
    body: ClaimRequest,
    db: Session = Depends(get_db),
):
    prize = claims_service.claim_prize(
        db,
        prize_id,
        verified_by=body.verified_by,
        device=body.device,
        notes=body.notes,
    )
    view = draws_service.prize_public_view(db, prize)
    manager.broadcast_sync("prize.claimed", view)
    return view


@router.post("/prizes/{prize_id}/redraw")
def redraw(
    prize_id: int,
    body: RedrawRequest,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    prize = draws_service.redraw(db, prize_id, reason=body.reason)
    view = draws_service.prize_public_view(db, prize)
    manager.broadcast_sync("winner.redrawn", view)
    return view
