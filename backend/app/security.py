"""Security helpers."""
import secrets


def pin_matches(candidate: str | None, expected: str | None) -> bool:
    """Constant-time PIN/secret comparison.

    Uses ``secrets.compare_digest`` so the comparison time does not leak how
    many leading characters matched. Returns ``False`` for empty inputs rather
    than raising.
    """
    if not candidate or not expected:
        return False
    return secrets.compare_digest(str(candidate), str(expected))
