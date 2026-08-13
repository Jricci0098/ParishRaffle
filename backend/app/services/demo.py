"""Demo / dry-run data generation and reset.

Runs against whichever database the app booted with. When ``DEMO_MODE`` is on
that is a separate demo database, so production data is never touched.
"""
import random
from datetime import datetime

from sqlalchemy.orm import Session

from ..models import (
    AuditLog,
    Buyer,
    Claim,
    Draw,
    Event,
    Prize,
    SaleStation,
    Setting,
    Ticket,
)
from ..models import prize as prize_model
from . import audit, state
from .tickets import format_ticket

FIRST_NAMES = [
    "Mary", "Robert", "James", "Patricia", "John", "Jennifer", "Michael",
    "Linda", "William", "Elizabeth", "David", "Barbara", "Joseph", "Susan",
    "Thomas", "Margaret", "Charles", "Dorothy", "Daniel", "Nancy",
]
LAST_NAMES = [
    "Jones", "Smith", "Williams", "Brown", "Davis", "Miller", "Wilson",
    "Moore", "Taylor", "Anderson", "Thomas", "Jackson", "White", "Harris",
    "Martin", "Thompson", "Garcia", "Martinez", "Robinson", "Clark",
]
PRIZE_NAMES = [
    "Chocolate Basket", "Restaurant Gift Card", "School Backpack",
    "Coffee Basket", "Wine Gift Set", "Toy Bundle", "Spa Day Package",
    "Grocery Gift Card", "Family Board Games", "Movie Night Basket",
    "Gardening Kit", "BBQ Grill Set", "Bakery Gift Box", "Bookstore Voucher",
    "Sports Equipment", "Handmade Quilt", "Electronics Bundle", "Pizza Party",
    "Ice Cream Basket", "Local Honey Set",
]
PICKUP_STATIONS = ["A", "B", "C"]


def generate_demo_data(
    db: Session,
    n_buyers: int = 100,
    n_tickets: int = 500,
    n_prizes: int = 20,
) -> dict:
    """Populate the database with a realistic sample raffle."""
    # Event
    event = Event(
        name="DEMO — Saint Paul VI Parish Picnic Raffle 2026",
        status="ACTIVE",
    )
    db.add(event)
    db.flush()

    # Stations covering 5000-5599 in three ranges.
    ranges = [(5000, 5199), (5200, 5399), (5400, 5599)]
    stations = []
    for i, (lo, hi) in enumerate(ranges, start=1):
        st = SaleStation(
            event_id=event.id,
            name=f"Ticket Table {i}",
            ticket_range_start=lo,
            ticket_range_end=hi,
            next_ticket_number=lo,
            ticket_width=6,
            active=True,
        )
        db.add(st)
        stations.append(st)
    db.flush()

    # Buyers
    buyers = []
    for _ in range(n_buyers):
        f = random.choice(FIRST_NAMES)
        l = random.choice(LAST_NAMES)
        b = Buyer(first_name=f, last_name=l, display_name=f"{f} {l}")
        db.add(b)
        buyers.append(b)
    db.flush()

    # Tickets assigned sequentially per station until n_tickets reached.
    created = 0
    now = datetime.utcnow()
    for st in stations:
        n = st.ticket_range_start
        while n <= st.ticket_range_end and created < n_tickets:
            buyer = random.choice(buyers)
            db.add(
                Ticket(
                    ticket_number=format_ticket(n, st.ticket_width),
                    buyer_id=buyer.id,
                    sale_station_id=st.id,
                    sold=True,
                    sold_at=now,
                )
            )
            n += 1
            created += 1
        st.next_ticket_number = n

    # Prizes split across two sessions.
    for i in range(1, n_prizes + 1):
        session = 1 if i <= n_prizes // 2 else 2
        db.add(
            Prize(
                prize_number=i,
                name=PRIZE_NAMES[(i - 1) % len(PRIZE_NAMES)],
                session_number=session,
                pickup_station=random.choice(PICKUP_STATIONS),
                sort_order=i,
                status=prize_model.STATUS_AVAILABLE,
            )
        )

    state.set_value(db, "sales_open", "true")
    state.set_value(db, "current_session", "1")
    state.set_value(db, "display_mode", "LATEST")
    audit.log(
        db,
        "sale.created",
        details=(
            f"Demo data generated: {n_buyers} buyers, {created} tickets, "
            f"{n_prizes} prizes"
        ),
        role="admin",
    )
    db.commit()
    return {"buyers": n_buyers, "tickets": created, "prizes": n_prizes}


def reset_demo(db: Session) -> None:
    """Delete all data (demo database only)."""
    for model in [Claim, Draw, Ticket, Prize, Buyer, SaleStation, Event, AuditLog, Setting]:
        db.query(model).delete()
    db.commit()
