from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..services import demo as demo_service
from ..services.errors import AuthError
from ..websocket import manager
from .deps import require_admin

router = APIRouter()


@router.get("/demo/status")
def demo_status():
    return {"demo_mode": settings.DEMO_MODE}


@router.post("/demo/generate")
def generate(
    buyers: int = 100,
    tickets: int = 500,
    prizes: int = 20,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    if not settings.DEMO_MODE:
        raise AuthError(
            "Demo data generation is only allowed in DEMO_MODE.",
            code="not_demo",
        )
    result = demo_service.generate_demo_data(db, buyers, tickets, prizes)
    manager.broadcast_sync("demo.generated", result)
    return result


@router.post("/demo/reset")
def reset(
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    if not settings.DEMO_MODE:
        raise AuthError(
            "Reset is only allowed in DEMO_MODE.", code="not_demo"
        )
    demo_service.reset_demo(db)
    manager.broadcast_sync("demo.reset", {})
    return {"ok": True}
