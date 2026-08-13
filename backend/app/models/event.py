from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Date

from ..database.base import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    event_date = Column(Date, nullable=True)
    # DRAFT | ACTIVE | CLOSED
    status = Column(String, nullable=False, default="DRAFT")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
