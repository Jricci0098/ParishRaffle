"""Database backups.

For SQLite we use the online backup API so a consistent copy is written even
while the raffle is running. Backups are timestamped in ``BACKUP_DIR``.
Periodic backups are scheduled from ``main.py``.
"""
import os
import shutil
import sqlite3
from datetime import datetime

from ..config import settings
from ..database.base import DATABASE_URL, engine


def _sqlite_path() -> str | None:
    if not DATABASE_URL.startswith("sqlite"):
        return None
    path = DATABASE_URL.replace("sqlite:///", "", 1)
    return path or None


def create_backup(label: str = "") -> str | None:
    """Create a timestamped backup. Returns the file path (or None)."""
    src = _sqlite_path()
    if not src or not os.path.exists(src):
        return None

    os.makedirs(settings.BACKUP_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    suffix = f"-{label}" if label else ""
    dest = os.path.join(settings.BACKUP_DIR, f"raffle-{stamp}{suffix}.db")

    source = sqlite3.connect(src)
    try:
        target = sqlite3.connect(dest)
        try:
            source.backup(target)
        finally:
            target.close()
    finally:
        source.close()
    return dest


def latest_backup_path() -> str | None:
    src = _sqlite_path()
    if not src or not os.path.exists(src):
        return None
    # Create an on-demand consistent snapshot for download.
    return create_backup(label="download")


def list_backups() -> list[dict]:
    if not os.path.isdir(settings.BACKUP_DIR):
        return []
    items = []
    for name in sorted(os.listdir(settings.BACKUP_DIR), reverse=True):
        full = os.path.join(settings.BACKUP_DIR, name)
        if os.path.isfile(full) and name.endswith(".db"):
            items.append(
                {
                    "name": name,
                    "size": os.path.getsize(full),
                    "modified": datetime.fromtimestamp(
                        os.path.getmtime(full)
                    ).isoformat(),
                }
            )
    return items
