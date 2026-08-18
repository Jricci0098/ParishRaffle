"""Drawing console: prize navigation, ticket lookup, winner confirmation,
redraw. All winner history is preserved as ``Draw`` rows."""
from datetime import datetime

from sqlalchemy.orm import Session

from ..config import settings
from ..models import Buyer, Draw, Prize, Ticket
from ..models.draw import DRAW_VALID, DRAW_VOID
from ..models import prize as prize_model
from . import audit, state
from .errors import (
    NotFoundError,
    TicketAlreadyWonError,
    TicketUnknownError,
    TicketUnsoldError,
)
from .tickets import find_ticket, format_ticket


def _prize_query(db: Session, session_number: int | None):
    q = db.query(Prize)
    if session_number is not None:
        q = q.filter(Prize.session_number == session_number)
    return q.order_by(Prize.sort_order, Prize.prize_number)


def current_prize(db: Session) -> Prize | None:
    """The next prize that still needs to be drawn in the current session."""
    session_number = int(state.get(db, "current_session", "1"))
    prize = (
        _prize_query(db, session_number)
        .filter(
            Prize.status.in_(
                [
                    prize_model.STATUS_AVAILABLE,
                    prize_model.STATUS_REDRAW_REQUIRED,
                ]
            )
        )
        .first()
    )
    if prize is not None:
        return prize
    # Fall back to the first prize in the session (all already drawn).
    return _prize_query(db, session_number).first()


def prize_at_offset(db: Session, prize_id: int, offset: int) -> Prize | None:
    """Return the previous/next prize relative to ``prize_id``."""
    prize = db.get(Prize, prize_id)
    session_number = prize.session_number if prize else None
    ordered = _prize_query(db, session_number).all()
    ids = [p.id for p in ordered]
    if prize_id not in ids:
        return ordered[0] if ordered else None
    idx = ids.index(prize_id) + offset
    if 0 <= idx < len(ordered):
        return ordered[idx]
    return None


def lookup(db: Session, ticket_number: str) -> dict:
    """Validate a ticket for drawing without mutating anything.

    Returns a dict with a ``status`` field:
        ok | unknown | unsold | already_won
    """
    ticket = find_ticket(db, ticket_number)
    if ticket is None:
        return {"status": "unknown", "ticket_number": ticket_number}

    buyer = db.get(Buyer, ticket.buyer_id) if ticket.buyer_id else None
    result = {
        "ticket_number": ticket.ticket_number,
        "ticket_id": ticket.id,
        "sold": ticket.sold,
        "buyer": {
            "id": buyer.id if buyer else None,
            "display_name": buyer.display_name if buyer else "(no buyer)",
        },
    }

    if not ticket.sold:
        result["status"] = "unsold"
        return result

    if ticket.winning:
        won_prize = (
            db.query(Prize)
            .filter(Prize.winning_ticket_id == ticket.id)
            .first()
        )
        result["status"] = "already_won"
        result["won_prize_number"] = won_prize.prize_number if won_prize else None
        result["won_prize_name"] = won_prize.name if won_prize else None
        return result

    result["status"] = "ok"
    return result


