from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text

from ..database.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    created_at = Column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )
    action = Column(String, nullable=False)
    device = Column(String, nullable=True)
    role = Column(String, nullable=True)
    details = Column(Text, nullable=True)
