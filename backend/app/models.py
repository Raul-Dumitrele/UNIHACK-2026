"""SQLModel tables, from docs/CONTRACT.md. Complex fields are stored as JSON."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, SQLModel


def new_id() -> str:
    return str(uuid.uuid4())


def now_utc() -> datetime:
    # SQLModel's datetime column requires tz-aware values; always UTC.
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    nume: str
    rol: str = "cetatean"  # UserRole
    cartier: str = ""
    lat: float
    lng: float


class Space(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    nume: str
    tip: str = ""
    lat: float
    lng: float
    capacitate: int = 0
    dotari: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    sloturi: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    owner_id: str = Field(foreign_key="user.id", index=True)
    is_demo: bool = False


class Idea(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    author_id: str = Field(foreign_key="user.id", index=True)
    titlu: str
    descriere: str
    structurat: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    prag: int = 5
    interesati: int = 0
    stare: str = "deschisa"  # IdeaStatus
    is_demo: bool = False
    created_at: datetime = Field(default_factory=now_utc)


class Interest(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("user_id", "idea_id", name="uq_interest_user_idea"),)

    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(foreign_key="user.id", index=True)
    idea_id: str = Field(foreign_key="idea.id", index=True)
    created_at: datetime = Field(default_factory=now_utc)


class Booking(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    idea_id: str = Field(foreign_key="idea.id", index=True)
    space_id: str = Field(foreign_key="space.id", index=True)
    slot: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    stare: str = "cerut"  # BookingStatus
    created_at: datetime = Field(default_factory=now_utc)


class Notification(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(foreign_key="user.id", index=True)
    idea_id: str = Field(foreign_key="idea.id")
    booking_id: str | None = Field(default=None, foreign_key="booking.id")
    mesaj: str
    citita: bool = False
    created_at: datetime = Field(default_factory=now_utc)