def confirm_winner(
    db: Session,
    prize_id: int,
    ticket_number: str,
    *,
    allow_unsold: bool = False,
    allow_already_won: bool = False,
    manual_first_name: str | None = None,
    manual_last_name: str | None = None,
    device: str | None = None,
    role: str = "volunteer",
) -> Prize:
    """Assign a winning ticket to a prize.

    ``manual_*`` names create an off-list buyer/ticket when an unregistered
    ticket must be recorded as the winner (requires admin authorisation at the
    API layer).
    """
    prize = db.get(Prize, prize_id)
    if prize is None:
        raise NotFoundError(f"Prize {prize_id} not found")

    ticket = find_ticket(db, ticket_number)

    if ticket is None:
        if not (manual_first_name or manual_last_name):
            raise TicketUnknownError(
                f"Ticket {ticket_number} is not registered."
            )
        # Manual winner: create a buyer and a ticket record.
        buyer = Buyer(
            first_name=(manual_first_name or "").strip(),
            last_name=(manual_last_name or "").strip(),
            display_name=" ".join(
                p
                for p in [
                    (manual_first_name or "").strip(),
                    (manual_last_name or "").strip(),
                ]
                if p
            )
            or "Manual Winner",
        )
        db.add(buyer)
        db.flush()
        ticket = Ticket(
            ticket_number=ticket_number.strip(),
            buyer_id=buyer.id,
            sold=True,
            sold_at=datetime.utcnow(),
            notes="Created via manual winner entry",
        )
        db.add(ticket)
        db.flush()

    if not ticket.sold and not allow_unsold:
        raise TicketUnsoldError(
            f"WARNING: Ticket {ticket.ticket_number} was not recorded as sold."
        )

    if ticket.winning:
        repeat_ok = settings.ALLOW_REPEAT_TICKET_WINNERS or allow_already_won
        if not repeat_ok:
            won_prize = (
                db.query(Prize)
                .filter(Prize.winning_ticket_id == ticket.id)
                .first()
            )
            pnum = won_prize.prize_number if won_prize else "?"
            raise TicketAlreadyWonError(
                f"Ticket {ticket.ticket_number} has already won Prize #{pnum}."
            )

    # If this prize had a prior voided draw, link the new one as a redraw.
    prior_void = (
        db.query(Draw)
        .filter(Draw.prize_id == prize.id, Draw.status == DRAW_VOID)
        .order_by(Draw.drawn_at.desc())
        .first()
    )

    draw = Draw(
        prize_id=prize.id,
        ticket_id=ticket.id,
        buyer_id=ticket.buyer_id,
        status=DRAW_VALID,
        drawn_at=datetime.utcnow(),
        redraw_of=prior_void.id if prior_void else None,
    )
    db.add(draw)

    ticket.winning = True
    prize.winning_ticket_id = ticket.id
    prize.winner_id = ticket.buyer_id
    prize.status = prize_model.STATUS_DRAWN

    buyer = db.get(Buyer, ticket.buyer_id) if ticket.buyer_id else None
    audit.log(
        db,
        "winner.confirmed",
        details=(
            f"Prize #{prize.prize_number} '{prize.name}' won by "
            f"{buyer.display_name if buyer else '?'} "
            f"(ticket {ticket.ticket_number})"
        ),
        device=device,
        role=role,
    )
    db.commit()
    db.refresh(prize)
    return prize


def redraw(
    db: Session, prize_id: int, reason: str = "", device: str | None = None
) -> Prize:
    """Void the current winner and reset the prize so it can be drawn again.

    The previous draw is preserved with status VOID; the winning flag on the
    old ticket is cleared unless it won another prize.
    """
    prize = db.get(Prize, prize_id)
    if prize is None:
        raise NotFoundError(f"Prize {prize_id} not found")

    valid_draw = (
        db.query(Draw)
        .filter(Draw.prize_id == prize.id, Draw.status == DRAW_VALID)
        .order_by(Draw.drawn_at.desc())
        .first()
    )
    if valid_draw is not None:
        valid_draw.status = DRAW_VOID
        valid_draw.notes = (valid_draw.notes or "") + f" [redraw: {reason}]"

    old_ticket = (
        db.get(Ticket, prize.winning_ticket_id)
        if prize.winning_ticket_id
        else None
    )
    if old_ticket is not None:
        other_win = (
            db.query(Prize)
            .filter(
                Prize.winning_ticket_id == old_ticket.id,
                Prize.id != prize.id,
            )
            .first()
        )
        if other_win is None:
            old_ticket.winning = False

    prize.winning_ticket_id = None
    prize.winner_id = None
    prize.status = prize_model.STATUS_REDRAW_REQUIRED

    audit.log(
        db,
        "winner.redrawn",
        details=f"Prize #{prize.prize_number} sent for redraw. {reason}",
        device=device,
        role="admin",
    )
    db.commit()
    db.refresh(prize)
    return prize


def prize_public_view(db: Session, prize: Prize) -> dict:
    """Serialise a prize for the drawing console / display."""
    buyer = db.get(Buyer, prize.winner_id) if prize.winner_id else None
    ticket = (
        db.get(Ticket, prize.winning_ticket_id)
        if prize.winning_ticket_id
        else None
    )
    return {
        "id": prize.id,
        "prize_number": prize.prize_number,
        "name": prize.name,
        "description": prize.description,
        "session_number": prize.session_number,
        "pickup_station": prize.pickup_station,
        "status": prize.status,
        "winner_name": buyer.display_name if buyer else None,
        "winning_ticket": ticket.ticket_number if ticket else None,
        "claimed": prize.status == prize_model.STATUS_CLAIMED,
    }
