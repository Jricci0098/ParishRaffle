from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import CsvImport
from ..services import reports as reports_service
from .deps import require_admin

router = APIRouter()

REPORTS = {
    "ticket-sales": reports_service.ticket_sales,
    "buyers": reports_service.buyers,
    "winners": reports_service.winners,
    "prizes": reports_service.prizes_report,
    "claimed": reports_service.claimed_prizes,
    "unclaimed": lambda db: reports_service.winners(db, only_unclaimed=True),
    "drawing-history": reports_service.drawing_history,
    "session-summary": reports_service.session_summary,
}


def _csv_response(content: str, name: str) -> Response:
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{name}.csv"'},
    )


@router.get("/reports/{report_name}")
def get_report(report_name: str, db: Session = Depends(get_db)):
    fn = REPORTS.get(report_name)
    if fn is None:
        return Response(status_code=404, content="Unknown report")
    return _csv_response(fn(db), f"raffle-{report_name}")


@router.post("/imports/tickets")
def import_tickets(
    body: CsvImport,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    return reports_service.import_tickets_csv(db, body.content)
