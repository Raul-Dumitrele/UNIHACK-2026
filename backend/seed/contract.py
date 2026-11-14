"""Seed records -> rows in the shape of the team contract (docs/CONTRACT.md, models in backend/app/models.py).

build.py keeps P3's richer internal records (dated slots, English keys, the city-hall proposal demo);
this module maps them to the contract tables that run.py writes:
  User         id, nume, rol, cartier, lat, lng           (only contract roles: cetatean, proprietar)
  Space        id, nume, tip, lat, lng, capacitate, dotari, sloturi (weekly Slot), owner_id, is_demo
  Idea         id, author_id, titlu, descriere, structurat, prag, interesati, stare, is_demo, created_at
  Interest     id, user_id, idea_id, created_at
  Booking      id, idea_id, space_id, slot, stare (cerut/aprobat/refuzat), created_at
  Notification id, user_id, idea_id, booking_id, mesaj, citita, created_at
The city-hall proposal (Proiect, ProiectEveniment, the free plot, primarie/verificator accounts) is not in
the contract yet: those rows are passed through and run.py skips them until P1 adds the models.
"""
from datetime import datetime

from backend.ai.contract import DOTARI, to_structurat
from backend.ai.geo import city_centre, neighborhood_point
from backend.ai.schemas import IdeaDossier
from backend.seed.build import LOCAL_TZ, SeedData

ROLES = {"locuitor": "cetatean", "proprietar": "proprietar"}
BOOKING_STATES = {"ceruta": "cerut", "aprobata": "aprobat", "refuzata": "refuzat"}
WEEKDAY = ["luni", "marti", "miercuri", "joi", "vineri", "sambata", "duminica"]
DAY_ORDER = {d: i for i, d in enumerate(WEEKDAY)}


def weekly(slot: dict) -> dict:
    """Dated UTC slot -> contract Slot {zi, de_la, pana_la} in Timișoara local time."""
    start = datetime.fromisoformat(slot["starts_at"]).astimezone(LOCAL_TZ)
    end = datetime.fromisoformat(slot["ends_at"]).astimezone(LOCAL_TZ)
    return {"zi": WEEKDAY[start.weekday()], "de_la": f"{start:%H:%M}", "pana_la": f"{end:%H:%M}"}


def _key(s: dict) -> tuple:
    return DAY_ORDER[s["zi"]], s["de_la"], s["pana_la"]


def _dotari(amenities: list[str]) -> list[str]:
    out: list[str] = []
    for a in amenities:
        label = DOTARI.get(a)
        if label and label not in out:
            out.append(label)
    return out


def contract_rows(data: SeedData) -> dict[str, list[dict]]:
    users = [u for u in data.users if u["role"] in ROLES]
    user_ids = {u["id"] for u in users}
    spaces = [s for s in data.spaces if s["kind"] != "teren_liber"]
    slot_by_id = {s["id"]: s for s in data.slots}
    booked = {b["id"]: weekly(slot_by_id[b["slot_id"]]) for b in data.bookings}

    # Weekly availability per space; an approved booking takes its slot out (contract rule 4).
    taken: dict[str, list[dict]] = {}
    for b in data.bookings:
        if b["status"] == "aprobata":
            taken.setdefault(b["space_id"], []).append(booked[b["id"]])
    sloturi: dict[str, list[dict]] = {}
    for sl in data.slots:
        w = weekly(sl)
        bucket = sloturi.setdefault(sl["space_id"], [])
        if w not in bucket and w not in taken.get(sl["space_id"], []):
            bucket.append(w)

    def point(hood: str | None) -> tuple[float, float]:
        return neighborhood_point(hood) or city_centre()

    return {
        "User": [{
            "id": u["id"], "nume": u["name"], "rol": ROLES[u["role"]], "cartier": u["neighborhood"],
            "lat": point(u["neighborhood"])[0], "lng": point(u["neighborhood"])[1],
        } for u in users],
        "Space": [{
            "id": s["id"], "nume": s["name"], "tip": s["kind_label"], "lat": s["lat"], "lng": s["lon"],
            "capacitate": s["capacity"], "dotari": _dotari(s["amenities"]),
            "sloturi": sorted(sloturi.get(s["id"], []), key=_key), "owner_id": s["owner_id"], "is_demo": True,
        } for s in spaces],
        "Idea": [{
            "id": i["id"], "author_id": i["author_id"], "titlu": i["title"][:80], "descriere": i["text"],
            "structurat": to_structurat(IdeaDossier(**i["dossier"]), i["text"]).model_dump(mode="json"),
            "prag": i["prag"], "interesati": i["interest_count"], "stare": i["status"], "is_demo": True,
            "created_at": i["created_at"],
        } for i in data.ideas],
        "Interest": [{
            "id": it["id"], "user_id": it["user_id"], "idea_id": it["idea_id"], "created_at": it["created_at"],
        } for it in data.interests if it["user_id"] in user_ids],
        "Booking": [{
            "id": b["id"], "idea_id": b["idea_id"], "space_id": b["space_id"], "slot": booked[b["id"]],
            "stare": BOOKING_STATES[b["status"]], "created_at": b["created_at"],
        } for b in data.bookings],
        "Notification": [{
            "id": n["id"], "user_id": n["user_id"], "idea_id": n["idea_id"], "booking_id": n.get("booking_id"),
            "mesaj": n["text"], "citita": n["read"], "created_at": n["created_at"],
        } for n in data.notifications if not n.get("proiect_id") and n["user_id"] in user_ids],
        # Not in the contract yet (city-hall proposal extension): written only once P1 defines the models.
        "Proiect": data.proiecte,
        "ProiectEveniment": data.proiect_evenimente,
    }
