"""Pydantic request/response schemas, exactly as in docs/CONTRACT.md."""
from datetime import date, datetime, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, create_model, model_validator

Zi = Literal["luni", "marti", "miercuri", "joi", "vineri", "sambata", "duminica"]
Categorie = Literal["sport", "cultura", "educatie", "social", "creativ", "tehnologie", "altele"]
Zgomot = Literal["scazut", "mediu", "ridicat"]
Dotare = Literal[
    "scaune", "mese", "proiector", "wifi", "scena", "oglinzi",
    "vestiare", "bucatarie", "acces_rampa", "curte", "priza", "tabla",
]
IdeaStatus = Literal["deschisa", "prag_atins", "rezervata"]
BookingStatus = Literal["cerut", "aprobat", "refuzat"]
UserRole = Literal["cetatean", "proprietar", "primarie", "verificator"]
# Suggested values for tip_amenajare (the field itself is free text: "foisor", "parc acvatic"...).
TIP_AMENAJARE_SUGESTII = (
    "skatepark", "loc_de_joaca", "parc_caini", "pista_biciclete", "gradina_comunitara", "teren_sport",
)
TipAmenajare = Annotated[str, Field(min_length=2, max_length=80, description="text liber; sugestii: " + ", ".join(TIP_AMENAJARE_SUGESTII))]
ProiectStare = Literal["draft", "publicat", "trimis", "in_verificare", "clarificari", "acord_de_principiu", "respins"]
DISCLAIMER = (
    "Estimare orientativă, bazată pe proiecte de referință. Nu reprezintă o autorizație; "
    "acordul din aplicație este un acord de principiu simulat."
)


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
    proiecte_trimise: int = 0
    proiecte_cu_acord: int = 0
    proiecte_propuse: int = 0
    proiecte_publicate: int = 0
    proiecte_peste_prag: int = 0
    voturi_total: int = 0
    oameni_implicati: int = 0
    terenuri_libere: int = 0


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
    suprafata_mp: int | None = None
    cartier: str | None = None
    sursa: str | None = None
    sursa_detalii: str | None = None
    status_verificare: str | None = None
    descriere: str | None = None


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
    mesaj: str | None = None


class BookingUpdate(BaseModel):
    stare: Literal["aprobat", "refuzat"]


class BookingOut(ORM):
    id: str
    idea_id: str
    space_id: str
    slot: Slot
    stare: BookingStatus
    created_at: UtcDatetime
    mesaj: str | None = None


class NotificationOut(ORM):
    id: str
    user_id: str
    idea_id: str
    booking_id: str | None
    proiect_id: str | None = None
    mesaj: str
    citita: bool
    created_at: UtcDatetime


# --- Extensia "Propunere catre Primarie" ---------------------------------

class Referinta(BaseModel):
    id: str
    tip_amenajare: TipAmenajare
    oras: str
    an: int
    suprafata_mp: int | None = None
    cost_total_lei: int | None = None
    componente: list[str] = []
    sursa_url: str
    sursa_tip: str
    data_accesarii: date


class Cost(BaseModel):
    suficient: bool
    min_lei: int | None = None
    mediana_lei: int | None = None
    max_lei: int | None = None
    moneda: Literal["RON"] = "RON"
    ipoteze: list[str] = []
    referinte_folosite: list[str] = []
    motiv: str | None = None
    suma_cotata_lei: int | None = None
    articole_cotate: int = 0
    articole_necotate: list[str] = []
    pe_surse: dict[str, int] = {}
    eticheta_suma: str = ""
    metoda: str = ""


class Etapa(BaseModel):
    nume: str
    durata_luni: float


class Dosar(BaseModel):
    titlu: str
    descriere: str
    justificare: str
    componente: list[str] = []
    etape: list[Etapa] = []
    riscuri: list[str] = []
    lista_verificare: list[str] = []
    referinte_citate: list[str] = []
    memoriu: dict[str, str] = {}
    acte: list[dict] = []
    acte_disclaimer: str = ""
    cereri_tip: list[dict] = []


