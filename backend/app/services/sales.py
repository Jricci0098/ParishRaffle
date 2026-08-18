"""Ticket sales: sequential assignment, range enforcement, undo, imports.

Concurrency: each station owns a disjoint ticket range and its own
``next_ticket_number``. A sale locks the station row for update (real row lock
on PostgreSQL; on SQLite the write serialisation plus the unique constraint on
``ticket_number`` guarantee no overlapping assignments). The whole sale runs in
a single transaction so a failure rolls back cleanly.
"""
import json
import threading
from datetime import datetime

from sqlalchemy.orm import Session

from ..models import Buyer, SaleStation, Ticket
from . import audit, state
from .errors import (
    NotFoundError,
    RangeExhaustedError,
    SalesClosedError,
    StationInactiveError,
    DuplicateError,
)
from .tickets import format_ticket


# Serialises the read-modify-write of a station's next ticket number within a
# single server process. On SQLite (the default) row locks are unavailable, so
# this in-process lock is what prevents overlapping ticket assignments; run the
# app with a single worker. On PostgreSQL the ``with_for_update`` row lock adds
# cross-process safety as well.
_sale_lock = threading.Lock()


def _display_name(first: str, last: str) -> str:
    return " ".join(p for p in [first.strip(), last.strip()] if p).strip()


def _get_locked_station(db: Session, station_id: int) -> SaleStation:
    station = (
        db.query(SaleStation)
        .filter(SaleStation.id == station_id)
        .with_for_update()
        .first()
    )
    if station is None:
        raise NotFoundError(f"Station {station_id} not found")
    return station


def complete_sale(
    db: Session,
    station_id: int,
    first_name: str,
    last_name: str,
    quantity: int,
    device: str | None = None,
    role: str = "volunteer",
    allow_closed: bool = False,
) -> dict:
    """Create a buyer and assign the next ``quantity`` sequential tickets.

    Returns a summary dict with the buyer and the assigned ticket numbers.
    """
    if quantity < 1:
        raise DuplicateError("Quantity must be at least 1", code="bad_quantity")
    if quantity > 500:
        raise DuplicateError("Quantity too large", code="bad_quantity")

    if not allow_closed and not state.get_bool(db, "sales_open"):
        raise SalesClosedError("Raffle ticket sales are closed")

    with _sale_lock:
        station = _get_locked_station(db, station_id)
        if not station.active:
            raise StationInactiveError(
                f"Station '{station.name}' is not active"
            )

        start = station.next_ticket_number
        end = start + quantity - 1
        if end > station.ticket_range_end:
            raise RangeExhaustedError(
                "TICKET RANGE EXHAUSTED. "
                "Please contact the raffle administrator."
            )

        buyer = Buyer(
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            display_name=_display_name(first_name, last_name) or "Guest",
        )
        db.add(buyer)
        db.flush()  # obtain buyer.id

        now = datetime.utcnow()
        ticket_ids = []
        ticket_numbers = []
        for n in range(start, end + 1):
            number = format_ticket(n, station.ticket_width)
            ticket = Ticket(
                ticket_number=number,
                buyer_id=buyer.id,
                sale_station_id=station.id,
                sold=True,
                sold_at=now,
            )
            db.add(ticket)
            db.flush()
            ticket_ids.append(ticket.id)
            ticket_numbers.append(number)

        prev_next = station.next_ticket_number
        station.next_ticket_number = end + 1

        # Record enough information to undo this exact sale later.
        state.set_value(
            db,
            f"last_sale_{station.id}",
            json.dumps(
                {
                    "buyer_id": buyer.id,
                    "ticket_ids": ticket_ids,
                    "prev_next": prev_next,
                }
            ),
        )

        audit.log(
            db,
            "sale.created",
            details=(
                f"{buyer.display_name} bought {quantity} tickets "
                f"{ticket_numbers[0]}-{ticket_numbers[-1]} at {station.name}"
            ),
            device=device,
            role=role,
        )
        db.commit()

    return {
        "buyer": {
            "id": buyer.id,
            "display_name": buyer.display_name,
            "first_name": buyer.first_name,
            "last_name": buyer.last_name,
        },
        "station_id": station.id,
        "station_name": station.name,
        "quantity": quantity,
        "ticket_numbers": ticket_numbers,
        "first_ticket": ticket_numbers[0],
        "last_ticket": ticket_numbers[-1],
        "next_ticket": format_ticket(
            station.next_ticket_number, station.ticket_width
        )
        if station.next_ticket_number <= station.ticket_range_end
        else None,
    }


