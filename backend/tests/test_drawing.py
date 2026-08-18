"""Tests for drawing, lookup, confirmation, redraw, claim, sessions."""
from .conftest import ADMIN


def _setup_prizes(client):
    csv = "prize_number,name,session,pickup_station\n"
    for i in range(1, 6):
        csv += f"{i},Prize {i},1,A\n"
    r = client.post("/api/prizes/import", json={"content": csv}, headers=ADMIN)
    assert r.status_code == 200, r.text


def _sell(client, station_id, first, last, qty):
    return client.post(
        "/api/sales",
        json={
            "station_id": station_id,
            "first_name": first,
            "last_name": last,
            "quantity": qty,
        },
    ).json()


def test_duplicate_prize_prevention(client):
    r1 = client.post(
        "/api/prizes",
        json={"prize_number": 1, "name": "A", "session_number": 1},
        headers=ADMIN,
    )
    assert r1.status_code == 200
    r2 = client.post(
        "/api/prizes",
        json={"prize_number": 1, "name": "B", "session_number": 1},
        headers=ADMIN,
    )
    assert r2.status_code == 409


def test_csv_import_prizes(client):
    _setup_prizes(client)
    r = client.get("/api/prizes")
    assert len(r.json()) == 5


def test_lookup_and_confirm_winner(client, station, open_sales):
    _setup_prizes(client)
    sale = _sell(client, station["id"], "Mary", "Jones", 20)
    winning_ticket = sale["ticket_numbers"][5]  # 005005

    current = client.get("/api/prizes/current").json()
    assert current["prize_number"] == 1

    look = client.post(
        "/api/draws/lookup", json={"ticket_number": winning_ticket}
    ).json()
    assert look["status"] == "ok"
    assert look["buyer"]["display_name"] == "Mary Jones"

    confirm = client.post(
        "/api/draws",
        json={"prize_id": current["id"], "ticket_number": winning_ticket},
    )
    assert confirm.status_code == 200, confirm.text
    view = confirm.json()
    assert view["winner_name"] == "Mary Jones"
    assert view["status"] == "DRAWN"

    # Winner shows up in winners list.
    winners = client.get("/api/winners").json()
    assert any(w["winner_name"] == "Mary Jones" for w in winners)


def test_unknown_ticket(client, station, open_sales):
    _setup_prizes(client)
    current = client.get("/api/prizes/current").json()
    look = client.post(
        "/api/draws/lookup", json={"ticket_number": "999999"}
    ).json()
    assert look["status"] == "unknown"
    r = client.post(
        "/api/draws",
        json={"prize_id": current["id"], "ticket_number": "999999"},
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "ticket_unknown"


def test_already_won_requires_override(client, station, open_sales):
    _setup_prizes(client)
    sale = _sell(client, station["id"], "Mary", "Jones", 5)
    ticket = sale["ticket_numbers"][0]
    prizes = client.get("/api/prizes").json()

    # Win prize 1.
    r1 = client.post(
        "/api/draws",
        json={"prize_id": prizes[0]["id"], "ticket_number": ticket},
    )
    assert r1.status_code == 200

    # Same ticket cannot win prize 2 without override.
    r2 = client.post(
        "/api/draws",
        json={"prize_id": prizes[1]["id"], "ticket_number": ticket},
    )
    assert r2.status_code == 400
    assert r2.json()["error"]["code"] == "ticket_already_won"

    # With admin override it works.
    r3 = client.post(
        "/api/draws",
        json={
            "prize_id": prizes[1]["id"],
            "ticket_number": ticket,
            "allow_already_won": True,
        },
        headers=ADMIN,
    )
    assert r3.status_code == 200


def test_redraw_preserves_history(client, station, open_sales):
    _setup_prizes(client)
    sale = _sell(client, station["id"], "Mary", "Jones", 5)
    ticket = sale["ticket_numbers"][0]
    prize = client.get("/api/prizes/current").json()

    client.post(
        "/api/draws",
        json={"prize_id": prize["id"], "ticket_number": ticket},
    )
    # Redraw.
    rd = client.post(
        f"/api/prizes/{prize['id']}/redraw",
        json={"reason": "no show"},
        headers=ADMIN,
    )
    assert rd.status_code == 200
    assert rd.json()["status"] == "REDRAW_REQUIRED"
    assert rd.json()["winner_name"] is None

    # Draw history preserved (one VOID draw).
    hist = client.get("/api/reports/drawing-history").text
    assert "VOID" in hist

    # New winner links as redraw.
    sale2 = _sell(client, station["id"], "Bob", "Smith", 5)
    new_ticket = sale2["ticket_numbers"][0]
    again = client.post(
        "/api/draws",
        json={"prize_id": prize["id"], "ticket_number": new_ticket},
    )
    assert again.status_code == 200
    assert again.json()["winner_name"] == "Bob Smith"


def test_claim_workflow(client, station, open_sales):
    _setup_prizes(client)
    sale = _sell(client, station["id"], "Mary", "Jones", 5)
    ticket = sale["ticket_numbers"][0]
    prize = client.get("/api/prizes/current").json()
    client.post(
        "/api/draws",
        json={"prize_id": prize["id"], "ticket_number": ticket},
    )

    # Search by ticket in pickup.
    found = client.get(f"/api/winners/search?q={ticket}").json()
    assert len(found) == 1
    assert found[0]["winner_name"] == "Mary Jones"

    # Unclaimed before claim.
    assert len(client.get("/api/winners/unclaimed").json()) == 1

    claim = client.post(
        f"/api/prizes/{prize['id']}/claim",
        json={"verified_by": "volunteer"},
    )
    assert claim.status_code == 200
    assert claim.json()["status"] == "CLAIMED"

    # No longer unclaimed.
    assert len(client.get("/api/winners/unclaimed").json()) == 0

    # Double claim rejected.
    again = client.post(
        f"/api/prizes/{prize['id']}/claim", json={"verified_by": "v"}
    )
    assert again.status_code == 409


def test_session_logic(client, station, open_sales):
    csv = "prize_number,name,session,pickup_station\n"
    csv += "1,S1 Prize,1,A\n10,S2 Prize,2,B\n"
    client.post("/api/prizes/import", json={"content": csv}, headers=ADMIN)

    # Session 1 current prize.
    cur = client.get("/api/prizes/current").json()
    assert cur["session_number"] == 1

    # Switch to session 2.
    client.post(
        "/api/admin/session/start", json={"session_number": 2}, headers=ADMIN
    )
    cur2 = client.get("/api/prizes/current").json()
    assert cur2["session_number"] == 2
