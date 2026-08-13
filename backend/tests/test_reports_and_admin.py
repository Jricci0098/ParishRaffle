"""Tests for CSV export, ticket import, admin state, acceptance flow."""
from .conftest import ADMIN


def test_export_reports(client, station, open_sales):
    client.post(
        "/api/sales",
        json={
            "station_id": station["id"],
            "first_name": "Mary",
            "last_name": "Jones",
            "quantity": 3,
        },
    )
    for name in [
        "ticket-sales",
        "buyers",
        "winners",
        "prizes",
        "claimed",
        "unclaimed",
        "drawing-history",
        "session-summary",
    ]:
        r = client.get(f"/api/reports/{name}")
        assert r.status_code == 200, name
        assert r.headers["content-type"].startswith("text/csv")

    sales_csv = client.get("/api/reports/ticket-sales").text
    assert "005000" in sales_csv
    assert "Mary Jones" in sales_csv


def test_ticket_import_csv(client):
    csv = "ticket_number,first_name,last_name\n"
    csv += "005001,Mary,Jones\n005002,Mary,Jones\n005003,Robert,Smith\n"
    r = client.post("/api/imports/tickets", json={"content": csv}, headers=ADMIN)
    assert r.status_code == 200, r.text
    assert r.json()["created"] == 3

    t = client.get("/api/tickets/005003").json()
    assert t["buyer"]["display_name"] == "Robert Smith"


def test_sales_open_close(client, station):
    assert client.get("/api/sales/status").json()["sales_open"] is False
    client.post("/api/admin/sales/open", headers=ADMIN)
    assert client.get("/api/sales/status").json()["sales_open"] is True
    client.post("/api/admin/sales/close", headers=ADMIN)
    assert client.get("/api/sales/status").json()["sales_open"] is False


def test_admin_requires_pin(client):
    r = client.post("/api/admin/sales/open")
    assert r.status_code == 401
    r2 = client.post("/api/admin/sales/open", headers={"X-Admin-Pin": "wrong"})
    assert r2.status_code == 401


def test_summary(client, station, open_sales):
    client.post(
        "/api/sales",
        json={
            "station_id": station["id"],
            "first_name": "Mary",
            "last_name": "Jones",
            "quantity": 5,
        },
    )
    s = client.get("/api/admin/summary").json()
    assert s["tickets_sold"] == 5
    assert s["buyers"] == 1


def test_full_acceptance_flow(client):
    """Mirror the acceptance test in the requirements."""
    # 1-2. Create station with range 5000-5199.
    st = client.post(
        "/api/stations",
        json={
            "name": "Ticket Table 1",
            "ticket_range_start": 5000,
            "ticket_range_end": 5199,
            "ticket_width": 6,
        },
        headers=ADMIN,
    ).json()
    client.post("/api/admin/sales/open", headers=ADMIN)

    # 4-5. Mary buys 20 -> 005000-005019.
    mary = client.post(
        "/api/sales",
        json={
            "station_id": st["id"],
            "first_name": "Mary",
            "last_name": "Jones",
            "quantity": 20,
        },
    ).json()
    assert mary["first_ticket"] == "005000"
    assert mary["last_ticket"] == "005019"

    # 6-7. Robert buys 10 -> 005020-005029.
    rob = client.post(
        "/api/sales",
        json={
            "station_id": st["id"],
            "first_name": "Robert",
            "last_name": "Smith",
            "quantity": 10,
        },
    ).json()
    assert rob["first_ticket"] == "005020"
    assert rob["last_ticket"] == "005029"

    # 8. Import 20 prizes.
    csv = "prize_number,name,session,pickup_station\n"
    for i in range(1, 21):
        csv += f"{i},Prize {i},1,A\n"
    client.post("/api/prizes/import", json={"content": csv}, headers=ADMIN)

    # 10. Prize #1 current.
    current = client.get("/api/prizes/current").json()
    assert current["prize_number"] == 1

    # 11-12. Type 005005 -> Mary Jones.
    look = client.post(
        "/api/draws/lookup", json={"ticket_number": "005005"}
    ).json()
    assert look["buyer"]["display_name"] == "Mary Jones"

    # 13-14. Confirm winner.
    view = client.post(
        "/api/draws",
        json={"prize_id": current["id"], "ticket_number": "005005"},
    ).json()
    assert view["winner_name"] == "Mary Jones"

    # 15-16. Pickup searches 005005.
    found = client.get("/api/winners/search?q=005005").json()
    assert found[0]["winner_name"] == "Mary Jones"
    assert found[0]["prize_number"] == 1

    # 17-19. Mark picked up -> CLAIMED.
    claimed = client.post(
        f"/api/prizes/{current['id']}/claim",
        json={"verified_by": "volunteer"},
    ).json()
    assert claimed["status"] == "CLAIMED"

    # 21. Export final report.
    report = client.get("/api/reports/winners").text
    assert "Mary Jones" in report
    assert "005005" in report
