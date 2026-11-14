"""Demo scenario on top of the seed: interests, bookings and in-app notifications, so the demo
starts with ideas in every state and a non-empty impact dashboard.

Status values are proposals for docs/CONTRACT.md (still TBD):
  IdeaStatus: deschisa (under threshold) -> prag_atins -> rezervata (has an approved booking)
  BookingStatus: ceruta -> aprobata | refuzata
Booking spaces come from backend.ai.matching (the idea author's district as origin), so the
scenario also shows the matching working on real OSM spaces.
"""
from collections.abc import Callable
from datetime import date, datetime, timedelta

from backend.ai.matching import match_spaces
from backend.impact import ApprovedBooking

WEEKDAYS = ["luni", "marți", "miercuri", "joi", "vineri", "sâmbătă", "duminică"]
MONTHS = ["ianuarie", "februarie", "martie", "aprilie", "mai", "iunie", "iulie", "august",
          "septembrie", "octombrie", "noiembrie", "decembrie"]
DECISION_KIND = {"aprobata": "rezervare_aprobata", "refuzata": "rezervare_refuzata"}
DECISION_WORD = {"aprobata": "aprobată", "refuzata": "refuzată"}


def format_local(iso: str, tz) -> str:
    """'2026-11-21T08:00:00+00:00' -> 'sâmbătă 21 noiembrie, 10:00' (Timișoara time)."""
    t = datetime.fromisoformat(iso).astimezone(tz)
    return f"{WEEKDAYS[t.weekday()]} {t.day} {MONTHS[t.month - 1]}, {t:%H:%M}"


def build_interests(demo: dict) -> list[dict]:
    return [{"id": f"{i['idea_id']}-interest-{i['user_id']}", **i, "is_demo": True} for i in demo["interests"]]


def build_bookings(demo: dict, ideas: list[dict], users: list[dict], spaces: list[dict], slots: list[dict],
                   start: date, make_slot: Callable[[str, date], dict]) -> list[dict]:
    """Specs with `days_ago` are past events: their slot is created in the past and added to `slots`."""
    hood = {u["id"]: u["neighborhood"] for u in users}
    by_idea = {i["id"]: i for i in ideas}
    used: set[str] = set()
    bookings = []
    for spec in demo["bookings"]:
        idea = by_idea[spec["idea_id"]]
        matches = match_spaces(idea["dossier"], spaces, hood[idea["author_id"]], limit=spec["match_rank"] + 1)
        space_id = matches[spec["match_rank"]].space_id
        if spec.get("days_ago"):
            slot = make_slot(space_id, start - timedelta(days=spec["days_ago"]))
            slots.append(slot)
        else:
            slot = next(s for s in slots if s["space_id"] == space_id and s["id"] not in used)
        used.add(slot["id"])
        bookings.append({
            "id": spec["id"],
            "idea_id": idea["id"],
            "space_id": space_id,
            "slot_id": slot["id"],
            "requester_id": idea["author_id"],
            "status": spec["status"],
            "created_at": spec["created_at"],
            "decided_at": spec["decided_at"],
            "is_demo": True,
        })
    return bookings


def apply_states(ideas: list[dict], slots: list[dict], interests: list[dict], bookings: list[dict],
                 threshold: int) -> None:
    """Set idea status / interest count and mark slots taken by approved bookings (in place)."""
    approved = [b for b in bookings if b["status"] == "aprobata"]
    for idea in ideas:
        count = sum(1 for i in interests if i["idea_id"] == idea["id"])
        idea["interest_count"] = count
        idea["prag"] = threshold
        if any(b["idea_id"] == idea["id"] for b in approved):
            idea["status"] = "rezervata"
        else:
            idea["status"] = "prag_atins" if count >= threshold else "deschisa"
    taken = {b["slot_id"] for b in approved}
    for slot in slots:
        slot["is_free"] = slot["id"] not in taken


def build_notifications(ideas: list[dict], spaces: list[dict], slots: list[dict], interests: list[dict],
                        bookings: list[dict], threshold: int, tz) -> list[dict]:
    space_by_id = {s["id"]: s for s in spaces}
    slot_by_id = {s["id"]: s for s in slots}
    title = {i["id"]: i["title"] for i in ideas}
    notes = []
    for idea in ideas:
        ordered = sorted((i for i in interests if i["idea_id"] == idea["id"]), key=lambda i: i["created_at"])
        if len(ordered) >= threshold:
            notes.append({
                "id": f"{idea['id']}-notif-prag", "user_id": idea["author_id"], "idea_id": idea["id"],
                "booking_id": None, "kind": "prag_atins", "created_at": ordered[threshold - 1]["created_at"],
                "text": f"Ideea „{idea['title']}” a atins pragul: {threshold} persoane interesate.",
            })
    for b in bookings:
        space = space_by_id[b["space_id"]]
        when = format_local(slot_by_id[b["slot_id"]]["starts_at"], tz)
        notes.append({
            "id": f"{b['id']}-notif-cerere", "user_id": space["owner_id"], "idea_id": b["idea_id"],
            "booking_id": b["id"], "kind": "cerere_rezervare", "created_at": b["created_at"],
            "text": f"Cerere nouă de rezervare: „{title[b['idea_id']]}” la {space['name']}, {when}.",
        })
        if b["status"] in DECISION_KIND:
            notes.append({
                "id": f"{b['id']}-notif-{b['status']}", "user_id": b["requester_id"], "idea_id": b["idea_id"],
                "booking_id": b["id"], "kind": DECISION_KIND[b["status"]], "created_at": b["decided_at"],
                "text": f"Rezervarea pentru „{title[b['idea_id']]}” la {space['name']} ({when}) "
                        f"a fost {DECISION_WORD[b['status']]}.",
            })
    for n in notes:
        n.update(read=False, is_demo=True)
    return sorted(notes, key=lambda n: (n["created_at"], n["id"]))


def approved_for_impact(bookings: list[dict], spaces: list[dict], slots: list[dict], interests: list[dict],
                        users: list[dict]) -> list[ApprovedBooking]:
    """Reference mapping from booking rows to impact inputs (what P1 does for GET /impact)."""
    space_by_id = {s["id"]: s for s in spaces}
    slot_by_id = {s["id"]: s for s in slots}
    hood = {u["id"]: u.get("neighborhood") for u in users}
    result = []
    for b in (b for b in bookings if b["status"] == "aprobata"):
        space, slot = space_by_id[b["space_id"]], slot_by_id[b["slot_id"]]
        people = [i["user_id"] for i in interests if i["idea_id"] == b["idea_id"]]
        result.append(ApprovedBooking(
            idea_id=b["idea_id"], space_id=space["id"],
            starts_at=datetime.fromisoformat(slot["starts_at"]), ends_at=datetime.fromisoformat(slot["ends_at"]),
            participants=len(people), space_kind=space["kind"], space_lat=space["lat"], space_lon=space["lon"],
            participant_neighborhoods=tuple(hood[p] for p in people if hood.get(p)),
        ))
    return result
