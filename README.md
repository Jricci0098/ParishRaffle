# 🎟️ Picnic Raffle Manager

A parish picnic raffle sells hundreds of physical tickets across several tables,
then draws 60–100 prizes in front of a crowd. The bottleneck is the draw: a
number is called, and someone has to find the matching name in a pile of paper
stubs while everyone waits. **Picnic Raffle Manager** removes that lookup —
tickets are recorded as they're sold, and when a number is drawn the winner's
name appears instantly on the volunteers' screens and on the TVs.

It's built for **non-technical volunteers on whatever devices are on hand**
(Chromebooks, tablets, phones), and it's **local-first**: the whole system runs
on one laptop plus a wireless router, with no Internet required — event Wi-Fi
usually isn't available or trustworthy. Physical stubs remain the source of
truth; the app speeds up the lookup, it doesn't replace "you must present the
winning ticket to claim."

---

## What the application does

It automates the whole raffle workflow:

```
ticket sale → buyer/ticket association → drawing → winner lookup
→ live TV display → prize pickup → claimed / unclaimed tracking
```

Participants still keep and present their **physical** ticket stubs — the app
does not replace the physical ticket. It simply removes the manual paper lookup
when a winning number is drawn, and shows winners live on the televisions.

### Screens

| Route            | Screen              | For                              |
| ---------------- | ------------------- | -------------------------------- |
| `/`              | Home                | Pick this device's screen        |
| `/sales`         | Ticket Sales        | Selling stations                 |
| `/drawing`       | Drawing Console     | The person running the draw      |
| `/display`       | Public TV Display   | Televisions (no login)           |
| `/pickup`        | Prize Pickup        | Prize hand-out stations          |
| `/unclaimed`     | Unclaimed Winners   | Chasing down unclaimed prizes    |
| `/admin`         | Admin Dashboard     | Raffle administrator (PIN)       |
| `/admin/prizes`  | Prize Management     | Add/edit/import prizes           |
| `/admin/reports` | Reporting / Export  | CSV exports & ticket import      |
| `/admin/setup`   | Setup Wizard        | First-time setup                 |
| `/admin/demo`    | Demo / Dry Run      | Practice run on a separate DB    |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     One local server                      │
│                                                           │
│   FastAPI (Python)                React SPA (built)       │
│   ├─ REST API   /api/*     ◄──►   served as static files │
│   ├─ WebSocket  /ws  ──────────►  live updates to all     │
│   └─ SQLAlchemy → SQLite (default) or PostgreSQL          │
│                                                           │
│   Data + timestamped backups persisted on the /data volume│
└─────────────────────────────────────────────────────────┘
        ▲            ▲            ▲            ▲
     Sales       Drawing        TVs        Pickup
   Chromebook     laptop     (browser)     tablet
```

- **Backend:** Python · FastAPI · SQLAlchemy · SQLite (PostgreSQL optional)
- **Frontend:** React · TypeScript · Vite · Tailwind CSS
- **Live updates:** WebSockets (auto-reconnect + heartbeat)
- **Deployment:** Docker · Docker Compose

The backend serves the built frontend, so **everything runs from a single
server on `http://<server-ip>:8000`**.

---

## Security model & trust boundaries

This app is designed for **one trusted local network at a single event** — the
server and every client (sales tablets, the drawing laptop, the TVs) sit on a
private LAN the organisers control. The auth model is deliberately minimal so
volunteers aren't fighting logins mid-event.

**Authentication.** Two shared PINs, set via environment variables and compared
in constant time (`secrets.compare_digest`):

- **Admin PIN** gates every destructive or event-shaping action: open/close
  sales, start/end sessions, prize create/edit/delete and CSV import, redraw,
  undo-sale, manual ticket entry, winner overrides, backups, and demo reset.
- **Volunteer PIN** applies to the write endpoints only when the flag below is
  on.

There are no user accounts, sessions, or tokens — by design.

**What's unauthenticated, and why.** The read endpoints (winner board, public
display, ticket lookup, CSV report downloads) and the three *volunteer write*
endpoints — record a sale, confirm a winner, mark a prize claimed — are
unauthenticated by default. On a trusted LAN that is the point: every device on
the network is being operated by a volunteer, and a PIN prompt on every sale is
friction with no security benefit against someone already on the wire.

**When the assumption breaks.** Exposed to the public Internet, those write
endpoints become abusable — anyone could record sales or confirm winners. That
boundary is deployment-specific, so it is a switch rather than a hardcoded
assumption:

- **`REQUIRE_PIN_FOR_WRITES=true`** requires the volunteer (or admin) PIN on the
  sale/draw/claim endpoints. **Set it for any Internet-facing deployment.**
- The hosted demo intentionally leaves it **off** so visitors can click through
  the whole flow; it holds only throwaway data (ephemeral SQLite) and its admin
  PIN is set to a non-default value so visitors can't close sales or wipe it.

**Other boundaries, stated plainly:**

- **CORS is `*`** — the server IP varies per venue and all callers are on the
  trusted LAN. Tighten it if you expose the API beyond that.
- **Transport is plain HTTP** on the LAN. For an Internet deployment, terminate
  TLS at a reverse proxy (Cloud Run does this for you).
- **No rate limiting** — a LAN assumption; add it at the proxy if exposed.
- **Integrity is prioritised over access control** here: ticket assignment runs
  under a single-process lock inside one transaction, so concurrent sales can't
  collide — which means the app must run with **one worker / one instance**;
  ticket and prize numbers are `UNIQUE`; every state change is written to an
  **audit log**; and the database is backed up at startup and on an interval.
- **Physical verification stays human:** winners must present the physical stub
  at pickup. The app tracks claimed/unclaimed; it does not authenticate people.

Out of scope: account management, roles beyond the two PINs, and secrets
management — this is a single-event tool, not a multi-tenant service.

---

## 🎬 Demo

A single narrated walkthrough (~3½ min) with title cards and voice-over:
**Setup → Sell & Draw → Live on the TVs**.

[![Narrated end-to-end walkthrough](demo/media/end-to-end-poster.png)](https://github.com/Jricci0098/ParishRaffle/raw/main/demo/media/raffle-end-to-end.mp4)

<video src="https://github.com/Jricci0098/ParishRaffle/raw/main/demo/media/raffle-end-to-end.mp4" poster="https://github.com/Jricci0098/ParishRaffle/raw/main/demo/media/end-to-end-poster.png" controls width="100%"></video>

It's stitched from three clips — first-run setup, the volunteer workflow, and
the live TV board — recorded automatically by the Playwright scripts in
[`demo/`](demo/); only the finished video is committed.

---

## Requirements

- **Docker** and **Docker Compose** (recommended), _or_
- Python 3.11+ and Node.js 20+ for local development.

No cloud services are required to run it — that's the whole point. A separate
[Cloud Run path](#deploy-a-public-demo-to-google-cloud-run) is provided only
for hosting a public demo.

---

## Installation (Docker — recommended)

```bash
# 1. Get the code
git clone https://github.com/Jricci0098/ParishRaffle.git
cd ParishRaffle

# 2. Create your configuration
cp .env.example .env
#    → edit .env and set ADMIN_PIN / VOLUNTEER_PIN

# 3. Build and start
docker compose up -d
```

Open **http://localhost:8000** (or the server's LAN IP from other devices).

To stop: `docker compose down`. Your data stays in the `./data` folder.

> No `sudo` is required if your user is in the `docker` group.

### Using PostgreSQL instead of SQLite (optional)

Set in `.env`:

```
DATABASE_URL=postgresql+psycopg2://raffle:raffle@postgres:5432/raffle
```

then:

```bash
docker compose --profile postgres up -d
```

---

## Deploy a public demo to Google Cloud Run

Cloud Run builds the image with Cloud Build (no local Docker needed) and gives
you a public HTTPS URL.

```bash
# one-time: install gcloud and authenticate
gcloud auth login

# deploy (edit the values or pass them as environment variables)
PROJECT_ID=your-project-id REGION=us-central1 ./deploy/deploy-cloudrun.sh
```

The script enables the required APIs and deploys the service
`--allow-unauthenticated` (public). It prints the URL and the generated **Admin
PIN** at the end.

**Important notes for a public demo:**

- The volunteer screens (`/sales`, `/drawing`, `/pickup`) are intentionally
  unauthenticated — that is what lets visitors play with the demo. Only the
  admin screens are PIN-protected, and the script sets a **non-default admin
  PIN** so visitors cannot close sales or wipe data. For real event use, keep
  the server on a trusted local network rather than the public Internet.
- The service runs as a **single always-on instance** (`--max-instances 1
  --min-instances 1`), because ticket assignment relies on an in-process lock
  and an in-memory SQLite database. Set `--min-instances 0` to save cost; the
  demo data then resets on a cold start.
- SQLite lives under `/tmp` (ephemeral). For durable data, deploy Cloud SQL
  (PostgreSQL) and set `DATABASE_URL` accordingly.

---

## Local development (without Docker)

**Backend:**

```bash
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
# use a local database path so /data is not required
DATABASE_URL=sqlite:///./raffle.db uvicorn app.main:app --reload
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173, proxies /api and /ws to :8000
```

---

## First-time setup

1. Go to **`/admin`** and enter the **Admin PIN**.
2. Open **Setup** (`/admin/setup`) and run the wizard:
   1. Create the event.
   2. Define ticket ranges.
   3. Define sales stations.
   4. Import/create prizes (CSV supported).
   5. Choose the number of sessions.
   6. Review.
   7. Start.
3. On the Admin Dashboard, click **OPEN SALES** when you're ready to sell.

**Prize CSV format** (`/admin/prizes`):

```csv
prize_number,name,session,pickup_station
1,Chocolate Basket,1,A
2,Restaurant Gift Card,1,A
3,School Backpack,1,B
```

**Ticket CSV format** (fallback import, `/admin/reports`):

```csv
ticket_number,first_name,last_name
005001,Mary,Jones
005002,Mary,Jones
```

---

## Local network setup

1. Put the server on the venue's Wi-Fi/LAN and find its IP address
   (e.g. `192.168.1.50`).
2. All devices open **`http://192.168.1.50:8000`**.
3. No Internet connection is needed — everything is served locally.

### Connecting Chromebooks / tablets / laptops

- Open Chrome and browse to `http://<server-ip>:8000`.
- Choose the screen for that device (Sales, Drawing, Pickup…).
- **Tip:** press **F11** (or use "Add to shelf / Open as window") for a clean
  full-screen kiosk view.
- A sales device remembers its **station** even after a refresh.

### Connecting a TV display

- On the TV's browser (or an attached stick/laptop), open
  `http://<server-ip>:8000/display`.
- Press **F11** for full screen. No login is required.
- Mirror the same URL on the second TV — both update live.
- Control what the TVs show from **Admin → Public TV Display** (Latest, All,
  Unclaimed, Session 1/2, or a custom Announcement).

---

## How barcode scanners work

Most USB barcode scanners act as a **keyboard**: they "type" the number and
press **Enter**. No drivers needed.

- On the **Drawing Console** and **Pickup** screens the input field is
  auto-focused. Scan a ticket and it looks up automatically on Enter.
- You can also type numbers by hand.
- Leading zeros are preserved (ticket numbers are stored as text).

---

## How to perform the dry run

1. Start the server with demo mode on:

   ```bash
   # in .env
   DEMO_MODE=true
   ```

   ```bash
   docker compose up -d
   ```

   A separate **demo database** is used, so production data is never touched,
   and every screen shows a **DEMO MODE** banner.

2. Go to **Admin → Demo** and click **GENERATE DEMO DATA**
   (e.g. 100 buyers, 500 tickets, 20 prizes).
3. Practice the whole flow: sale → drawing → TV display → pickup → redraw.
4. Click **RESET DEMO** to clear it.
5. When finished, set `DEMO_MODE=false` and restart for the real event.

---

## How backups work

- SQLite backups are written to `data/backups/` as timestamped files, e.g.
  `raffle-2026-09-20-1400-auto.db`.
- Backups are created **at startup**, **before drawing** (server-side), and
  **every `BACKUP_INTERVAL` minutes** (default 15) while running.
- **Admin → Backup & Export → DOWNLOAD BACKUP** downloads a fresh consistent
  copy of the database to your device at any time.

---

## How to recover from failure

- **A screen was refreshed / a device rebooted:** just reopen the URL. All
  state lives on the server; sales devices remember their station.
- **The server was restarted:** data is on the `./data` volume and reloads
  automatically. `docker compose up -d` brings it back.
- **You need to roll back:** stop the app, replace `data/raffle.db` with a file
  from `data/backups/`, and start again.
- **Total disaster / no power:** print **paper fallback sheets** in advance and
  keep exported CSVs. The physical ticket stubs remain the source of truth.

---

## How to export results

Go to **Admin → Reports** and download any of:

1. All ticket sales
2. Buyers
3. Winners
4. Prizes
5. Claimed prizes
6. Unclaimed prizes
7. Drawing history
8. Session summary

Each is a plain CSV that opens in any spreadsheet program.

---

## Data integrity & fail-safes

- Duplicate ticket numbers and duplicate prize numbers are prevented at the
  database level.
- Ticket assignment is transactional and serialized, so concurrent sales at
  several stations never overlap (see `backend/app/services/sales.py`).
- Sales, winners and draws are **never silently deleted**. Redraws keep the
  previous draw as `VOID` history.
- Destructive actions require confirmation; **Undo Last Sale** requires the
  admin PIN.
- Every significant action is written to an **audit log**
  (Admin Dashboard → Recent Activity).

---

## Configuration reference

All via environment variables (see `.env.example`):

| Variable                       | Default                        | Purpose                                   |
| ------------------------------ | ------------------------------ | ----------------------------------------- |
| `APP_NAME`                     | Picnic Raffle Manager          | Display name                              |
| `ADMIN_PIN`                    | 1234                           | Admin access                              |
| `VOLUNTEER_PIN`                | 0000                           | Volunteer access                          |
| `DATABASE_URL`                 | sqlite:////data/raffle.db      | Database connection                       |
| `DEMO_MODE`                    | false                          | Run against the demo database             |
| `BACKUP_INTERVAL`              | 15                             | Minutes between automatic backups         |
| `DISPLAY_ROTATION_SECONDS`     | 8                              | TV page rotation interval                 |
| `NEW_WINNER_HIGHLIGHT_SECONDS` | 9                              | How long a new winner is spotlighted      |
| `ALLOW_REPEAT_TICKET_WINNERS`  | false                          | Whether one ticket may win multiple prizes|
| `REQUIRE_PIN_FOR_WRITES`       | false                          | Require the volunteer/admin PIN on write endpoints (see Security model) |

---

## Running the tests

**Backend** (23 tests incl. concurrency & the full acceptance flow):

```bash
cd backend
. .venv/bin/activate
pytest
```

**Frontend:**

```bash
cd frontend
npm test
```

---

## Project structure

```
ParishRaffle/
├── backend/
│   ├── app/
│   │   ├── api/           # REST + auth routers
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # business logic (sales, draws, claims, …)
│   │   ├── websocket/     # live-update manager
│   │   ├── database/      # engine & session
│   │   └── main.py        # app entry point
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/    # shared UI
│       ├── pages/         # one per screen
│       ├── hooks/         # useWebSocket, useConfig
│       ├── services/      # API client
│       └── types/
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## API overview

REST endpoints live under `/api` (interactive docs at `/docs`). Highlights:

```
POST /api/sales                     GET  /api/tickets/{ticket_number}
POST /api/draws/lookup              POST /api/draws
GET  /api/prizes/current            POST /api/prizes/{id}/claim
POST /api/prizes/{id}/redraw        GET  /api/winners
GET  /api/winners/unclaimed         GET  /api/reports/{name}
POST /api/admin/sales/open|close    POST /api/admin/display
```

WebSocket events broadcast on `/ws`: `sale.created`, `sales.opened`,
`sales.closed`, `winner.created`, `winner.redrawn`, `prize.claimed`,
`session.started`, `session.ended`, `display.mode.changed`.
