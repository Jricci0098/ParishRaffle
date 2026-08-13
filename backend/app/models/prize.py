from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from ..database.base import Base

# Prize status values.
STATUS_AVAILABLE = "AVAILABLE"
STATUS_DRAWN = "DRAWN"
STATUS_CLAIMED = "CLAIMED"
STATUS_REDRAW_REQUIRED = "REDRAW_REQUIRED"


class Prize(Base):
    __tablename__ = "prizes"

    id = Column(Integer, primary_key=True)
    prize_number = Column(Integer, nullable=False, unique=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    category = Column(String, nullable=True)
    session_number = Column(Integer, nullable=False, default=1)
    pickup_station = Column(String, nullable=True)
    # Manual ordering for the drawing console.
    sort_order = Column(Integer, nullable=False, default=0)

    winning_ticket_id = Column(
        Integer, ForeignKey("tickets.id"), nullable=True
    )
    winner_id = Column(Integer, ForeignKey("buyers.id"), nullable=True)
    status = Column(String, nullable=False, default=STATUS_AVAILABLE)

    winning_ticket = relationship("Ticket", foreign_keys=[winning_ticket_id])
    winner = relationship("Buyer", foreign_keys=[winner_id])
    draws = relationship(
        "Draw", back_populates="prize", order_by="Draw.drawn_at"
    )
