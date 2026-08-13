"""Prize management: CRUD, reordering, CSV import."""
import csv
import io

from sqlalchemy.orm import Session

from ..models import Prize
from ..models import prize as prize_model
from . import audit
from .errors import DuplicateError, NotFoundError


def list_prizes(db: Session, session_number: int | None = None) -> list[Prize]:
    q = db.query(Prize)
    if session_number is not None:
        q = q.filter(Prize.session_number == session_number)
    return q.order_by(Prize.sort_order, Prize.prize_number).all()


def create_prize(db: Session, data: dict, device: str | None = None) -> Prize:
    number = data["prize_number"]
    if db.query(Prize).filter(Prize.prize_number == number).first():
        raise DuplicateError(
            f"Prize #{number} already exists", code="duplicate_prize"
        )
    max_order = db.query(Prize).count()
    prize = Prize(
        prize_number=number,
        name=data["name"],
        description=data.get("description"),
        category=data.get("category"),
        session_number=data.get("session_number", 1),
        pickup_station=data.get("pickup_station"),
        sort_order=data.get("sort_order", max_order),
        status=prize_model.STATUS_AVAILABLE,
    )
    db.add(prize)
    audit.log(
        db,
        "prize.created",
        details=f"Prize #{number} '{prize.name}'",
        device=device,
        role="admin",
    )
    db.commit()
    db.refresh(prize)
    return prize


def update_prize(
    db: Session, prize_id: int, data: dict, device: str | None = None
) -> Prize:
    prize = db.get(Prize, prize_id)
    if prize is None:
        raise NotFoundError(f"Prize {prize_id} not found")

    new_number = data.get("prize_number")
    if new_number is not None and new_number != prize.prize_number:
        clash = (
            db.query(Prize)
            .filter(Prize.prize_number == new_number, Prize.id != prize_id)
            .first()
        )
        if clash:
            raise DuplicateError(
                f"Prize #{new_number} already exists", code="duplicate_prize"
            )

    for field in [
        "prize_number",
        "name",
        "description",
        "category",
        "session_number",
        "pickup_station",
        "sort_order",
    ]:
        if field in data and data[field] is not None:
            setattr(prize, field, data[field])

    audit.log(
        db,
        "ticket.modified",
        details=f"Prize #{prize.prize_number} edited",
        device=device,
        role="admin",
    )
    db.commit()
    db.refresh(prize)
    return prize


def delete_prize(db: Session, prize_id: int, device: str | None = None) -> None:
    prize = db.get(Prize, prize_id)
    if prize is None:
        raise NotFoundError(f"Prize {prize_id} not found")
    if prize.winning_ticket_id is not None:
        raise DuplicateError(
            "Cannot delete a prize that has already been drawn.",
            code="prize_drawn",
        )
    audit.log(
        db,
        "prize.deleted",
        details=f"Prize #{prize.prize_number} '{prize.name}' deleted",
        device=device,
        role="admin",
    )
    db.delete(prize)
    db.commit()


def reorder_prizes(
    db: Session, ordered_ids: list[int], device: str | None = None
) -> None:
    for index, pid in enumerate(ordered_ids):
        prize = db.get(Prize, pid)
        if prize is not None:
            prize.sort_order = index
    db.commit()


def import_csv(db: Session, content: str, device: str | None = None) -> dict:
    """Import prizes from CSV.

    Expected columns: prize_number,name,session,pickup_station
    (description and category optional). Existing prize numbers are updated.
    """
    reader = csv.DictReader(io.StringIO(content))
    created = 0
    updated = 0
    errors: list[str] = []

    for i, row in enumerate(reader, start=2):
        try:
            raw_num = (row.get("prize_number") or "").strip()
            if not raw_num:
                continue
            number = int(raw_num)
            name = (row.get("name") or "").strip()
            if not name:
                errors.append(f"Row {i}: missing name")
                continue
            session = int((row.get("session") or "1").strip() or "1")
            pickup = (row.get("pickup_station") or "").strip() or None
            description = (row.get("description") or "").strip() or None
            category = (row.get("category") or "").strip() or None

            existing = (
                db.query(Prize)
                .filter(Prize.prize_number == number)
                .first()
            )
            if existing:
                existing.name = name
                existing.session_number = session
                existing.pickup_station = pickup
                existing.description = description
                existing.category = category
                updated += 1
            else:
                db.add(
                    Prize(
                        prize_number=number,
                        name=name,
                        session_number=session,
                        pickup_station=pickup,
                        description=description,
                        category=category,
                        sort_order=number,
                        status=prize_model.STATUS_AVAILABLE,
                    )
                )
                created += 1
        except (ValueError, KeyError) as exc:
            errors.append(f"Row {i}: {exc}")

    audit.log(
        db,
        "prize.created",
        details=f"CSV import: {created} created, {updated} updated",
        device=device,
        role="admin",
    )
    db.commit()
    return {"created": created, "updated": updated, "errors": errors}
