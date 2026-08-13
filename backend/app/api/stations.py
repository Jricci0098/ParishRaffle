from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import SaleStation
from ..schemas import StationCreate, StationUpdate
from ..services.errors import NotFoundError
from ..services.tickets import format_ticket
from .deps import require_admin

router = APIRouter()


def _serialize(st: SaleStation) -> dict:
    exhausted = st.next_ticket_number > st.ticket_range_end
    return {
        "id": st.id,
        "name": st.name,
        "ticket_range_start": st.ticket_range_start,
        "ticket_range_end": st.ticket_range_end,
        "next_ticket_number": st.next_ticket_number,
        "ticket_width": st.ticket_width,
        "active": st.active,
        "exhausted": exhausted,
        "range_start_display": format_ticket(
            st.ticket_range_start, st.ticket_width
        ),
        "range_end_display": format_ticket(
            st.ticket_range_end, st.ticket_width
        ),
        "next_ticket_display": None
        if exhausted
        else format_ticket(st.next_ticket_number, st.ticket_width),
    }


@router.get("/stations")
def list_stations(db: Session = Depends(get_db)):
    stations = db.query(SaleStation).order_by(SaleStation.id).all()
    return [_serialize(s) for s in stations]


@router.get("/stations/{station_id}")
def get_station(station_id: int, db: Session = Depends(get_db)):
    st = db.get(SaleStation, station_id)
    if st is None:
        raise NotFoundError(f"Station {station_id} not found")
    return _serialize(st)


@router.post("/stations")
def create_station(
    body: StationCreate,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    st = SaleStation(
        name=body.name,
        ticket_range_start=body.ticket_range_start,
        ticket_range_end=body.ticket_range_end,
        next_ticket_number=body.ticket_range_start,
        ticket_width=body.ticket_width,
        active=body.active,
    )
    db.add(st)
    db.commit()
    db.refresh(st)
    return _serialize(st)


@router.patch("/stations/{station_id}")
def update_station(
    station_id: int,
    body: StationUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    st = db.get(SaleStation, station_id)
    if st is None:
        raise NotFoundError(f"Station {station_id} not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(st, field, value)
    db.commit()
    db.refresh(st)
    return _serialize(st)


@router.delete("/stations/{station_id}")
def delete_station(
    station_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    st = db.get(SaleStation, station_id)
    if st is None:
        raise NotFoundError(f"Station {station_id} not found")
    db.delete(st)
    db.commit()
    return {"ok": True}
