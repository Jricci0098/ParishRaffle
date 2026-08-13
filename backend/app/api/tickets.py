from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Buyer, Prize
from ..services.errors import NotFoundError
from ..services.tickets import find_ticket

router = APIRouter()


@router.get("/tickets/{ticket_number}")
def get_ticket(ticket_number: str, db: Session = Depends(get_db)):
    ticket = find_ticket(db, ticket_number)
    if ticket is None:
        raise NotFoundError(f"Ticket {ticket_number} is not registered.")
    buyer = db.get(Buyer, ticket.buyer_id) if ticket.buyer_id else None
    won_prize = None
    if ticket.winning:
        p = db.query(Prize).filter(Prize.winning_ticket_id == ticket.id).first()
        if p:
            won_prize = {"prize_number": p.prize_number, "name": p.name}
    return {
        "ticket_number": ticket.ticket_number,
        "sold": ticket.sold,
        "winning": ticket.winning,
        "claimed": ticket.claimed,
        "buyer": {
            "id": buyer.id if buyer else None,
            "display_name": buyer.display_name if buyer else None,
        },
        "won_prize": won_prize,
    }
