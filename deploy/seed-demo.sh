#!/usr/bin/env bash
#
# Populate a running Picnic Raffle Manager instance with a demo dataset:
# an event, 3 stations, 20 prizes, sample sales, and a few drawn/claimed winners.
#
# Usage:
#   ./deploy/seed-demo.sh BASE_URL ADMIN_PIN
#   ./deploy/seed-demo.sh https://picnic-raffle-207884166310.us-central1.run.app 0068
#
set -euo pipefail

BASE_URL="${1:-${BASE_URL:-http://localhost:8000}}"
ADMIN_PIN="${2:-${ADMIN_PIN:-1234}}"
BASE_URL="${BASE_URL%/}"

A=(-H "X-Admin-Pin: $ADMIN_PIN" -H "Content-Type: application/json")
J=(-H "Content-Type: application/json")

echo "==> Creating event + 3 stations"
curl -fsS "${A[@]}" -d '{
  "event_name":"Saint Paul VI Parish Picnic Raffle 2026","sessions":2,
  "stations":[
    {"name":"Ticket Table 1","ticket_range_start":5000,"ticket_range_end":5199,"ticket_width":6,"active":true},
    {"name":"Ticket Table 2","ticket_range_start":5200,"ticket_range_end":5399,"ticket_width":6,"active":true},
    {"name":"Ticket Table 3","ticket_range_start":5400,"ticket_range_end":5599,"ticket_width":6,"active":true}
  ]}' "$BASE_URL/api/setup/wizard" >/dev/null

echo "==> Opening sales"
curl -fsS "${A[@]}" -X POST "$BASE_URL/api/admin/sales/open" >/dev/null

echo "==> Importing 20 prizes"
names=("Chocolate Basket" "Restaurant Gift Card" "School Backpack" "Coffee Basket" "Wine Gift Set" "Toy Bundle" "Spa Day Package" "Grocery Gift Card" "Family Board Games" "Movie Night Basket" "Gardening Kit" "BBQ Grill Set" "Bakery Gift Box" "Bookstore Voucher" "Sports Equipment" "Handmade Quilt" "Electronics Bundle" "Pizza Party" "Ice Cream Basket" "Local Honey Set")
CSV='prize_number,name,session,pickup_station\n'
for i in $(seq 1 20); do
  s=1; [ "$i" -gt 10 ] && s=2
  case $(((i - 1) % 3)) in 0) p=A;; 1) p=B;; 2) p=C;; esac
  CSV="${CSV}${i},${names[$((i-1))]},${s},${p}\n"
done
curl -fsS "${A[@]}" -d "{\"content\":\"$CSV\"}" "$BASE_URL/api/prizes/import" >/dev/null

# Map stations by range so this works regardless of assigned ids.
read -r S1 S2 S3 < <(curl -fsS "$BASE_URL/api/stations" | python3 -c "
import sys, json
m = {s['ticket_range_start']: s['id'] for s in json.load(sys.stdin)}
print(m.get(5000), m.get(5200), m.get(5400))")

sale() { curl -fsS "${J[@]}" -d "{\"station_id\":$1,\"first_name\":\"$2\",\"last_name\":\"$3\",\"quantity\":$4}" "$BASE_URL/api/sales" >/dev/null; }

echo "==> Creating sample sales"
sale "$S1" Mary Jones 20
sale "$S1" Robert Smith 10
sale "$S1" Susan Williams 5
sale "$S2" James Brown 15
sale "$S2" Patricia Davis 8
sale "$S2" Michael Miller 20
sale "$S3" Linda Wilson 10
sale "$S3" David Anderson 25
sale "$S3" Barbara Thomas 5

# Map prize number -> id.
declare -A PID
while IFS=$'\t' read -r num id; do PID[$num]=$id; done < <(curl -fsS "$BASE_URL/api/prizes" | python3 -c "
import sys, json
for p in json.load(sys.stdin): print(f\"{p['prize_number']}\t{p['id']}\")")

draw() { curl -fsS "${J[@]}" -d "{\"prize_id\":${PID[$1]},\"ticket_number\":\"$2\"}" "$BASE_URL/api/draws" >/dev/null; }
claim() { curl -fsS "${J[@]}" -d '{"verified_by":"volunteer"}' "$BASE_URL/api/prizes/${PID[$1]}/claim" >/dev/null; }

echo "==> Drawing 6 winners (3 claimed, 3 left unclaimed)"
draw 1 005005; draw 2 005025; draw 3 005032
draw 4 005205; draw 5 005410; draw 6 005436
claim 1; claim 2; claim 3

echo
echo "Done. Open:"
echo "  $BASE_URL/display   (TV board)"
echo "  $BASE_URL/drawing   (advances to Prize #7)"
echo "  $BASE_URL/pickup    (search 005205 or a name)"
echo "  $BASE_URL/admin     (PIN $ADMIN_PIN)"
