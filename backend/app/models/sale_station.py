from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from ..database.base import Base


class SaleStation(Base):
    __tablename__ = "sale_stations"

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)
    name = Column(String, nullable=False)
    # Ticket numbers are stored as strings to preserve leading zeros, but the
    # numeric bounds are stored as integers for range arithmetic.
    ticket_range_start = Column(Integer, nullable=False)
    ticket_range_end = Column(Integer, nullable=False)
    next_ticket_number = Column(Integer, nullable=False)
    # Width used when formatting ticket numbers (e.g. 6 -> "005000").
    ticket_width = Column(Integer, nullable=False, default=6)
    active = Column(Boolean, nullable=False, default=True)

    tickets = relationship("Ticket", back_populates="sale_station")
