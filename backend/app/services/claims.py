"""Prize pickup / claim tracking and winner search."""
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..models import Buyer, Claim, Prize, Ticket
from ..models import prize as prize_model
from . import audit
from .draws import prize_public_view
from .errors import NotFoundError, DuplicateError
from .tickets import find_ticket


def search_winners(db: Session, query: str) -> list[dict]:
    """Search drawn prizes by ticket number, winner name, or prize number."""
    query = (query or "").strip()
    results: list[Prize] = []

    drawn = (
        db.query(Prize)
        .filter(Prize.winning_ticket_id.isnot(None))
        .order_by(Prize.prize_number)
        .all()
    )

    if not query:
        results = drawn
    else:
        lowered = query.lower()
        # Prize number match.
        prize_num = None
        cleaned = query.lstrip("#")
        if cleaned.isdigit():
            prize_num = int(cleaned)

        ticket = find_ticket(db, query)
        for p in drawn:
            buyer = db.get(Buyer, p.winner_id) if p.winner_id else None
            t = db.get(Ticket, p.winning_ticket_id)
            match = False
            if prize_num is not None and p.prize_number == prize_num:
                match = True
            if buyer and lowered in buyer.display_name.lower():
                match = True
            if t and ticket and t.id == ticket.id:
                match = True
            if t and lowered in t.ticket_number.lower():
                match = True
            if match:
                results.append(p)

    return [prize_public_view(db, p) for p in results]


def claim_prize(
    db: Session,
    prize_id: int,
    verified_by: str = "volunteer",
    device: str | None = None,
    notes: str = "",
) -> Prize:
    """Mark a drawn prize as picked up / claimed."""
    prize = db.get(Prize, prize_id)
    if prize is None:
        raise NotFoundError(f"Prize {prize_id} not found")
    if prize.winning_ticket_id is None:
        raise DuplicateError(
            "Prize has no confirmed winner yet.", code="not_drawn"
        )
    if prize.status == prize_model.STATUS_CLAIMED:
        raise DuplicateError(
            "Prize has already been claimed.", code="already_claimed"
        )

    claim = Claim(
        prize_id=prize.id,
        ticket_id=prize.winning_ticket_id,
        buyer_id=prize.winner_id,
        verified_by=verified_by,
        notes=notes,
        claimed_at=datetime.utcnow(),
    )
    db.add(claim)

    prize.status = prize_model.STATUS_CLAIMED
    ticket = db.get(Ticket, prize.winning_ticket_id)
    if ticket is not None:
        ticket.claimed = True

    buyer = db.get(Buyer, prize.winner_id) if prize.winner_id else None
    audit.log(
        db,
        "prize.claimed",
        details=(
            f"Prize #{prize.prize_number} claimed by "
            f"{buyer.display_name if buyer else '?'} (verified by {verified_by})"
        ),
        device=device,
        role=verified_by,
    )
    db.commit()
    db.refresh(prize)
    return prize
