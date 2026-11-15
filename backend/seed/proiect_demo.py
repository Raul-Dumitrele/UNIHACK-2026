"""Demo data for the "Propunere către Primărie" extension: city-hall and verifier accounts, a free plot
(Space kind teren_liber with suprafata_mp), an idea past the threshold and one Proiect with its events.

Offline and deterministic: references come from the local base only (no live search) and the dossier
from the template (no Gemini). Proiect/ProiectEveniment are written by run.py once P1 defines the
models; until then they are skipped and exported as JSON by export_examples.
"""
from backend.ai.geo import neighborhood_point
from backend.ai.references import type_label

FILE = "proiect_demo.json"
STATE_TEXT = {
    "trimis": "a fost trimisă către Primărie",
    "in_verificare": "a intrat în verificare",
    "clarificari": "are nevoie de clarificări",
    "acord_de_principiu": "a primit un acord de principiu (simulat)",
    "respins": "a fost respinsă",
}


def merge_demo(demo: dict, extra: dict) -> dict:
    """demo.json plus the extension's users, idea and interests (new dict; inputs untouched)."""
    return {
        **demo,
        "users": demo["users"] + extra["users"],
        "ideas": demo["ideas"] + [extra["idea"]],
        "interests": demo["interests"] + extra["interests"],
    }


def build_teren(extra: dict) -> dict:
    t = extra["teren"]
    lat, lon = neighborhood_point(t["neighborhood"])  # district centre: the plot itself is fictional
    return {
        "id": t["id"], "name": t["name"], "kind": "teren_liber", "kind_label": "teren liber",
        "lat": lat, "lon": lon, "address": None, "neighborhood": t["neighborhood"],
        "capacity": 0, "amenities": [], "setting": "exterior", "owner_id": t["owner_id"],
        "suprafata_mp": t["suprafata_mp"], "source": "demo", "is_demo": True,
    }


def build_proiect(extra: dict, idea: dict, teren: dict) -> tuple[dict, list[dict]]:
    from backend.ai.proiect.pipeline import build_proiect as pipeline  # offline: use_llm=False, local references

    spec, events = extra["proiect"], extra["evenimente"]
    tip, area = spec["tip_amenajare"], teren["suprafata_mp"]
    space = {**teren, "nume": teren["name"], "cartier": teren["neighborhood"], "sursa": teren["source"]}
    r = pipeline(idea, space, tip, area, idea.get("text"), use_llm=False)
    votes = extra.get("voturi", [])
    proiect = {
        "id": spec["id"], "idea_id": idea["id"], "space_id": teren["id"], "autor_id": idea["author_id"],
        "tip_amenajare": r["tip_amenajare"], "suprafata_mp": area, "stare": events[-1]["stare_noua"],
        "dosar": r["dosar"], "referinte": r["referinte"], "cost": r["cost"],
        "specificatie": r["specificatie"], "fezabilitate": r["fezabilitate"],
        "voturi": len(votes), "prag_voturi": spec.get("prag_voturi", 3),
        "created_at": spec["created_at"], "updated_at": events[-1]["created_at"], "is_demo": True,
    }
    rows = [{"id": f"{spec['id']}-ev-{n}", "proiect_id": spec["id"], **e, "is_demo": True}
            for n, e in enumerate(events, 1)]
    return proiect, rows


def build_votes(extra: dict) -> list[dict]:
    pid = extra["proiect"]["id"]
    return [{"id": f"{pid}-vot-{v['user_id']}", "proiect_id": pid, "user_id": v["user_id"],
             "created_at": v["created_at"], "is_demo": True} for v in extra.get("voturi", [])]


def build_notifications(proiect: dict, events: list[dict], idea: dict, users: list[dict]) -> list[dict]:
    """Author is told about every state change; city-hall accounts get the 'sent' one."""
    city_hall = [u["id"] for u in users if u["role"] == "primarie"]
    label = type_label(proiect["tip_amenajare"])
    notes = []
    for e in events:
        state = e["stare_noua"]
        if state not in STATE_TEXT:
            continue
        recipients = [proiect["autor_id"]] + (city_hall if state == "trimis" else [])
        for user_id in recipients:
            notes.append({
                "id": f"{e['id']}-notif-{user_id}", "user_id": user_id, "idea_id": idea["id"],
                "booking_id": None, "proiect_id": proiect["id"], "kind": f"proiect_{state}",
                "created_at": e["created_at"], "read": False, "is_demo": True,
                "text": (f"Propunere nouă de {label}: „{idea['title']}”." if user_id in city_hall else
                         f"Propunerea „{idea['title']}” {STATE_TEXT[state]}."
                         + (f" Mesaj: {e['mesaj']}" if e.get("mesaj") else "")),
            })
    return notes
