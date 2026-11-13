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
    assert r.ipoteze["km_per_participant"] == KM_PER_PARTICIPANT
    assert [(w.saptamana, w.rezervari, w.ore) for w in r.pe_saptamani] == [("2026-W47", 3, 7.0)]
    assert r.pe_cartiere == {} and r.pe_tip_spatiu == {}


def test_bad_inputs_do_not_go_negative():
    r = compute_impact([_b("i1", "s1", 12, 10, -3)])
    assert r.ore_folosite == 0 and r.participanti == 0 and r.km_economisiti == 0


FABRIC_SPACE = dict(space_kind="community_centre", space_lat=45.756989, space_lon=21.249889)
START = datetime(2026, 11, 21, 10, tzinfo=timezone.utc)
END = datetime(2026, 11, 21, 12, tzinfo=timezone.utc)


def test_breakdowns_by_neighborhood_and_kind():
    r = compute_impact([
        ApprovedBooking("i1", "s1", START, END, 5, **FABRIC_SPACE),
        ApprovedBooking("i2", "s2", START, END, 5, space_kind="library", space_lat=45.74424, space_lon=21.209053),
    ])
    assert r.pe_cartiere == {"Fabric": 1, "Iosefin": 1}
    assert r.pe_tip_spatiu == {"bibliotecă": 1, "centru comunitar": 1}


def test_km_from_participant_neighborhoods():
    start, end = START, END
    # A Fabric resident using a space in Fabric avoids the trip to Cetate (~1.6 km each way).
    local = compute_impact([ApprovedBooking("i1", "s1", start, end, 1, **FABRIC_SPACE,
                                            participant_neighborhoods=("Fabric",))])
    assert 2.8 < local.km_economisiti < 3.6
    # Someone from Cetate going to Fabric saves nothing (never negative).
    central = compute_impact([ApprovedBooking("i1", "s1", start, end, 1, **FABRIC_SPACE,
                                              participant_neighborhoods=("Cetate",))])
    assert central.km_economisiti == 0
    # Unknown homes fall back to the constant; extra names beyond participants are ignored.
    mixed = compute_impact([ApprovedBooking("i1", "s1", start, end, 2, **FABRIC_SPACE,
                                            participant_neighborhoods=("Cetate", "Nicăieri", "Fabric"))])
    assert mixed.km_economisiti == KM_PER_PARTICIPANT
