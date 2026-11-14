from types import SimpleNamespace

from backend.ai.proiect import find_plots
from backend.ai.proiect.plots import default_spaces, score_plot


def plot(id_, area, hood="Fabric", lat=45.757, lon=21.25, **kw):
    return {"id": id_, "name": id_, "kind": "teren_liber", "suprafata_mp": area, "neighborhood": hood,
            "lat": lat, "lon": lon, "is_demo": True, **kw}


def test_default_pool_has_the_listed_lots_and_the_demo_plot():
    ids = {s["id"] for s in default_spaces()}
    assert "demo-space-teren-1" in ids
    assert sum(i.startswith("lista-2019-") for i in ids) == 15


def test_only_free_plots_at_least_the_minimum_area():
    spaces = [plot("a", 300), plot("b", 200), {**plot("c", 900), "kind": "bibliotecă"}]
    assert [c.space_id for c in find_plots("skatepark", 250, spaces=spaces)] == ["a"]


def test_listed_lots_say_they_must_be_confirmed():
    found = find_plots("loc de joacă", 250, "Ronaț")
    assert found and all(c.din_lista_primarie for c in found if c.space_id.startswith("lista-"))
    listed = next(c for c in found if c.din_lista_primarie)
    assert "de confirmat" in listed.motiv and "Legea 15/2003" in listed.motiv
    assert listed.cartier == "Ronaț" and "în cartierul Ronaț" in listed.motiv


def test_big_skatepark_fits_on_the_osm_candidates_and_the_demo_plot():
    found = find_plots("skatepark", 500)
    ids = [c.space_id for c in found]
    assert "demo-space-teren-1" in ids and sum(i.startswith("teren-osm-") for i in ids) == 8
    assert not any(c.din_lista_primarie for c in found)  # the 252/276 m² lots are too small
    assert all(c.is_demo for c in found)  # OSM candidates are unconfirmed examples


def test_default_pool_has_the_osm_candidates():
    pool = default_spaces()
    osm = [s for s in pool if s["id"].startswith("teren-osm-")]
    assert len(osm) == 8 and all(s["status_verificare"] == "neconfirmat" and s["source"] == "osm" for s in osm)


def test_plot_where_the_main_element_does_not_fit_ranks_last_and_says_why():
    spaces = [plot("lot", 276, source="lista_primarie"), plot("mare", 600)]
    first, last = find_plots("teren_sport", 200, spaces=spaces)
    assert first.space_id == "mare" and first.complet
    assert not last.complet and "nu încape: teren multisport" in last.motiv and last.scor < first.scor


def test_closer_plot_wins():
    near = plot("aproape", 400, hood="Fabric")
    far = plot("departe", 400, hood="Ronaț", lat=45.77, lon=21.18)
    found = find_plots("loc_de_joaca", 300, "Fabric", spaces=[far, near])
    assert [c.space_id for c in found] == ["aproape", "departe"]
    assert "km de centrul cartierului Fabric" in found[1].motiv


def test_unknown_district_is_neutral():
    c = score_plot(plot("x", 400), "foisor", 100, "Nicăieri")
    assert "nu e cunoscut" in c.motiv and c.distanta_km is None


def test_oversized_plot_loses_points_and_ties_prefer_the_smaller_plot():
    a, b = plot("b-mic", 300), plot("a-mare", 5000)
    found = find_plots("foisor", 100, spaces=[b, a])
    assert found[0].space_id == "b-mic"
    assert "mult mai mare" in found[1].motiv


def test_orm_rows_and_deterministic_order():
    rows = [SimpleNamespace(id="o1", nume="Teren", tip="teren_liber", suprafata_mp=350, cartier="Fabric",
                            lat=45.757, lng=21.25, is_demo=False, sursa=None)]
    assert find_plots("gradina comunitara", 200, "Fabric", spaces=rows)[0].scor == 100
    assert find_plots("skatepark", 250) == find_plots("skatepark", 250)
    assert all(0 <= c.scor <= 100 for c in find_plots("Fântână arteziană", 1))
