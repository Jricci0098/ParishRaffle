"""Ticket helpers shared across services."""
from sqlalchemy.orm import Session

from ..models import Ticket


def format_ticket(number: int, width: int = 6) -> str:
    """Zero-pad a ticket number to preserve leading zeros."""
    return str(number).zfill(width)


def normalize_ticket_input(raw: str) -> str:
    """Normalise scanner / keyboard input into a stored ticket number.

    Strips surrounding whitespace. Leading zeros are preserved. If a plain
    integer is entered we keep it as typed so both "5142" and "005142" can be
    matched by the lookup fallback.
    """
    return (raw or "").strip()


def find_ticket(db: Session, ticket_number: str) -> Ticket | None:
    """Look up a ticket, tolerant of leading-zero differences."""
    ticket_number = normalize_ticket_input(ticket_number)
    if not ticket_number:
        return None
    ticket = (
        db.query(Ticket)
        .filter(Ticket.ticket_number == ticket_number)
        .first()
    )
    if ticket is not None:
        return ticket
    # Fallback: match ignoring leading zeros (e.g. "5142" -> "005142").
    if ticket_number.isdigit():
        stripped = ticket_number.lstrip("0") or "0"
        for candidate in db.query(Ticket).all():
            cand = candidate.ticket_number
            if cand.isdigit() and (cand.lstrip("0") or "0") == stripped:
                return candidate
    return None
