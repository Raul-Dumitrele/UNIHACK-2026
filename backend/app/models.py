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
    suprafata_mp: int | None = None
    cartier: str | None = None
    sursa: str | None = None
    sursa_detalii: str | None = None
    status_verificare: str | None = None
    descriere: str | None = None


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
    mesaj: str | None = None


class Notification(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(foreign_key="user.id", index=True)
    idea_id: str = Field(foreign_key="idea.id")
    booking_id: str | None = Field(default=None, foreign_key="booking.id")
    proiect_id: str | None = Field(default=None, foreign_key="proiect.id")
    mesaj: str
    citita: bool = False
    created_at: datetime = Field(default_factory=now_utc)


class Proiect(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    idea_id: str = Field(foreign_key="idea.id", index=True)
    space_id: str = Field(foreign_key="space.id", index=True)
    autor_id: str = Field(foreign_key="user.id", index=True)
    verificator_id: str | None = Field(default=None, foreign_key="user.id", index=True)
    tip_amenajare: str
    suprafata_mp: int
    is_demo: bool = False
    stare: str = "draft"  # ProiectStare
    dosar: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    referinte: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    cost: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class ProiectEveniment(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    proiect_id: str = Field(foreign_key="proiect.id", index=True)
    user_id: str = Field(foreign_key="user.id")
    stare_noua: str
    mesaj: str | None = None
    created_at: datetime = Field(default_factory=now_utc)
