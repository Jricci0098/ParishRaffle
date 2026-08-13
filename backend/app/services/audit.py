"""Audit logging helper."""
from sqlalchemy.orm import Session

from ..models import AuditLog


def log(
    db: Session,
    action: str,
    details: str = "",
    device: str | None = None,
    role: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        action=action, details=details, device=device, role=role
    )
    db.add(entry)
    return entry
