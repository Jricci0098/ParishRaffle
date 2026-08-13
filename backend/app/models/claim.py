from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from ..database.base import Base


class Claim(Base):
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True)
    prize_id = Column(Integer, ForeignKey("prizes.id"), nullable=False)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True)
    buyer_id = Column(Integer, ForeignKey("buyers.id"), nullable=True)
    claimed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    verified_by = Column(String, nullable=True)
    notes = Column(String, nullable=True)

    prize = relationship("Prize", foreign_keys=[prize_id])
    ticket = relationship("Ticket", foreign_keys=[ticket_id])
    buyer = relationship("Buyer", foreign_keys=[buyer_id])
