import os

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AuditLog, Buyer, Prize, Ticket
from ..models import prize as prize_model
from ..schemas import DisplayMode, SessionAction
from ..services import audit, backup, state
from ..services.errors import NotFoundError
from ..websocket import manager
from .deps import require_admin

router = APIRouter()


@router.get("/admin/summary")
def summary(db: Session = Depends(get_db)):
    tickets_sold = db.query(Ticket).filter(Ticket.sold.is_(True)).count()
    buyers = db.query(Buyer).count()
    prizes = db.query(Prize).count()
    drawn = db.query(Prize).filter(Prize.winning_ticket_id.isnot(None)).count()
    claimed = (
        db.query(Prize)
        .filter(Prize.status == prize_model.STATUS_CLAIMED)
        .count()
    )
    st = state.all_state(db)
    return {
        "tickets_sold": tickets_sold,
        "buyers": buyers,
        "prizes": prizes,
        "prizes_drawn": drawn,
        "claimed": claimed,
        "unclaimed": drawn - claimed,
        "current_session": int(st.get("current_session", "1")),
        "sales_open": st.get("sales_open") == "true",
        "display_mode": st.get("display_mode", "LATEST"),
        "session_1_status": st.get("session_1_status"),
        "session_2_status": st.get("session_2_status"),
        "announcement_text": st.get("announcement_text"),
    }


@router.get("/admin/state")
def get_state(db: Session = Depends(get_db)):
    return state.all_state(db)


@router.post("/admin/sales/open")
def open_sales(db: Session = Depends(get_db), _: str = Depends(require_admin)):
    state.set_value(db, "sales_open", "true")
    audit.log(db, "sales.opened", role="admin")
    db.commit()
    manager.broadcast_sync("sales.opened", {"sales_open": True})
    return {"sales_open": True}


@router.post("/admin/sales/close")
def close_sales(db: Session = Depends(get_db), _: str = Depends(require_admin)):
    state.set_value(db, "sales_open", "false")
    audit.log(db, "sales.closed", role="admin")
    db.commit()
    manager.broadcast_sync("sales.closed", {"sales_open": False})
    return {"sales_open": False}


@router.post("/admin/session/start")
def start_session(
    body: SessionAction,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    state.set_value(db, "current_session", str(body.session_number))
    state.set_value(
        db, f"session_{body.session_number}_status", "STARTED"
    )
    audit.log(
        db, "session.started", details=f"Session {body.session_number}", role="admin"
    )
    db.commit()
    manager.broadcast_sync(
        "session.started", {"session_number": body.session_number}
    )
    return state.all_state(db)


@router.post("/admin/session/end")
def end_session(
    body: SessionAction,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    state.set_value(db, f"session_{body.session_number}_status", "ENDED")
    audit.log(
        db, "session.ended", details=f"Session {body.session_number}", role="admin"
    )
    db.commit()
    manager.broadcast_sync(
        "session.ended", {"session_number": body.session_number}
    )
    return state.all_state(db)


@router.post("/admin/display")
def set_display_mode(
    body: DisplayMode,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    state.set_value(db, "display_mode", body.mode)
    if body.announcement_text is not None:
        state.set_value(db, "announcement_text", body.announcement_text)
    audit.log(db, "display.mode.changed", details=body.mode, role="admin")
    db.commit()
    manager.broadcast_sync(
        "display.mode.changed",
        {
            "mode": body.mode,
            "announcement_text": state.get(db, "announcement_text"),
        },
    )
    return state.all_state(db)


@router.get("/admin/devices")
def devices():
    return manager.device_list()


@router.get("/admin/audit")
def audit_log(limit: int = 200, db: Session = Depends(get_db)):
    rows = (
        db.query(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "created_at": r.created_at.isoformat(),
            "action": r.action,
            "device": r.device,
            "role": r.role,
            "details": r.details,
        }
        for r in rows
    ]


@router.post("/admin/backup")
def create_backup(_: str = Depends(require_admin)):
    path = backup.create_backup(label="manual")
    return {"path": path, "created": path is not None}


@router.get("/admin/backup/download")
def download_backup(_: str = Depends(require_admin)):
    path = backup.latest_backup_path()
    if not path or not os.path.exists(path):
        raise NotFoundError("No SQLite database available to back up")
    return FileResponse(
        path, media_type="application/octet-stream", filename=os.path.basename(path)
    )


@router.get("/admin/backups")
def list_backups(_: str = Depends(require_admin)):
    return backup.list_backups()
