from datetime import date, datetime
from types import SimpleNamespace

import pytest
from sqlalchemy import JSON, Column
from sqlalchemy.orm import registry
from sqlmodel import Field, Session, SQLModel, create_engine, func, select

from backend.seed.build import SLOT_DAYS, build_seed, load_json
from backend.seed.fetch_osm import normalize, space_id
from backend.seed.run import seed

START = date(2026, 11, 16)  # a Monday


@pytest.fixture(scope="module")
def data():
    return build_seed(START)


# --- OSM normalization (fetch_osm) ---

def test_space_id_includes_osm_type():
    assert space_id("node", 42) == "osm-node-42"
    assert space_id("way", 42) != space_id("node", 42)


def test_normalize_uses_center_and_skips_unnamed():
    payload = {"elements": [
        {"type": "way", "id": 7, "center": {"lat": 45.75, "lon": 21.22},
         "tags": {"name": "Centrul X", "amenity": "community_centre", "addr:street": "Strada Y", "addr:housenumber": "3"}},
        {"type": "node", "id": 7, "lat": 45.7, "lon": 21.2, "tags": {"name": "Bibliotecă", "amenity": "library"}},
        {"type": "node", "id": 8, "lat": 45.7, "lon": 21.2, "tags": {"amenity": "library"}},
    ]}
    spaces = normalize(payload)
    assert [s["id"] for s in spaces] == ["osm-node-7", "osm-way-7"]
    assert spaces[1]["address"] == "Strada Y 3" and spaces[1]["lat"] == 45.75


def test_normalize_rejects_duplicates():
    el = {"type": "node", "id": 1, "lat": 1, "lon": 1, "tags": {"name": "A", "amenity": "library"}}
    with pytest.raises(ValueError, match="duplicate"):
        normalize({"elements": [el, el]})


def test_committed_osm_file_is_attributed_and_unique():
    osm = load_json("osm_spaces.json")
    assert osm["attribution"] == "© OpenStreetMap contributors (ODbL)"
    ids = [s["id"] for s in osm["spaces"]]
    assert len(ids) == len(set(ids)) > 20
    assert all(i.startswith(("osm-node-", "osm-way-", "osm-relation-")) for i in ids)


# --- build (pure, deterministic) ---

def test_build_is_deterministic(data):
    assert build_seed(START) == data


def test_ids_unique_and_everything_is_demo(data):
    for rows in (data.users, data.spaces, data.slots, data.ideas):
        ids = [r["id"] for r in rows]
        assert len(ids) == len(set(ids))
        # Everything is demo data except the plots from the city hall's Legea 15/2003 list (real, is_demo=false).
        assert all(r["is_demo"] is (not r["id"].startswith("lista-")) for r in rows)


def test_references_are_consistent(data):
    users = {u["id"]: u for u in data.users}
    space_ids = {s["id"] for s in data.spaces}
    # Bookable spaces belong to owners; the free plot of the city-hall proposal belongs to the city hall.
    assert all(users[s["owner_id"]]["role"] == ("primarie" if s["kind"] == "teren_liber" else "proprietar")
               for s in data.spaces)
    assert all(sl["space_id"] in space_ids for sl in data.slots)
    assert all(i["author_id"] in users for i in data.ideas)


def test_commercial_venues_excluded(data):
    names = " ".join(s["name"].lower() for s in data.spaces)
    assert "kart" not in names and "paintball" not in names


def test_slots_are_in_window(data):
    past = {b["slot_id"] for b in data.bookings if b["id"] in {"demo-booking-5", "demo-booking-6", "demo-booking-7"}}
    for sl in (s for s in data.slots if s["id"] not in past):
        starts, ends = datetime.fromisoformat(sl["starts_at"]), datetime.fromisoformat(sl["ends_at"])
        assert 0 <= (starts.date() - START).days < SLOT_DAYS
        assert starts < ends


