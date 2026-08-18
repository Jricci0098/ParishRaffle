from sqlalchemy import Column, String

from ..database.base import Base


class Setting(Base):
    """Simple key/value store for mutable runtime state.

    Used for things like whether ticket sales are open, the current session,
    the public display mode and announcement text.
    """

    __tablename__ = "settings"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=True)
