from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import CsvImport, PrizeCreate, PrizeReorder, PrizeUpdate
from ..services import draws as draws_service
from ..services import prizes as prizes_service
from ..services.errors import NotFoundError
from .deps import require_admin

router = APIRouter()


@router.get("/prizes")
def list_prizes(session: int | None = None, db: Session = Depends(get_db)):
    prizes = prizes_service.list_prizes(db, session_number=session)
    return [draws_service.prize_public_view(db, p) for p in prizes]


@router.get("/prizes/current")
def current_prize(db: Session = Depends(get_db)):
    prize = draws_service.current_prize(db)
    if prize is None:
        return None
    return draws_service.prize_public_view(db, prize)


@router.get("/prizes/navigate/{prize_id}")
def navigate(prize_id: int, offset: int = 0, db: Session = Depends(get_db)):
    prize = draws_service.prize_at_offset(db, prize_id, offset)
    if prize is None:
        return None
    return draws_service.prize_public_view(db, prize)


@router.post("/prizes")
def create_prize(
    body: PrizeCreate,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    prize = prizes_service.create_prize(db, body.model_dump())
    return draws_service.prize_public_view(db, prize)


@router.patch("/prizes/{prize_id}")
def update_prize(
    prize_id: int,
    body: PrizeUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    prize = prizes_service.update_prize(db, prize_id, body.model_dump())
    return draws_service.prize_public_view(db, prize)


@router.delete("/prizes/{prize_id}")
def delete_prize(
    prize_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    prizes_service.delete_prize(db, prize_id)
    return {"ok": True}


@router.post("/prizes/reorder")
def reorder(
    body: PrizeReorder,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    prizes_service.reorder_prizes(db, body.ordered_ids)
    return {"ok": True}


@router.post("/prizes/import")
def import_prizes(
    body: CsvImport,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    return prizes_service.import_csv(db, body.content)