def test_slots_are_local_windows_stored_as_utc(data):
    from backend.seed.build import LOCAL_TZ, SLOT_WINDOWS

    local_starts = {t for t, _ in SLOT_WINDOWS}
    for sl in data.slots:
        starts = datetime.fromisoformat(sl["starts_at"])
        assert starts.utcoffset().total_seconds() == 0
        local = starts.astimezone(LOCAL_TZ)
        assert local.time() in local_starts
        assert sl["id"].endswith(f"-{local.date().isoformat()}-{local:%H%M}")


def test_scenario_covers_every_state(data):
    statuses = {i["status"] for i in data.ideas}
    assert statuses == {"deschisa", "prag_atins", "rezervata"}
    assert {b["status"] for b in data.bookings} == {"ceruta", "aprobata", "refuzata"}
    for idea in data.ideas:
        assert idea["interest_count"] == sum(1 for i in data.interests if i["idea_id"] == idea["id"])


def test_scenario_rules(data):
    users = {u["id"] for u in data.users}
    ideas = {i["id"]: i for i in data.ideas}
    slots = {s["id"]: s for s in data.slots}
    pairs = [(i["idea_id"], i["user_id"]) for i in data.interests]
    assert len(pairs) == len(set(pairs)), "one interest per user per idea"
    assert all(u in users and ideas[i]["author_id"] != u for i, u in pairs), "no self-interest"
    for b in data.bookings:
        assert slots[b["slot_id"]]["space_id"] == b["space_id"]
        assert ideas[b["idea_id"]]["interest_count"] >= 3, "booking only after threshold"
        assert slots[b["slot_id"]]["is_free"] is (b["status"] != "aprobata")
    approved_slots = [b["slot_id"] for b in data.bookings if b["status"] == "aprobata"]
    assert len(approved_slots) == len(set(approved_slots)), "a slot is approved at most once"


def test_past_events_have_past_slots(data):
    past = [b for b in data.bookings if b["id"] in {"demo-booking-5", "demo-booking-6", "demo-booking-7"}]
    slots = {s["id"]: s for s in data.slots}
    assert all(datetime.fromisoformat(slots[b["slot_id"]]["starts_at"]).date() < START for b in past)


def test_notifications(data):
    users = {u["id"] for u in data.users}
    kinds = {n["kind"] for n in data.notifications}
    assert kinds == {"prag_atins", "cerere_rezervare", "rezervare_aprobata", "rezervare_refuzata",
                     "proiect_trimis", "proiect_in_verificare"}
    assert all(n["user_id"] in users and n["text"] and n["read"] is False for n in data.notifications)
    owners = {s["id"]: s["owner_id"] for s in data.spaces}
    for n in data.notifications:
        if n["kind"] == "cerere_rezervare":
            booking = next(b for b in data.bookings if b["id"] == n["booking_id"])
            assert n["user_id"] == owners[booking["space_id"]]
    ids = [n["id"] for n in data.notifications]
    assert len(ids) == len(set(ids))


def test_format_local():
    from backend.seed.build import LOCAL_TZ
    from backend.seed.scenario import format_local

    assert format_local("2026-11-21T08:00:00+00:00", LOCAL_TZ) == "sâmbătă 21 noiembrie, 10:00"


def test_demo_impact_is_not_empty(data):
    from backend.impact import impact_report
    from backend.seed.scenario import approved_for_impact

    r = impact_report(approved_for_impact(data.bookings, data.spaces, data.slots, data.interests, data.users))
    assert r.rezervari_aprobate == 5 and r.idei_realizate == 5
    assert len(r.pe_saptamani) >= 3 and r.km_economisiti > 0


def test_committed_examples_are_up_to_date():
    """If this fails, run: python -m backend.seed.export_examples (and commit the JSON)."""
    import json

    from backend.seed.export_examples import OUT, build_examples

    for name, payload in build_examples().items():
        committed = json.loads((OUT / f"{name}.json").read_text(encoding="utf-8"))
        assert committed == json.loads(json.dumps(payload, ensure_ascii=False)), name


