"""Application configuration loaded from environment variables.

All settings have sensible defaults so the app runs with zero configuration.
"""
import os
from functools import lru_cache


def _get_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def _get_int(name: str, default: int) -> int:
    val = os.getenv(name)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        return default


class Settings:
    """Runtime configuration. Instantiated once and cached."""

    APP_NAME: str = os.getenv("APP_NAME", "Picnic Raffle Manager")

    # Authentication PINs (kept intentionally simple for volunteers).
    ADMIN_PIN: str = os.getenv("ADMIN_PIN", "1234")
    VOLUNTEER_PIN: str = os.getenv("VOLUNTEER_PIN", "0000")

    # Database. SQLite by default; set DATABASE_URL for PostgreSQL, etc.
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "sqlite:////data/raffle.db"
    )
    # Separate database used when DEMO_MODE is active.
    DEMO_DATABASE_URL: str = os.getenv(
        "DEMO_DATABASE_URL", "sqlite:////data/raffle-demo.db"
    )
    DEMO_MODE: bool = _get_bool("DEMO_MODE", False)

    # Backups.
    BACKUP_DIR: str = os.getenv("BACKUP_DIR", "/data/backups")
    BACKUP_INTERVAL: int = _get_int("BACKUP_INTERVAL", 15)  # minutes
    ENABLE_PERIODIC_BACKUP: bool = _get_bool("ENABLE_PERIODIC_BACKUP", True)

    # Display behaviour.
    DISPLAY_ROTATION_SECONDS: int = _get_int("DISPLAY_ROTATION_SECONDS", 8)
    NEW_WINNER_HIGHLIGHT_SECONDS: int = _get_int(
        "NEW_WINNER_HIGHLIGHT_SECONDS", 9
    )
    WINNERS_PER_PAGE: int = _get_int("WINNERS_PER_PAGE", 8)

    # Raffle rules.
    ALLOW_REPEAT_TICKET_WINNERS: bool = _get_bool(
        "ALLOW_REPEAT_TICKET_WINNERS", False
    )

    @property
    def active_database_url(self) -> str:
        return self.DEMO_DATABASE_URL if self.DEMO_MODE else self.DATABASE_URL


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