class ProiectDirectCreate(BaseModel):
    """POST /proiecte: a project straight on a free plot, without an idea or an interest threshold."""
    space_id: str
    tip_amenajare: TipAmenajare
    descriere: str = Field(min_length=3)
    suprafata_mp: int | None = Field(default=None, ge=1)


class ProiectCreate(BaseModel):
    space_id: str
    tip_amenajare: TipAmenajare
    suprafata_mp: int | None = Field(default=None, ge=1)


class TrimiteIn(BaseModel):
    mesaj: str | None = None


class InainteazaIn(BaseModel):
    verificator_id: str


class DecizieIn(BaseModel):
    stare: Literal["acord_de_principiu", "respins", "clarificari"]
    mesaj: str | None = None

    @model_validator(mode="after")
    def _mesaj_required(self) -> "DecizieIn":
        if self.stare in ("respins", "clarificari") and not (self.mesaj and self.mesaj.strip()):
            raise ValueError("mesajul este obligatoriu la respingere și la cerere de clarificări")
        return self


class ProiectEvenimentOut(ORM):
    id: str
    proiect_id: str
    user_id: str
    stare_noua: ProiectStare
    mesaj: str | None = None
    created_at: UtcDatetime


class ProiectOut(ORM):
    id: str
    idea_id: str
    space_id: str
    autor_id: str
    tip_amenajare: TipAmenajare
    suprafata_mp: int
    stare: ProiectStare
    dosar: Dosar
    referinte: list[Referinta]
    cost: Cost
    created_at: UtcDatetime
    updated_at: UtcDatetime
    verificator_id: str | None = None
    is_demo: bool = False
    voturi: int = 0
    prag_voturi: int = 3
    specificatie: dict | None = None
    fezabilitate: dict | None = None


class ProiectDetaliuOut(ProiectOut):
    evenimente: list[ProiectEvenimentOut] = []
    votat_de_mine: bool = False


class AnalizaIn(BaseModel):
    """POST /proiecte/analiza: specification + feasibility before generating a project (fast, no dossier)."""
    tip_amenajare: TipAmenajare
    descriere: str | None = Field(default=None, max_length=2000)
    suprafata_mp: int | None = Field(default=None, ge=1)
    space_id: str | None = None


class AnalizaOut(BaseModel):
    tip_amenajare: str
    eticheta: str
    specificatie: dict
    fezabilitate: dict
    plan_complet: bool | None = None
    omise: list[dict] = []


class VotOut(BaseModel):
    proiect_id: str
    voturi: int
    prag_voturi: int
    stare: ProiectStare
    votat_de_mine: bool = True


# --- Terenuri si documente (functii P3 din backend.ai.proiect) ----------------
from backend.ai.proiect.design import Scene  # noqa: E402
from backend.ai.proiect.materiale import ListaMateriale  # noqa: E402,F401
from backend.ai.proiect.plots import PlotCandidate  # noqa: E402

LEGEA_15_AVERTISMENT = (
    "Teren din lista Primăriei pentru Legea 15/2003 (atribuit pentru locuințe ale tinerilor). "
    "Folosirea lui pentru o amenajare publică trebuie aprobată de Primărie."
)


class PlotCandidateOut(PlotCandidate):
    avertisment: str | None = None


# Scene's fields plus suprafata_ocupata_mp (a property on Scene, a plain field in the response).
PlanOut = create_model(
    "PlanOut",
    **{name: (f.annotation, f) for name, f in Scene.model_fields.items()},
    suprafata_ocupata_mp=(float, ...),
    bilant=(list[dict], []),
    pot_procent=(float, 0.0),
    cut=(float, 0.0),
)


class TerenCreate(BaseModel):
    """POST /spaces: a free plot marked on the map by a user."""
    nume: str = Field(min_length=3, max_length=120)
    lat: float = Field(ge=45.6, le=45.9, description="Timișoara și împrejurimi")
    lng: float = Field(ge=21.0, le=21.45, description="Timișoara și împrejurimi")
    suprafata_mp: int = Field(ge=10, le=1_000_000)
    descriere: str | None = Field(default=None, max_length=1000)