def test_ideas_have_fallback_dossier(data):
    bikes = next(i for i in data.ideas if i["id"] == "demo-idea-1")
    assert bikes["dossier"]["source"] == "fallback"
    assert bikes["dossier"]["category"] == "atelier"
    assert bikes["title"] == bikes["dossier"]["title"]


# --- run (DB upsert) against throwaway models; real ones come from backend.app.models ---

_reg = registry()


class _Base(SQLModel, registry=_reg):
    pass


class User(_Base, table=True):
    __tablename__ = "seedtest_user"
    id: str = Field(primary_key=True)
    nume: str
    rol: str


class Space(_Base, table=True):
    __tablename__ = "seedtest_space"
    id: str = Field(primary_key=True)
    nume: str
    capacitate: int
    dotari: list[str] = Field(sa_column=Column(JSON))
    sloturi: list[dict] = Field(sa_column=Column(JSON))
    owner_id: str
    is_demo: bool = False


FAKE_MODELS = SimpleNamespace(User=User, Space=Space)  # no Idea: must be skipped


def _count(session, model):
    return session.exec(select(func.count()).select_from(model)).one()


def test_seed_is_idempotent(data, capsys):
    from backend.seed.contract import contract_rows

    rows = contract_rows(data)
    engine = create_engine("sqlite://")
    _Base.metadata.create_all(engine)
    with Session(engine) as session:
        first = seed(session, data, FAKE_MODELS)
        counts = [_count(session, m) for m in (User, Space)]
        second = seed(session, data, FAKE_MODELS)
        assert [_count(session, m) for m in (User, Space)] == counts
    assert first == second == {"User": len(rows["User"]), "Space": len(rows["Space"])}
    assert "model Idea not defined yet" in capsys.readouterr().err


def test_seed_upsert_updates_existing_rows(data):
    from backend.seed.contract import contract_rows

    space = contract_rows(data)["Space"][0]
    engine = create_engine("sqlite://")
    _Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed(session, data, FAKE_MODELS)
        session.get(Space, space["id"]).nume = "modificat"
        session.commit()
        seed(session, data, FAKE_MODELS)
        session.expire_all()
        assert session.get(Space, space["id"]).nume == space["nume"]
        assert session.get(Space, space["id"]).sloturi == space["sloturi"]


# --- contract shapes (docs/CONTRACT.md; schemas and models from backend/app, owned by P1) ---

def test_contract_rows_validate_against_p1_schemas(data):
    from backend.app.schemas import BookingOut, IdeaOut, NotificationOut, SpaceOut, UserOut
    from backend.seed.contract import contract_rows

    rows = contract_rows(data)
    from backend.app.schemas import ProiectEvenimentOut, ProiectOut

    for name, schema in [("User", UserOut), ("Space", SpaceOut), ("Booking", BookingOut),
                         ("Notification", NotificationOut), ("Proiect", ProiectOut),
                         ("ProiectEveniment", ProiectEvenimentOut)]:
        for row in rows[name]:
            schema.model_validate(row)
    for row in rows["Idea"]:
        IdeaOut.model_validate({**row, "created_at": datetime.fromisoformat(row["created_at"])})


