"""Pydantic request/response schemas."""
from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


# ----- Auth -----
class PinLogin(BaseModel):
    pin: str


# ----- Stations -----
class StationCreate(BaseModel):
    name: str
    ticket_range_start: int
    ticket_range_end: int
    ticket_width: int = 6
    active: bool = True


class StationUpdate(BaseModel):
    name: Optional[str] = None
    ticket_range_start: Optional[int] = None
    ticket_range_end: Optional[int] = None
    next_ticket_number: Optional[int] = None
    ticket_width: Optional[int] = None
    active: Optional[bool] = None


# ----- Sales -----
class SaleCreate(BaseModel):
    station_id: int
    first_name: str = ""
    last_name: str = ""
    quantity: int = Field(gt=0, le=500)
    device: Optional[str] = None


class ManualTicketEntry(BaseModel):
    first_name: str = ""
    last_name: str = ""
    starting_ticket: int
    quantity: int = Field(gt=0, le=500)
    ticket_width: int = 6
    station_id: Optional[int] = None


class UndoSale(BaseModel):
    station_id: int
    device: Optional[str] = None


# ----- Prizes -----
class PrizeCreate(BaseModel):
    prize_number: int
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    session_number: int = 1
    pickup_station: Optional[str] = None
    sort_order: Optional[int] = None


class PrizeUpdate(BaseModel):
    prize_number: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    session_number: Optional[int] = None
    pickup_station: Optional[str] = None
    sort_order: Optional[int] = None


class PrizeReorder(BaseModel):
    ordered_ids: list[int]


class CsvImport(BaseModel):
    content: str


# ----- Draws -----
class LookupRequest(BaseModel):
    ticket_number: str


class ConfirmWinner(BaseModel):
    prize_id: int
    ticket_number: str
    allow_unsold: bool = False
    allow_already_won: bool = False
    manual_first_name: Optional[str] = None
    manual_last_name: Optional[str] = None
    device: Optional[str] = None


class RedrawRequest(BaseModel):
    reason: str = ""


# ----- Claims -----
class ClaimRequest(BaseModel):
    verified_by: str = "volunteer"
    notes: str = ""
    device: Optional[str] = None


# ----- Admin / state -----
class DisplayMode(BaseModel):
    mode: str
    announcement_text: Optional[str] = None


class SessionAction(BaseModel):
    session_number: int


# ----- Setup wizard -----
class EventCreate(BaseModel):
    name: str
    event_date: Optional[date] = None


class SetupWizard(BaseModel):
    event_name: str
    event_date: Optional[date] = None
    stations: list[StationCreate] = []
    sessions: int = 1
