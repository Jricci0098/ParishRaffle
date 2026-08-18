from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import ManualTicketEntry, SaleCreate, UndoSale
from ..services import sales as sales_service
from ..services import state
from ..websocket import manager
from .deps import require_admin

router = APIRouter()


@router.post("/sales")
def create_sale(body: SaleCreate, db: Session = Depends(get_db)):
    result = sales_service.complete_sale(
        db,
        station_id=body.station_id,
        first_name=body.first_name,
        last_name=body.last_name,
        quantity=body.quantity,
        device=body.device,
    )
    manager.broadcast_sync(
        "sale.created",
        {
            "buyer": result["buyer"]["display_name"],
            "station_id": result["station_id"],
            "first_ticket": result["first_ticket"],
            "last_ticket": result["last_ticket"],
            "quantity": result["quantity"],
        },
    )
    return result


@router.post("/sales/undo")
def undo_sale(
    body: UndoSale,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    result = sales_service.undo_last_sale(
        db, station_id=body.station_id, device=body.device
    )
    manager.broadcast_sync("sale.undone", {"station_id": body.station_id})
    return result


@router.post("/sales/manual")
def manual_entry(
    body: ManualTicketEntry,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    return sales_service.manual_ticket_entry(
        db,
        first_name=body.first_name,
        last_name=body.last_name,
        starting_ticket=body.starting_ticket,
        quantity=body.quantity,
        ticket_width=body.ticket_width,
        station_id=body.station_id,
    )


@router.get("/sales/status")
def sales_status(db: Session = Depends(get_db)):
    return {"sales_open": state.get_bool(db, "sales_open")}
