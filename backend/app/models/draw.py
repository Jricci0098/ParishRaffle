from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from ..database.base import Base

# Draw status values.
DRAW_VALID = "VALID"
DRAW_VOID = "VOID"  # superseded by a redraw / winner could not claim


class Draw(Base):
    __tablename__ = "draws"

    id = Column(Integer, primary_key=True)
    prize_id = Column(Integer, ForeignKey("prizes.id"), nullable=False)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True)
    buyer_id = Column(Integer, ForeignKey("buyers.id"), nullable=True)
    drawn_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String, nullable=False, default=DRAW_VALID)
    # If this draw replaced another (redraw), the id of the previous draw.
    redraw_of = Column(Integer, ForeignKey("draws.id"), nullable=True)
    notes = Column(String, nullable=True)

    prize = relationship("Prize", back_populates="draws")
    ticket = relationship("Ticket", foreign_keys=[ticket_id])
    buyer = relationship("Buyer", foreign_keys=[buyer_id])
