# 🎟️ Picnic Raffle Manager

A lightweight, **local-first** web application for running a church picnic
raffle — from ticket sale, to drawing, to live TV display, to prize pickup.
Built to be operated by non-technical volunteers on any device on the local
network, and to keep working **even with no Internet access**.

---

## 🎬 Demo

Screen recordings produced automatically by the scripts in
[`demo/`](demo/) — no manual screen capture.

### 🎥 Full narrated walkthrough (3½ min)

One end-to-end video with title cards and voice-over: **Setup → Sell & Draw →
Live on the TVs**.

[![Narrated end-to-end walkthrough](demo/media/end-to-end-poster.png)](https://github.com/Jricci0098/ParishRaffle/raw/main/demo/media/raffle-end-to-end.mp4)

<video src="https://github.com/Jricci0098/ParishRaffle/raw/main/demo/media/raffle-end-to-end.mp4" poster="https://github.com/Jricci0098/ParishRaffle/raw/main/demo/media/end-to-end-poster.png" controls width="100%"></video>

The individual clips below feed into it.

### 🛠️ Setup walkthrough (first run)

Admin login → **Setup Wizard** (event → ticket ranges → stations → sessions →
review → start) → **Prize Management** (add a prize + CSV import) → open sales →
ready to sell.

[![Setup walkthrough](demo/media/setup-poster.png)](https://github.com/Jricci0098/ParishRaffle/raw/main/demo/media/raffle-setup-demo.webm)

<video src="https://github.com/Jricci0098/ParishRaffle/raw/main/demo/media/raffle-setup-demo.webm" poster="https://github.com/Jricci0098/ParishRaffle/raw/main/demo/media/setup-poster.png" controls width="100%"></video>

### ▶️ In action

| Public TV display — live winner board | Volunteer workflow — sale → draw → pickup |
| :-----------------------------------: | :---------------------------------------: |
| [![TV display demo](demo/media/tv-display-poster.png)](https://github.com/Jricci0098/ParishRaffle/raw/main/demo/media/raffle-tv-display-demo.webm) | [![Operator demo](demo/media/operator-poster.png)](https://github.com/Jricci0098/ParishRaffle/raw/main/demo/media/raffle-operator-demo.webm) |

**▶ Click a thumbnail to play** (WebM — plays in Chrome, Edge, Firefox, VLC).
On github.com the players can also embed inline:

<video src="https://github.com/Jricci0098/ParishRaffle/raw/main/demo/media/raffle-tv-display-demo.webm" poster="https://github.com/Jricci0098/ParishRaffle/raw/main/demo/media/tv-display-poster.png" controls width="100%"></video>

<video src="https://github.com/Jricci0098/ParishRaffle/raw/main/demo/media/raffle-operator-demo.webm" poster="https://github.com/Jricci0098/ParishRaffle/raw/main/demo/media/operator-poster.png" controls width="100%"></video>

Regenerate them against any running instance — see [`demo/README.md`](demo/README.md).

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

## Requirements

- **Docker** and **Docker Compose** (recommended), _or_
- Python 3.11+ and Node.js 20+ for local development.

No cloud services are required.

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
