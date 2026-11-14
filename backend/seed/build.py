"""Pure, offline seed builder: committed JSON -> plain dict records with stable ids.

No database and no network here, so it is testable before backend.app.models exists.
Synthetic fields (capacity, amenities, owner, slots) are derived deterministically from the id.
"""
import json
import re
import zlib
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from backend.ai.fallback import build_fallback
from backend.ai.geo import nearest_neighborhood
from backend.ai.matching import KIND_LABELS
from backend.seed import proiect_demo, scenario, terenuri

DATA = Path(__file__).resolve().parent / "data"
SLOT_DAYS = 14

BASE_CAPACITY = {
    "library": 25, "community_centre": 40, "social_centre": 30, "arts_centre": 60,
    "cultural_centre": 60, "coworking_space": 20, "sports_centre": 40, "sports_hall": 60,
}
AMENITIES = {
    "library": ["mese", "scaune", "priză", "wi-fi", "acces persoane cu dizabilități", "proiector"],
    "community_centre": ["mese", "scaune", "priză", "proiector", "bucătărie", "wi-fi", "sonorizare"],
    "social_centre": ["mese", "scaune", "priză", "bucătărie", "wi-fi"],
    "arts_centre": ["scaune", "proiector", "sonorizare", "priză", "ecran", "tablă"],
    "cultural_centre": ["scaune", "proiector", "sonorizare", "priză", "ecran"],
    "coworking_space": ["mese", "scaune", "priză", "wi-fi", "proiector", "tablă"],
    "sports_centre": ["vestiar", "dușuri", "saltele", "parcare"],
    "sports_hall": ["vestiar", "dușuri", "saltele", "sonorizare"],
}
CORE_AMENITIES = 3  # always offered; the rest are picked by hash
OUTDOOR_NAME = re.compile(r"teren|baz[aă]|ștrand|strand|arena", re.IGNORECASE)
# Commercial venues that slipped through the OSM tags; not community spaces.
EXCLUDED_NAME = re.compile(r"kart|paintball|motor|pool|gym|fitness|librări", re.IGNORECASE)
# Slot windows are Timișoara local time, stored as UTC. Fixed +02:00 (EET): the venv has no tzdata
# for zoneinfo on Windows, so summer time (+03:00) is ignored; fine for a demo seeded in November.
LOCAL_TZ = timezone(timedelta(hours=2), "EET")
SLOT_WINDOWS = [(time(10), time(12)), (time(17), time(19)), (time(18), time(20)), (time(9), time(13))]


def stable_hash(*parts: object) -> int:
    return zlib.crc32("|".join(map(str, parts)).encode("utf-8"))


@dataclass
class SeedData:
    users: list[dict] = field(default_factory=list)
    spaces: list[dict] = field(default_factory=list)
    slots: list[dict] = field(default_factory=list)
    ideas: list[dict] = field(default_factory=list)
    interests: list[dict] = field(default_factory=list)
    bookings: list[dict] = field(default_factory=list)
    notifications: list[dict] = field(default_factory=list)
    proiecte: list[dict] = field(default_factory=list)
    proiect_evenimente: list[dict] = field(default_factory=list)


