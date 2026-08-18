"""Pytest fixtures. Configures an isolated temp SQLite DB before importing
the app so the real /data database is never touched."""
import os
import tempfile

import pytest

# Configure environment BEFORE importing application modules.
_tmpdir = tempfile.mkdtemp(prefix="raffle-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmpdir}/test.db"
os.environ["DEMO_MODE"] = "false"
os.environ["ENABLE_PERIODIC_BACKUP"] = "false"
os.environ["BACKUP_DIR"] = f"{_tmpdir}/backups"
os.environ["ADMIN_PIN"] = "1234"
os.environ["VOLUNTEER_PIN"] = "0000"
os.environ["ALLOW_REPEAT_TICKET_WINNERS"] = "false"

from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine, SessionLocal  # noqa: E402
from app.main import app  # noqa: E402

ADMIN = {"X-Admin-Pin": "1234"}


@pytest.fixture()
def db():
    # Fresh schema for every test.
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db):
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def station(client):
    resp = client.post(
        "/api/stations",
        json={
            "name": "Ticket Table 1",
            "ticket_range_start": 5000,
            "ticket_range_end": 5199,
            "ticket_width": 6,
        },
        headers=ADMIN,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.fixture()
def open_sales(client):
    r = client.post("/api/admin/sales/open", headers=ADMIN)
    assert r.status_code == 200
