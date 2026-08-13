from fastapi import APIRouter

from . import (
    admin,
    auth,
    claims,
    demo,
    draws,
    prizes,
    reports,
    sales,
    setup,
    stations,
    tickets,
)

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(stations.router, tags=["stations"])
api_router.include_router(sales.router, tags=["sales"])
api_router.include_router(tickets.router, tags=["tickets"])
api_router.include_router(prizes.router, tags=["prizes"])
api_router.include_router(draws.router, tags=["draws"])
api_router.include_router(claims.router, tags=["claims"])
api_router.include_router(reports.router, tags=["reports"])
api_router.include_router(admin.router, tags=["admin"])
api_router.include_router(demo.router, tags=["demo"])
api_router.include_router(setup.router, tags=["setup"])

__all__ = ["api_router"]
