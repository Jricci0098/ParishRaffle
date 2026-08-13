from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Event, Prize, SaleStation
from ..schemas import SetupWizard
from ..services import audit, state
from .deps import require_admin

router = APIRouter()


@router.get("/setup/status")
def setup_status(db: Session = Depends(get_db)):
    event = db.query(Event).first()
    station_count = db.query(SaleStation).count()
    prize_count = db.query(Prize).count()
    return {
        "needs_setup": event is None or station_count == 0,
        "has_event": event is not None,
        "event_name": event.name if event else None,
        "station_count": station_count,
        "prize_count": prize_count,
    }


@router.post("/setup/wizard")
def run_wizard(
    body: SetupWizard,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    """Create the event and its sales stations in one call (setup wizard)."""
    event = Event(name=body.event_name, event_date=body.event_date, status="ACTIVE")
    db.add(event)
    db.flush()

    created_stations = []
    for s in body.stations:
        st = SaleStation(
            event_id=event.id,
            name=s.name,
            ticket_range_start=s.ticket_range_start,
            ticket_range_end=s.ticket_range_end,
            next_ticket_number=s.ticket_range_start,
            ticket_width=s.ticket_width,
            active=s.active,
        )
        db.add(st)
        created_stations.append(st)

    state.set_value(db, "current_session", "1")
    state.set_value(db, "sales_open", "false")
    audit.log(
        db,
        "session.started",
        details=f"Event '{event.name}' created via setup wizard",
        role="admin",
    )
    db.commit()
    return {
        "event": {"id": event.id, "name": event.name},
        "stations": len(created_stations),
    }