def test_contract_rows_are_consistent(data):
    from backend.seed.contract import contract_rows

    rows = contract_rows(data)
    users = {u["id"]: u for u in rows["User"]}
    spaces = {s["id"]: s for s in rows["Space"]}
    ideas = {i["id"]: i for i in rows["Idea"]}
    assert {u["rol"] for u in users.values()} == {"cetatean", "proprietar", "primarie", "verificator"}
    assert all(s["owner_id"] in users and users[s["owner_id"]]["rol"] ==
               ("primarie" if s["tip"] == "teren_liber" else "proprietar") for s in spaces.values())
    assert all(i["author_id"] in users and len(i["titlu"]) <= 80 for i in ideas.values())
    assert all(it["user_id"] in users and it["idea_id"] in ideas for it in rows["Interest"])
    assert all(n["user_id"] in users and n["idea_id"] in ideas for n in rows["Notification"])
    teren = spaces["demo-space-teren-1"]  # the free plot of the city-hall proposal
    assert teren["suprafata_mp"] == 600 and teren["sloturi"] == []
    [p] = rows["Proiect"]
    assert p["verificator_id"] == "demo-user-10" and p["stare"] == "in_verificare" and p["space_id"] in spaces
    assert p["is_demo"] is True  # badge "exemplu" (Proiect.is_demo in the contract)
    assert all(e["proiect_id"] == p["id"] for e in rows["ProiectEveniment"])
    assert {n["proiect_id"] for n in rows["Notification"] if n["proiect_id"]} == {p["id"]}
    for b in rows["Booking"]:
        assert b["space_id"] in spaces and b["stare"] in {"cerut", "aprobat", "refuzat"}
        if b["stare"] == "aprobat":  # rule 4: an approved slot leaves the space's availability
            assert b["slot"] not in spaces[b["space_id"]]["sloturi"]
    for i in ideas.values():
        assert i["interesati"] == sum(1 for it in rows["Interest"] if it["idea_id"] == i["id"])
        assert i["stare"] in {"deschisa", "prag_atins", "rezervata"}


def test_seed_into_p1_models_and_impact(data):
    from backend.app import models
    from backend.impact import compute_impact
    from backend.seed.contract import contract_rows

    rows = contract_rows(data)
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        seed(session, data)
        seed(session, data)
        for name in ("User", "Space", "Idea", "Interest", "Booking", "Notification", "Proiect", "ProiectEveniment"):
            assert _count(session, getattr(models, name)) == len(rows[name]), name
        impact = compute_impact(session)
    active = [i for i in rows["Idea"] if i["stare"] in ("prag_atins", "rezervata")]
    assert impact.proiecte_active == len(active) == 7  # definition shared with P1: past the threshold
    assert impact.ore_recuperate > 0 and impact.oameni_conectati > 0 and impact.km_economisiti > 0
    assert (impact.proiecte_trimise, impact.proiecte_cu_acord) == (1, 0)  # demo project is in verification


# --- "Propunere către Primărie" demo (proiect_demo) ---

def test_city_hall_and_verifier_accounts(data):
    roles = {u["id"]: u["role"] for u in data.users}
    assert roles["demo-user-9"] == "primarie" and roles["demo-user-10"] == "verificator"
    assert all(u["is_demo"] for u in data.users)


def test_free_plot_is_never_matched_or_bookable(data):
    from backend.ai.matching import match_spaces

    [teren] = [s for s in data.spaces if s["id"] == "demo-space-teren-1"]
    assert teren["suprafata_mp"] == 600 and teren["is_demo"] and teren["neighborhood"] == "Fabric"
    assert not any(sl["space_id"] == teren["id"] for sl in data.slots)
    for idea in data.ideas:
        assert teren["id"] not in {m.space_id for m in match_spaces(idea["dossier"], data.spaces, limit=100)}


def test_demo_project(data):
    from backend.ai.proiect import DISCLAIMER, money_mentions

    [p] = data.proiecte
    ideas = {i["id"]: i for i in data.ideas}
    assert p["idea_id"] == "demo-idea-8" and ideas["demo-idea-8"]["status"] == "prag_atins"
    assert p["space_id"] == "demo-space-teren-1" and p["tip_amenajare"] == "skatepark" and p["is_demo"]
    assert p["stare"] == "in_verificare" == data.proiect_evenimente[-1]["stare_noua"]
    assert p["cost"]["suficient"] and p["cost"]["moneda"] == "RON"
    assert set(p["cost"]["referinte_folosite"]) <= {r["id"] for r in p["referinte"]}
    assert p["dosar"]["justificare"].endswith(DISCLAIMER)
    assert set(p["dosar"]["referinte_citate"]) <= {r["id"] for r in p["referinte"]}
    text = p["dosar"]["descriere"] + p["dosar"]["justificare"]
    assert money_mentions(text) == []  # figures only in p["cost"]


