"""Tests for the PIN auth boundary and the opt-in write-authorisation flag."""
from app.security import pin_matches

from .conftest import ADMIN

VOL = {"X-Pin": "0000"}  # matches VOLUNTEER_PIN in conftest


def _sell(client, station_id, headers=None):
    return client.post(
        "/api/sales",
        json={
            "station_id": station_id,
            "first_name": "A",
            "last_name": "B",
            "quantity": 1,
        },
        headers=headers or {},
    )


def test_pin_matches_is_safe_for_empty_and_mismatch():
    assert pin_matches("1234", "1234")
    assert not pin_matches("1234", "1235")
    assert not pin_matches("", "1234")
    assert not pin_matches(None, "1234")
    assert not pin_matches("1234", None)


def test_admin_endpoint_rejects_missing_and_wrong_pin(client):
    assert client.post("/api/admin/sales/close").status_code == 401
    assert (
        client.post("/api/admin/sales/close", headers={"X-Admin-Pin": "wrong"}).status_code
        == 401
    )
    assert client.post("/api/admin/sales/close", headers=ADMIN).status_code == 200


def test_writes_are_open_by_default(client, station, open_sales):
    # REQUIRE_PIN_FOR_WRITES is off by default: no PIN needed to record a sale.
    assert _sell(client, station["id"]).status_code == 200


def test_writes_require_pin_when_flag_enabled(
    client, station, open_sales, monkeypatch
):
    from app.config import settings

    monkeypatch.setattr(settings, "REQUIRE_PIN_FOR_WRITES", True)

    # Blocked without a PIN...
    assert _sell(client, station["id"]).status_code == 401
    # ...allowed with the volunteer PIN.
    assert _sell(client, station["id"], headers=VOL).status_code == 200
    # ...and the flag is advertised to the frontend.
    assert client.get("/api/config").json()["require_pin_for_writes"] is True
