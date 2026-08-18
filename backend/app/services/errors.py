"""Domain-specific exceptions mapped to HTTP responses in the API layer."""


class RaffleError(Exception):
    """Base class. ``code`` is a stable machine-readable identifier."""

    status_code = 400
    code = "raffle_error"

    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code


class SalesClosedError(RaffleError):
    code = "sales_closed"


class StationInactiveError(RaffleError):
    code = "station_inactive"


class RangeExhaustedError(RaffleError):
    code = "range_exhausted"


class NotFoundError(RaffleError):
    status_code = 404
    code = "not_found"


class DuplicateError(RaffleError):
    status_code = 409
    code = "duplicate"


class TicketUnknownError(RaffleError):
    code = "ticket_unknown"


class TicketUnsoldError(RaffleError):
    code = "ticket_unsold"


class TicketAlreadyWonError(RaffleError):
    code = "ticket_already_won"


class AuthError(RaffleError):
    status_code = 401
    code = "auth_error"