def test_demo_project_events_and_notifications(data):
    events = data.proiect_evenimente
    assert [e["stare_noua"] for e in events] == ["draft", "trimis", "in_verificare"]
    assert [e["created_at"] for e in events] == sorted(e["created_at"] for e in events)
    notes = [n for n in data.notifications if n.get("proiect_id")]
    assert {(n["kind"], n["user_id"]) for n in notes} == {
        ("proiect_trimis", "demo-user-5"), ("proiect_trimis", "demo-user-9"), ("proiect_in_verificare", "demo-user-5"),
    }


def test_project_is_offline_and_deterministic(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "would-be-used-if-called")
    monkeypatch.setenv("REFERENCES_LIVE_SEARCH", "true")
    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.setattr("backend.ai.llm.chain.complete", lambda *a, **k: pytest.fail("seed must not call an LLM"))
    monkeypatch.setattr("backend.ai.references.search.search_references",
                        lambda *a: pytest.fail("seed must not search the web"))
    assert build_seed(START).proiecte == build_seed(START).proiecte


# --- plots from the city hall's Legea 15/2003 list (backend/seed/terenuri.py) ---

def test_list_plots_follow_the_rule(data):
    from backend.seed import terenuri

    plots = [s for s in data.spaces if s["id"].startswith("lista-")]
    assert terenuri.MIN_PLOTS <= len(plots) <= terenuri.MAX_PLOTS
    assert all(p["suprafata_mp"] >= terenuri.MIN_AREA_MP and p["kind"] == "teren_liber" for p in plots)
    assert all(p["is_demo"] is False and p["owner_id"] == "demo-user-9" and p["source"] == "lista_primarie" for p in plots)
    assert all(p["sursa_detalii"].startswith("HCL 20/2019, anexa nr. 1, poz.") for p in plots)
    assert all("locatie_aproximativa" in p["sursa_detalii"] for p in plots)  # street only, no house number
    assert len({p["id"] for p in plots}) == len(plots)


def test_list_plots_are_side_by_side_not_stacked(data):
    from backend.ai.geo import distance_km
    from backend.seed import terenuri

    plots = [s for s in data.spaces if s["id"].startswith("lista-")]
    points = [(p["lat"], p["lon"]) for p in plots]
    assert len(set(points)) == len(plots)  # no two plots on the same map point
    gaps = [distance_km(a, b) * 1000 for a, b in zip(points, points[1:])]
    assert all(abs(g - terenuri.LOT_WIDTH_M) < 0.5 for g in gaps)  # adjacent lots, ~12 m apart, list order
    centre = (sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points))
    assert distance_km(centre, (45.7631866, 21.1810539)) < 0.005  # centred on the geocoded street point
    assert all("pozitie_schematica" in p["sursa_detalii"] for p in plots)


def test_list_plots_in_contract_rows(data):
    from backend.seed.contract import contract_rows

    rows = [s for s in contract_rows(data)["Space"] if s["id"].startswith("lista-")]
    assert rows and all(r["tip"] == "teren_liber" and r["sloturi"] == [] and r["is_demo"] is False for r in rows)
    assert all(r["sursa"] == "lista_primarie" for r in rows)


@pytest.mark.parametrize("min_count, rows, expected", [(5, 4, 0), (5, 5, 5), (5, 30, 15)])
def test_list_selection_threshold_and_cap(monkeypatch, min_count, rows, expected):
    from backend.seed import terenuri

    monkeypatch.setattr(terenuri, "MIN_PLOTS", min_count)
    fake = [{"cf": str(i), "pozitie": i, "suprafata_mp": 276, "strada": "s"} for i in range(rows)]
    fake.append({"cf": "small", "pozitie": 99, "suprafata_mp": 120, "strada": "s"})
    fake.append({"cf": "nowhere", "pozitie": 98, "suprafata_mp": 900, "strada": "unknown"})
    assert len(terenuri.select(fake, {"s": {}})) == expected
