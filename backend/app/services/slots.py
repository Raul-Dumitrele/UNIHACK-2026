"""Slot arithmetic on plain dicts {zi, de_la, pana_la} (as stored in JSON columns)."""
DAY_RO = {
    "luni": "luni", "marti": "marți", "miercuri": "miercuri", "joi": "joi",
    "vineri": "vineri", "sambata": "sâmbătă", "duminica": "duminică",
}


def to_min(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def to_hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def duration(slot: dict) -> int:
    return to_min(slot["pana_la"]) - to_min(slot["de_la"])


def overlap(a: dict, b: dict) -> dict | None:
    """Intersection of two slots on the same day, or None."""
    if a["zi"] != b["zi"]:
        return None
    start, end = max(to_min(a["de_la"]), to_min(b["de_la"])), min(to_min(a["pana_la"]), to_min(b["pana_la"]))
    if end <= start:
        return None
    return {"zi": a["zi"], "de_la": to_hhmm(start), "pana_la": to_hhmm(end)}


def contains(outer: dict, inner: dict) -> bool:
    return (
        outer["zi"] == inner["zi"]
        and to_min(outer["de_la"]) <= to_min(inner["de_la"])
        and to_min(inner["pana_la"]) <= to_min(outer["pana_la"])
    )


def subtract(slots: list[dict], taken: dict) -> list[dict]:
    """Remove `taken` from `slots`, splitting a slot when intervals remain on both sides."""
    result: list[dict] = []
    for s in slots:
        if overlap(s, taken) is None:
            result.append(s)
            continue
        s0, s1 = to_min(s["de_la"]), to_min(s["pana_la"])
        t0, t1 = to_min(taken["de_la"]), to_min(taken["pana_la"])
        if s0 < t0:
            result.append({"zi": s["zi"], "de_la": s["de_la"], "pana_la": to_hhmm(t0)})
        if t1 < s1:
            result.append({"zi": s["zi"], "de_la": to_hhmm(t1), "pana_la": s["pana_la"]})
    return result


def fmt_hour(minutes: int) -> str:
    return str(minutes // 60) if minutes % 60 == 0 else f"{minutes // 60}:{minutes % 60:02d}"


def fmt_slot(slot: dict) -> str:
    return f"{DAY_RO[slot['zi']]} {fmt_hour(to_min(slot['de_la']))}-{fmt_hour(to_min(slot['pana_la']))}"