def undo_last_sale(
    db: Session, station_id: int, device: str | None = None
) -> dict:
    """Reverse the most recent sale at a station (with safeguards).

    Refuses to undo if any of the tickets has already won a prize.
    """
    with _sale_lock:
        station = _get_locked_station(db, station_id)
        raw = state.get(db, f"last_sale_{station.id}")
        if not raw:
            raise NotFoundError("No sale available to undo for this station")

        info = json.loads(raw)
        ticket_ids = info.get("ticket_ids", [])
        tickets = (
            db.query(Ticket).filter(Ticket.id.in_(ticket_ids)).all()
            if ticket_ids
            else []
        )
        if any(t.winning for t in tickets):
            raise DuplicateError(
                "Cannot undo: one of these tickets has already won a prize.",
                code="ticket_won",
            )

        numbers = sorted(t.ticket_number for t in tickets)
        for t in tickets:
            db.delete(t)

        buyer_id = info.get("buyer_id")
        if buyer_id is not None:
            remaining = (
                db.query(Ticket)
                .filter(
                    Ticket.buyer_id == buyer_id,
                    ~Ticket.id.in_(ticket_ids),
                )
                .count()
            )
            if remaining == 0:
                buyer = db.get(Buyer, buyer_id)
                if buyer is not None:
                    db.delete(buyer)

        station.next_ticket_number = info.get(
            "prev_next", station.next_ticket_number
        )
        state.set_value(db, f"last_sale_{station.id}", "")

        audit.log(
            db,
            "sale.undone",
            details=(
                f"Undo sale at {station.name}: removed tickets "
                f"{numbers[0]}-{numbers[-1]}" if numbers else "Undo sale"
            ),
            device=device,
            role="admin",
        )
        db.commit()
    return {
        "station_id": station.id,
        "removed": numbers,
        "next_ticket": format_ticket(
            station.next_ticket_number, station.ticket_width
        ),
    }


def manual_ticket_entry(
    db: Session,
    first_name: str,
    last_name: str,
    starting_ticket: int,
    quantity: int,
    ticket_width: int = 6,
    station_id: int | None = None,
    device: str | None = None,
) -> dict:
    """Admin: create explicit ticket numbers not tied to sequential ranges."""
    if quantity < 1:
        raise DuplicateError("Quantity must be at least 1", code="bad_quantity")

    numbers = [
        format_ticket(n, ticket_width)
        for n in range(starting_ticket, starting_ticket + quantity)
    ]
    existing = (
        db.query(Ticket)
        .filter(Ticket.ticket_number.in_(numbers))
        .first()
    )
    if existing is not None:
        raise DuplicateError(
            f"Ticket {existing.ticket_number} already exists",
            code="duplicate_ticket",
        )

    buyer = Buyer(
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        display_name=_display_name(first_name, last_name) or "Guest",
    )
    db.add(buyer)
    db.flush()

    now = datetime.utcnow()
    for number in numbers:
        db.add(
            Ticket(
                ticket_number=number,
                buyer_id=buyer.id,
                sale_station_id=station_id,
                sold=True,
                sold_at=now,
            )
        )

    audit.log(
        db,
        "sale.created",
        details=(
            f"Manual entry: {buyer.display_name} tickets "
            f"{numbers[0]}-{numbers[-1]}"
        ),
        device=device,
        role="admin",
    )
    db.commit()
    return {
        "buyer": {"id": buyer.id, "display_name": buyer.display_name},
        "ticket_numbers": numbers,
    }
