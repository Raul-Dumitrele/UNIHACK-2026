"""Pydantic request/response schemas, exactly as in docs/CONTRACT.md."""
from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, model_validator

Zi = Literal["luni", "marti", "miercuri", "joi", "vineri", "sambata", "duminica"]
Categorie = Literal["sport", "cultura", "educatie", "social", "creativ", "tehnologie", "altele"]
Zgomot = Literal["scazut", "mediu", "ridicat"]
Dotare = Literal[
    "scaune", "mese", "proiector", "wifi", "scena", "oglinzi",
    "vestiare", "bucatarie", "acces_rampa", "curte", "priza", "tabla",
]
IdeaStatus = Literal["deschisa", "prag_atins", "rezervata"]
BookingStatus = Literal["cerut", "aprobat", "refuzat"]
UserRole = Literal["cetatean", "proprietar"]


def _iso_utc(v: datetime) -> str:
    if v.tzinfo is None:
        v = v.replace(tzinfo=timezone.utc)
    return v.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


UtcDatetime = Annotated[datetime, PlainSerializer(_iso_utc, return_type=str)]
HHMM = Annotated[str, Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ErrorOut(BaseModel):
    detail: str


class Slot(BaseModel):
    zi: Zi
    de_la: HHMM
    pana_la: HHMM

    @model_validator(mode="after")
    def _ordered(self) -> "Slot":
        if self.de_la >= self.pana_la:
            raise ValueError("de_la trebuie să fie înainte de pana_la")
        return self


class Structurat(BaseModel):
    categorie: Categorie
    persoane: int = Field(ge=1)
    dotari: list[Dotare] = []
    program: list[Slot] = []
    zgomot: Zgomot
    rezumat: str


class Impact(BaseModel):
    ore_recuperate: float
    oameni_conectati: int
    km_economisiti: float  # estimare
    proiecte_active: int


class UserOut(ORM):
    id: str
    nume: str
    rol: UserRole
    cartier: str
    lat: float
    lng: float


class SpaceOut(ORM):
    id: str
    nume: str
    tip: str
    lat: float
    lng: float
    capacitate: int
    dotari: list[Dotare]
    sloturi: list[Slot]
    owner_id: str
    is_demo: bool


class IdeaCreate(BaseModel):
    descriere: str = Field(min_length=3)
    titlu: str | None = None
    prag: int | None = Field(default=None, ge=1)


class IdeaOut(ORM):
    id: str
    author_id: str
    titlu: str
    descriere: str
    structurat: Structurat
    prag: int
    interesati: int
    stare: IdeaStatus
    is_demo: bool
    created_at: UtcDatetime


class MatchOut(BaseModel):
    space: SpaceOut
    scor: int = Field(ge=0, le=100)
    motiv: str
    suprapunere: list[Slot]


class OwnerMessageIn(BaseModel):
    space_id: str
    slot: Slot


class OwnerMessageOut(BaseModel):
    mesaj: str


class BookingCreate(BaseModel):
    idea_id: str
    space_id: str
    slot: Slot


class BookingUpdate(BaseModel):
    stare: Literal["aprobat", "refuzat"]


class BookingOut(ORM):
    id: str
    idea_id: str
    space_id: str
    slot: Slot
    stare: BookingStatus
    created_at: UtcDatetime


class NotificationOut(ORM):
    id: str
    user_id: str
    idea_id: str
    booking_id: str | None
    mesaj: str
    citita: bool
    created_at: UtcDatetime
