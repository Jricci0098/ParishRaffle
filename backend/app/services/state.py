"""Mutable runtime state stored in the ``settings`` key/value table.

Keys:
    sales_open           -> "true" / "false"
    current_session      -> "1" / "2" / ...
    session_1_status     -> "NOT_STARTED" / "STARTED" / "ENDED"
    session_2_status     -> ...
    display_mode         -> LATEST | ALL | UNCLAIMED | SESSION_1 |
                            SESSION_2 | ANNOUNCEMENT
    announcement_text    -> free text shown in ANNOUNCEMENT mode
"""
from sqlalchemy.orm import Session

from ..models import Setting

DEFAULTS = {
    "sales_open": "false",
    "current_session": "1",
    "session_1_status": "NOT_STARTED",
    "session_2_status": "NOT_STARTED",
    "display_mode": "LATEST",
    "announcement_text": "Welcome to the Parish Picnic Raffle!",
}


def get(db: Session, key: str, default: str | None = None) -> str | None:
    row = db.get(Setting, key)
    if row is not None:
        return row.value
    return DEFAULTS.get(key, default)


def set_value(db: Session, key: str, value: str) -> None:
    row = db.get(Setting, key)
    if row is None:
        row = Setting(key=key, value=value)
        db.add(row)
    else:
        row.value = value


def get_bool(db: Session, key: str, default: bool = False) -> bool:
    val = get(db, key, "true" if default else "false")
    return str(val).lower() == "true"


def all_state(db: Session) -> dict:
    """Return the full runtime state, merging defaults with stored values."""
    stored = {s.key: s.value for s in db.query(Setting).all()}
    merged = dict(DEFAULTS)
    merged.update(stored)
    return merged
