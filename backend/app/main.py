"""FastAPI application entry point.

Serves the REST API under ``/api``, a WebSocket at ``/ws`` for live updates,
and (in production) the built React frontend for every other route so the
whole app runs from a single local server with no Internet access.
"""
import asyncio
import json
import logging
import os

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .api import api_router
from .config import settings
from .database import init_db
from .services import backup
from .services.errors import RaffleError
from .websocket import manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("raffle")

app = FastAPI(title=settings.APP_NAME)

# CORS is permissive: devices are on a trusted local network and the origin is
# not known in advance (server IP varies per venue).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RaffleError)
async def raffle_error_handler(request: Request, exc: RaffleError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


app.include_router(api_router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME, "demo_mode": settings.DEMO_MODE}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue
            action = msg.get("action")
            if action == "register":
                await manager.register_device(
                    websocket,
                    msg.get("name", "Unknown"),
                    msg.get("role", "viewer"),
                )
            elif action == "heartbeat":
                manager.heartbeat(websocket)
            elif action == "ping":
                await websocket.send_text(json.dumps({"event": "pong", "data": {}}))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:  # pragma: no cover - defensive
        manager.disconnect(websocket)


async def _periodic_backup():
    interval = max(1, settings.BACKUP_INTERVAL) * 60
    while True:
        await asyncio.sleep(interval)
        try:
            path = backup.create_backup(label="auto")
            if path:
                logger.info("Automatic backup created: %s", path)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Backup failed: %s", exc)


@app.on_event("startup")
async def on_startup():
    init_db()
    # Startup backup (best-effort).
    try:
        backup.create_backup(label="startup")
    except Exception as exc:  # pragma: no cover
        logger.warning("Startup backup failed: %s", exc)
    if settings.ENABLE_PERIODIC_BACKUP:
        asyncio.create_task(_periodic_backup())
    logger.info("%s started (demo_mode=%s)", settings.APP_NAME, settings.DEMO_MODE)


# ----- Serve the built frontend (production) -----
# The Docker image copies the Vite build to ``/app/static``. In development the
# frontend runs on its own Vite dev server, so this block is optional.
_static_dir = os.getenv("STATIC_DIR", "/app/static")
if os.path.isdir(_static_dir):
    app.mount(
        "/", StaticFiles(directory=_static_dir, html=True), name="static"
    )

    @app.exception_handler(404)
    async def spa_fallback(request: Request, exc):
        # Let the SPA handle client-side routes; return index.html for
        # non-API GET requests that 404.
        if request.url.path.startswith("/api") or request.url.path.startswith("/ws"):
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        index = os.path.join(_static_dir, "index.html")
        if os.path.exists(index):
            from fastapi.responses import FileResponse

            return FileResponse(index)
        return JSONResponse(status_code=404, content={"detail": "Not found"})
