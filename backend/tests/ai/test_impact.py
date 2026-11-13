# Lives under tests/ai because the P3 zone has no tests/impact folder yet.
from datetime import datetime, timezone

from backend.impact import KM_PER_PARTICIPANT, ApprovedBooking, compute_impact


def _b(idea, space, h0, h1, people):
    day = lambda h: datetime(2026, 11, 21, h, tzinfo=timezone.utc)  # noqa: E731
    return ApprovedBooking(idea, space, day(h0), day(h1), people)


def test_empty():
    r = compute_impact([])
    assert (r.idei_realizate, r.spatii_activate, r.ore_folosite, r.participanti, r.km_economisiti) == (0, 0, 0, 0, 0)
    assert r.km_economisiti_estimare is True


def test_totals():
    r = compute_impact([
        _b("i1", "s1", 10, 12, 15),
        _b("i1", "s2", 17, 19, 15),
        _b("i2", "s1", 18, 21, 10),
    ])
    assert r.idei_realizate == 2
    assert r.spatii_activate == 2
    assert r.rezervari_aprobate == 3
    assert r.ore_folosite == 7.0
    assert r.participanti == 40
    assert r.km_economisiti == 40 * KM_PER_PARTICIPANT
    assert r.ipoteze == {"km_per_participant": KM_PER_PARTICIPANT}


def test_bad_inputs_do_not_go_negative():
    r = compute_impact([_b("i1", "s1", 12, 10, -3)])
    assert r.ore_folosite == 0 and r.participanti == 0 and r.km_economisiti == 0
