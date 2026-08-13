"""Tests for ticket sales: sequential assignment, ranges, undo, concurrency."""
from concurrent.futures import ThreadPoolExecutor

from .conftest import ADMIN


def _sale(client, station_id, first, last, qty):
    return client.post(
        "/api/sales",
        json={
            "station_id": station_id,
            "first_name": first,
            "last_name": last,
            "quantity": qty,
        },
    )


def test_sequential_ticket_assignment(client, station, open_sales):
    r = _sale(client, station["id"], "Mary", "Jones", 20)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["first_ticket"] == "005000"
    assert data["last_ticket"] == "005019"
    assert len(data["ticket_numbers"]) == 20

    r2 = _sale(client, station["id"], "Robert", "Smith", 10)
    d2 = r2.json()
    assert d2["first_ticket"] == "005020"
    assert d2["last_ticket"] == "005029"


def test_leading_zeros_preserved(client, station, open_sales):
    r = _sale(client, station["id"], "A", "B", 1)
    assert r.json()["first_ticket"] == "005000"


def test_sales_closed_blocks_sale(client, station):
    # Sales are closed by default.
    r = _sale(client, station["id"], "Mary", "Jones", 1)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "sales_closed"


def test_range_exhaustion(client, open_sales):
    r = client.post(
        "/api/stations",
        json={
            "name": "Tiny",
            "ticket_range_start": 1,
            "ticket_range_end": 5,
            "ticket_width": 6,
        },
        headers=ADMIN,
    )
    sid = r.json()["id"]
    ok = _sale(client, sid, "A", "B", 5)
    assert ok.status_code == 200
    over = _sale(client, sid, "C", "D", 1)
    assert over.status_code == 400
    assert over.json()["error"]["code"] == "range_exhausted"


def test_no_overlap_at_boundary(client, open_sales):
    r = client.post(
        "/api/stations",
        json={
            "name": "Small",
            "ticket_range_start": 100,
            "ticket_range_end": 104,
            "ticket_width": 6,
        },
        headers=ADMIN,
    )
    sid = r.json()["id"]
    a = _sale(client, sid, "A", "A", 3)
    assert a.json()["last_ticket"] == "000102"
    b = _sale(client, sid, "B", "B", 2)
    assert b.json()["first_ticket"] == "000103"
    assert b.json()["last_ticket"] == "000104"
    # Range now exhausted.
    c = _sale(client, sid, "C", "C", 1)
    assert c.status_code == 400


def test_concurrent_sales_no_duplicates(client, station, open_sales):
    """Multiple simultaneous sales at one station must not overlap."""
    sid = station["id"]

    def buy(i):
        return _sale(client, sid, f"Buyer{i}", "X", 5)

    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(buy, range(8)))

    all_numbers = []
    for r in results:
        assert r.status_code == 200, r.text
        all_numbers.extend(r.json()["ticket_numbers"])

    # 8 sales x 5 tickets = 40 unique numbers, no duplicates.
    assert len(all_numbers) == 40
    assert len(set(all_numbers)) == 40


def test_undo_last_sale(client, station, open_sales):
    sid = station["id"]
    _sale(client, sid, "Mary", "Jones", 5)
    r = client.post(
        "/api/sales/undo", json={"station_id": sid}, headers=ADMIN
    )
    assert r.status_code == 200, r.text
    # Next sale should reuse the freed numbers.
    nxt = _sale(client, sid, "New", "Buyer", 1)
    assert nxt.json()["first_ticket"] == "005000"


def test_undo_requires_admin(client, station, open_sales):
    sid = station["id"]
    _sale(client, sid, "Mary", "Jones", 5)
    r = client.post("/api/sales/undo", json={"station_id": sid})
    assert r.status_code == 401


def test_manual_ticket_entry(client):
    r = client.post(
        "/api/sales/manual",
        json={
            "first_name": "Manual",
            "last_name": "Buyer",
            "starting_ticket": 7845,
            "quantity": 5,
            "ticket_width": 6,
        },
        headers=ADMIN,
    )
    assert r.status_code == 200, r.text
    nums = r.json()["ticket_numbers"]
    assert nums == ["007845", "007846", "007847", "007848", "007849"]
