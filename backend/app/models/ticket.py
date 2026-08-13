from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from ..database.base import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True)
    # Stored as a string to preserve leading zeros (e.g. "005142").
    ticket_number = Column(String, nullable=False, unique=True, index=True)
    buyer_id = Column(Integer, ForeignKey("buyers.id"), nullable=True)
    sale_station_id = Column(
        Integer, ForeignKey("sale_stations.id"), nullable=True
    )
    sold = Column(Boolean, nullable=False, default=False)
    sold_at = Column(DateTime, nullable=True)
    winning = Column(Boolean, nullable=False, default=False)
    claimed = Column(Boolean, nullable=False, default=False)
    notes = Column(String, nullable=True)

    buyer = relationship("Buyer", back_populates="tickets")
    sale_station = relationship("SaleStation", back_populates="tickets")
