"""CSV report generation and ticket import."""
import csv
import io
from datetime import datetime

from sqlalchemy.orm import Session

from ..models import Buyer, Claim, Draw, Prize, SaleStation, Ticket
from ..models import prize as prize_model
from . import audit
from .errors import DuplicateError


def _csv(headers: list[str], rows: list[list]) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(["" if v is None else v for v in row])
    return out.getvalue()


def _fmt(dt: datetime | None) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else ""


def ticket_sales(db: Session) -> str:
    rows = []
    for t in db.query(Ticket).order_by(Ticket.ticket_number).all():
        buyer = db.get(Buyer, t.buyer_id) if t.buyer_id else None
        station = (
            db.get(SaleStation, t.sale_station_id)
            if t.sale_station_id
            else None
        )
        rows.append(
            [
                t.ticket_number,
                buyer.display_name if buyer else "",
                station.name if station else "",
                "yes" if t.sold else "no",
                _fmt(t.sold_at),
                "yes" if t.winning else "no",
                "yes" if t.claimed else "no",
            ]
        )
    return _csv(
        [
            "ticket_number",
            "buyer",
            "station",
            "sold",
            "sold_at",
            "winning",
            "claimed",
        ],
        rows,
    )


def buyers(db: Session) -> str:
    rows = []
    for b in db.query(Buyer).order_by(Buyer.last_name, Buyer.first_name).all():
        count = db.query(Ticket).filter(Ticket.buyer_id == b.id).count()
        rows.append(
            [b.id, b.first_name, b.last_name, b.display_name, count, _fmt(b.created_at)]
        )
    return _csv(
        ["id", "first_name", "last_name", "display_name", "ticket_count", "created_at"],
        rows,
    )


def _winner_rows(db: Session, prizes):
    rows = []
    for p in prizes:
        buyer = db.get(Buyer, p.winner_id) if p.winner_id else None
        ticket = (
            db.get(Ticket, p.winning_ticket_id)
            if p.winning_ticket_id
            else None
        )
        draw = (
            db.query(Draw)
            .filter(Draw.prize_id == p.id, Draw.status == "VALID")
            .order_by(Draw.drawn_at.desc())
            .first()
        )
        claim = (
            db.query(Claim)
            .filter(Claim.prize_id == p.id)
            .order_by(Claim.claimed_at.desc())
            .first()
        )
        rows.append(
            [
                p.prize_number,
                p.name,
                ticket.ticket_number if ticket else "",
                buyer.display_name if buyer else "",
                _fmt(draw.drawn_at) if draw else "",
                "yes" if p.status == prize_model.STATUS_CLAIMED else "no",
                _fmt(claim.claimed_at) if claim else "",
                p.session_number,
                p.pickup_station or "",
            ]
        )
    return rows


def winners(db: Session, only_unclaimed: bool = False) -> str:
    q = db.query(Prize).filter(Prize.winning_ticket_id.isnot(None))
    if only_unclaimed:
        q = q.filter(Prize.status != prize_model.STATUS_CLAIMED)
    prizes = q.order_by(Prize.prize_number).all()
    headers = [
        "prize_number",
        "prize",
        "ticket_number",
        "winner",
        "draw_time",
        "claimed",
        "claim_time",
        "session",
        "pickup_station",
    ]
    return _csv(headers, _winner_rows(db, prizes))


def prizes_report(db: Session) -> str:
    rows = []
    for p in db.query(Prize).order_by(Prize.prize_number).all():
        rows.append(
            [
                p.prize_number,
                p.name,
                p.description or "",
                p.category or "",
                p.session_number,
                p.pickup_station or "",
                p.status,
            ]
        )
    return _csv(
        [
            "prize_number",
            "name",
            "description",
            "category",
            "session",
            "pickup_station",
            "status",
        ],
        rows,
    )


def claimed_prizes(db: Session) -> str:
    return winners(db, only_unclaimed=False)


def drawing_history(db: Session) -> str:
    rows = []
    for d in db.query(Draw).order_by(Draw.drawn_at).all():
        prize = db.get(Prize, d.prize_id)
        buyer = db.get(Buyer, d.buyer_id) if d.buyer_id else None
        ticket = db.get(Ticket, d.ticket_id) if d.ticket_id else None
        rows.append(
            [
                d.id,
                prize.prize_number if prize else "",
                prize.name if prize else "",
                ticket.ticket_number if ticket else "",
                buyer.display_name if buyer else "",
                _fmt(d.drawn_at),
                d.status,
                d.redraw_of or "",
                d.notes or "",
            ]
        )
    return _csv(
        [
            "draw_id",
            "prize_number",
            "prize",
            "ticket_number",
            "winner",
            "drawn_at",
            "status",
            "redraw_of",
            "notes",
        ],
        rows,
    )


def session_summary(db: Session) -> str:
    rows = []
    sessions = [
        r[0]
        for r in db.query(Prize.session_number).distinct().all()
    ]
    for s in sorted(sessions):
        prizes = db.query(Prize).filter(Prize.session_number == s)
        total = prizes.count()
        drawn = prizes.filter(Prize.winning_ticket_id.isnot(None)).count()
        claimed = prizes.filter(
            Prize.status == prize_model.STATUS_CLAIMED
        ).count()
        rows.append([s, total, drawn, claimed, drawn - claimed])
    return _csv(
        ["session", "total_prizes", "drawn", "claimed", "unclaimed"], rows
    )


def import_tickets_csv(
    db: Session, content: str, device: str | None = None
) -> dict:
    """Import ticket-to-buyer mappings.

    Format: ticket_number,first_name,last_name
    Buyers are de-duplicated by name within the import.
    """
    reader = csv.DictReader(io.StringIO(content))
    created = 0
    skipped = 0
    errors: list[str] = []
    buyer_cache: dict[tuple, Buyer] = {}

    for i, row in enumerate(reader, start=2):
        number = (row.get("ticket_number") or "").strip()
        first = (row.get("first_name") or "").strip()
        last = (row.get("last_name") or "").strip()
        if not number:
            continue
        if db.query(Ticket).filter(Ticket.ticket_number == number).first():
            skipped += 1
            continue
        key = (first.lower(), last.lower())
        buyer = buyer_cache.get(key)
        if buyer is None:
            buyer = Buyer(
                first_name=first,
                last_name=last,
                display_name=" ".join(p for p in [first, last] if p) or "Guest",
            )
            db.add(buyer)
            db.flush()
            buyer_cache[key] = buyer
        db.add(
            Ticket(
                ticket_number=number,
                buyer_id=buyer.id,
                sold=True,
                sold_at=datetime.utcnow(),
            )
        )
        created += 1

    audit.log(
        db,
        "ticket.modified",
        details=f"Ticket CSV import: {created} created, {skipped} skipped",
        device=device,
        role="admin",
    )
    db.commit()
    return {"created": created, "skipped": skipped, "errors": errors}
