# Running Picnic Raffle Manager on a Raspberry Pi

The app is a natural fit for a Pi: one small server on a local network, no
Internet required. This guide runs the **Python backend natively** and serves a
**frontend you build on another machine** — the Pi has enough power to *run*
the app comfortably but not enough RAM (1 GB on Pi 2/3) to *build* the frontend
reliably.

For what each screen does and how volunteers use the app, see the main
[README](../README.md). This guide is only about getting it onto a Pi.

## 1. Which Pi / OS

- **Recommended: Raspberry Pi 3 B+ on 64-bit Raspberry Pi OS (Bookworm).** The
  64-bit OS means every Python dependency installs from a prebuilt wheel (no
  slow source builds), Docker images are available, and Wi-Fi is built in.
  Bookworm ships **Python 3.11**, which the app requires (it uses `X | None`
  type hints, so **Python ≥ 3.10** is mandatory — Bullseye's 3.9 will not run
  it).
- **Pi 2, or a Pi 3 on the 32-bit OS**, also works but is 32-bit only: use the
  lean install in step 4b, skip Docker on the device, and (Pi 2) add a USB
  Wi-Fi dongle or use Ethernet.

Give the Pi a **reserved/static IP** on your router so the URL volunteers type
doesn't change mid-event.

## 2. Storage: prefer a USB SSD, and protect against power loss

An SD card's real weakness on a Pi is **corruption on an unclean power-off**
(someone trips over the cord mid-write) — not speed. This app's write volume is
tiny, so you are never I/O-bound; you are protecting against a dead card.

- **Best:** run from a **USB SSD**. On a Pi 3 the USB is 2.0 (~30–40 MB/s cap),
  so any small SSD is plenty — the win is durability and power-loss resilience,
  not throughput.
- **Power:** use a quality 2.5 A+ PSU, and ideally a small **UPS** (UPS HAT or a
  pass-through power bank) so an accidental unplug can't corrupt data mid-write.
  This is the single highest-value reliability step.
- Keep at least one **backup off the device** (see step 9).

Mount the SSD (or a data partition) as **ext4** with `noatime` — do **not** use
exFAT/FAT for the database; SQLite needs proper `fsync` semantics:

```bash
sudo mkdir -p /mnt/ssd
sudo blkid                       # find the SSD's UUID
# add to /etc/fstab (one line), then `sudo mount -a`:
#   UUID=<uuid>  /mnt/ssd  ext4  defaults,noatime  0  2
sudo chown "$USER" /mnt/ssd
```

Optional, to cut background SD writes: send system logs to RAM
(`sudo apt install log2ram`, or set `Storage=volatile` in
`/etc/systemd/journald.conf`).

## 3. Build the frontend on your PC and copy it over

The Pi does not have the RAM to run the Vite/TypeScript build reliably. Build it
on your laptop:

```bash
cd frontend
npm ci
npm run build            # -> frontend/dist
scp -r dist <pi-user>@<pi-ip>:~/ParishRaffle/frontend/dist
```

Put `dist` wherever you like on the Pi; just point `STATIC_DIR` (step 5) at that
exact path. The rest of this guide assumes `~/ParishRaffle/frontend/dist`.

## 4. Install the backend on the Pi

```bash
git clone https://github.com/Jricci0098/ParishRaffle.git
cd ParishRaffle/backend
python3 -m venv .venv
. .venv/bin/activate
```

**4a. 64-bit OS (recommended):** the pinned requirements install cleanly.

```bash
pip install -r requirements.txt
```

**4b. 32-bit OS (Pi 2 / 32-bit Pi 3):** skip the heavy/ARM-unfriendly extras
(`uvicorn[standard]`'s compiled parts and the Postgres driver you don't need
with SQLite):

```bash
pip install "fastapi==0.115.6" "uvicorn==0.34.0" "sqlalchemy==2.0.36" \
            "pydantic==2.10.4" "python-multipart==0.0.20" "websockets==14.1"
```

## 5. Configuration

Create `/etc/picnic-raffle.env` (readable only by root) with your PINs and
paths. Note that the default `DATABASE_URL` points at a Docker path (`/data`),
so on a bare Pi you must set it to a real writable location — ideally on the
SSD.

```bash
sudo tee /etc/picnic-raffle.env >/dev/null <<'EOF'
APP_NAME=Parish Picnic Raffle
ADMIN_PIN=CHANGE_ME
VOLUNTEER_PIN=CHANGE_ME
DATABASE_URL=sqlite:////mnt/ssd/raffle.db
BACKUP_DIR=/mnt/ssd/backups
STATIC_DIR=/home/pi/ParishRaffle/frontend/dist
ENABLE_PERIODIC_BACKUP=true
EOF
sudo chmod 600 /etc/picnic-raffle.env
```

(If you kept everything on the SD card, use e.g.
`DATABASE_URL=sqlite:////home/pi/raffle.db` and `BACKUP_DIR=/home/pi/backups`.)

## 6. Test it once by hand

```bash
cd ~/ParishRaffle/backend && . .venv/bin/activate
set -a; . /etc/picnic-raffle.env; set +a
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

From another device on the same network, open `http://<pi-ip>:8000` and run the
Setup Wizard. Stop it with Ctrl-C once you've confirmed it works, then set up
auto-start below.

## 7. Run on boot with systemd

A ready-made unit is in [`../deploy/picnic-raffle.service`](../deploy/picnic-raffle.service).
Edit the `User`, `WorkingDirectory`, and `ExecStart` paths to match your install
(the Raspberry Pi OS default user is often `pi`, but yours may differ), then:

```bash
sudo cp ~/ParishRaffle/deploy/picnic-raffle.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now picnic-raffle
systemctl status picnic-raffle          # should be active (running)
journalctl -u picnic-raffle -f          # live logs
```

`Restart=on-failure` brings it back if it crashes, and `enable` starts it on
every boot — so a power blip during the event recovers on its own.

## 8. Connect the devices

Every Chromebook / tablet / TV opens `http://<pi-ip>:8000` and picks its screen.
Press **F11** for full-screen kiosk mode. See the main README's *Local network
setup* section for per-device tips.

## 9. Backups and recovery

The app writes timestamped SQLite backups to `BACKUP_DIR` at startup, before
drawing, and every 15 minutes, and the Admin dashboard has a **Download Backup**
button. For a one-day event those writes are negligible — leave them on.

- Periodically copy one backup **off the Pi** (Download Backup → laptop, or
  `scp` from `BACKUP_DIR`). A dead card/SSD then isn't a dead raffle.
- To restore: stop the service, replace the DB file at your `DATABASE_URL` path
  with a backup, start the service.

## 10. Security

On a trusted LAN the defaults are correct: the volunteer screens are
unauthenticated so nobody fights a login mid-event (see the README's *Security
model* section). **Only** if the Pi is reachable from the public Internet, set
`REQUIRE_PIN_FOR_WRITES=true` in `/etc/picnic-raffle.env` to require the
volunteer/admin PIN on the sale/draw/claim endpoints, and restart the service.

## 11. Updating

Rebuild the frontend on your PC and copy `dist` over (step 3), `git pull` on the
Pi, reinstall backend deps if `requirements.txt` changed, then:

```bash
sudo systemctl restart picnic-raffle
```