def load_json(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def build_users(demo: dict) -> list[dict]:
    return [{**u, "is_demo": True} for u in demo["users"]]


def build_spaces(osm: dict, owner_ids: list[str]) -> list[dict]:
    spaces = []
    for s in osm["spaces"]:
        if s["kind"] not in KIND_LABELS or EXCLUDED_NAME.search(s["name"]):
            continue
        h = stable_hash(s["id"])
        extras = AMENITIES[s["kind"]][CORE_AMENITIES:]
        picked = [a for i, a in enumerate(extras) if (h >> i) & 1]
        amenities = AMENITIES[s["kind"]][:CORE_AMENITIES] + picked
        if s.get("wheelchair") == "yes" and "acces persoane cu dizabilități" not in amenities:
            amenities.append("acces persoane cu dizabilități")
        outdoor = s["kind"] == "sports_centre" and OUTDOOR_NAME.search(s["name"])
        spaces.append({
            "id": s["id"],
            "name": s["name"],
            "kind": s["kind"],
            "kind_label": KIND_LABELS[s["kind"]],
            "lat": s["lat"],
            "lon": s["lon"],
            "address": s.get("address"),
            "neighborhood": nearest_neighborhood((s["lat"], s["lon"])),
            "capacity": BASE_CAPACITY[s["kind"]] + (h % 5) * 5,
            "amenities": amenities,
            "setting": "exterior" if outdoor else "interior",
            "owner_id": owner_ids[h % len(owner_ids)],
            "source": "osm",
            "is_demo": True,
        })
    return spaces


def make_slot(space_id: str, day: date) -> dict:
    """The space's (hash-chosen) local time window on `day`, stored in UTC."""
    start_t, end_t = SLOT_WINDOWS[stable_hash(space_id, "slots") % len(SLOT_WINDOWS)]
    to_utc = lambda t: datetime.combine(day, t, tzinfo=LOCAL_TZ).astimezone(timezone.utc)  # noqa: E731
    return {
        "id": f"{space_id}-slot-{day.isoformat()}-{start_t:%H%M}",  # local date and time
        "space_id": space_id,
        "starts_at": to_utc(start_t).isoformat(),
        "ends_at": to_utc(end_t).isoformat(),
        "is_demo": True,
    }


def build_slots(spaces: list[dict], start: date) -> list[dict]:
    """Free slots for the next SLOT_DAYS days: 3 weekdays and one time window per space."""
    slots = []
    for s in spaces:
        h = stable_hash(s["id"], "slots")
        weekdays = {(h + k * 2) % 7 for k in range(3)}
        for offset in range(SLOT_DAYS):
            day = start + timedelta(days=offset)
            if day.weekday() in weekdays:
                slots.append(make_slot(s["id"], day))
    return slots


def build_ideas(demo: dict) -> list[dict]:
    # Offline seeding never calls Gemini: dossiers come from the deterministic fallback.
    ideas = []
    for i in demo["ideas"]:
        dossier = {**build_fallback(i["text"]).model_dump(mode="json"), "source": "fallback"}
        ideas.append({**i, "title": dossier["title"], "dossier": dossier, "is_demo": True})
    return ideas


def build_seed(start: date | None = None) -> SeedData:
    extra = load_json(proiect_demo.FILE)
    demo, osm = proiect_demo.merge_demo(load_json("demo.json"), extra), load_json("osm_spaces.json")
    users = build_users(demo)
    owners = [u["id"] for u in users if u["role"] == "proprietar"]
    spaces = build_spaces(osm, owners)
    start = start or date.today()
    slots = build_slots(spaces, start)
    ideas = build_ideas(demo)
    interests = scenario.build_interests(demo)
    bookings = scenario.build_bookings(demo, ideas, users, spaces, slots, start, make_slot)
    threshold = demo["interest_threshold"]
    scenario.apply_states(ideas, slots, interests, bookings, threshold)
    notifications = scenario.build_notifications(ideas, spaces, slots, interests, bookings, threshold, LOCAL_TZ)

    # "Propunere către Primărie": a free plot (no slots, never matched: capacity 0) and one project.
    teren = proiect_demo.build_teren(extra)
    spaces.append(teren)
    spaces += terenuri.build_terenuri_lista()  # Legea 15/2003 list plots (no slots, never matched)
    spaces += terenuri.build_terenuri_osm()  # free plots spotted on OSM (P2's list), unconfirmed
    idea = next(i for i in ideas if i["id"] == extra["idea"]["id"])
    proiect, events = proiect_demo.build_proiect(extra, idea, teren)
    notifications += proiect_demo.build_notifications(proiect, events, idea, users)
    return SeedData(
        users=users,
        spaces=spaces,
        slots=slots,
        ideas=ideas,
        interests=interests,
        bookings=bookings,
        notifications=sorted(notifications, key=lambda n: (n["created_at"], n["id"])),
        proiecte=[proiect],
        proiect_evenimente=events,
    )
