import itertools
import xml.etree.ElementTree as ET

import pytest

from backend.ai.proiect import generate_dosar  # noqa: F401  (the package keeps its old import path)
from backend.ai.proiect.design import PLAN_DISCLAIMER, build_plan_dxf, build_plan_svg, build_scene
from backend.ai.proiect.design.catalog import CATALOG
from backend.ai.proiect.design.dxf import ascii_text

KINDS = [*CATALOG, "fântână arteziană", "Parc acvatic"]
SIZES = [(252, 12.0), (276, 12.0), (600, None), (3, None), (100_000, None)]
CASES = [(k, a, w) for k in KINDS for a, w in SIZES]
LAYERS = {"TEREN", "ELEMENTE", "COTE", "TEXT"}


def _overlap(a, b) -> bool:
    return (a.x < b.x + b.latime_m - 1e-6 and b.x < a.x + a.latime_m - 1e-6
            and a.y < b.y + b.lungime_m - 1e-6 and b.y < a.y + a.lungime_m - 1e-6)


@pytest.mark.parametrize("tip,area,width", CASES)
def test_elements_inside_plot_and_never_overlap(tip, area, width):
    s = build_scene(tip, area, width)
    assert abs(s.latime_m * s.lungime_m - area) / area < 0.01
    for e in s.elemente:
        assert e.x >= -1e-6 and e.y >= -1e-6
        assert e.x + e.latime_m <= s.latime_m + 1e-6 and e.y + e.lungime_m <= s.lungime_m + 1e-6
    for a, b in itertools.combinations(s.elemente, 2):
        assert not _overlap(a, b), (a.nume, b.nume)


@pytest.mark.parametrize("tip,area,width", CASES)
def test_free_zones_stay_clear_of_other_elements(tip, area, width):
    s = build_scene(tip, area, width)
    for a, b in itertools.permutations(s.elemente, 2):
        if a.tip == "pista" and b.tip == "pista":
            continue  # the loop track segments touch by design
        z = a.zona_libera_m
        grown = a.model_copy(update={"x": a.x - z, "y": a.y - z, "latime_m": a.latime_m + 2 * z,
                                     "lungime_m": a.lungime_m + 2 * z})
        assert not _overlap(grown, b), (a.nume, b.nume)


def test_deterministic():
    a, b = build_scene("skatepark", 600), build_scene("skatepark", 600)
    assert a == b
    assert build_plan_svg(a, "T") == build_plan_svg(b, "T")
    assert build_plan_dxf(a, "T") == build_plan_dxf(b, "T")


def test_what_does_not_fit_is_listed_with_a_reason():
    s = build_scene("teren_sport", 276, 12.0)  # a 12 m lot is narrower than the smallest court
    assert not s.complet
    assert s.omise[0].nume == "teren multisport" and "nu mai încape" in s.omise[0].motiv
    tiny = build_scene("foisor", 3)
    assert tiny.elemente == [] and not tiny.complet


def test_main_element_fits_on_the_demo_plot_for_every_kind():
    for tip in KINDS:
        assert build_scene(tip, 600).complet, tip


def test_free_text_kind_gets_a_generic_plan():
    s = build_scene("Fântână arteziană", 300)
    assert s.tip_amenajare == "fantana_arteziana"
    assert s.elemente[1].nume == "zona propusă: fântână arteziană"
    assert any("nu are un model" in i for i in s.ipoteze)


def test_synonyms_reach_the_catalog():
    assert build_scene("parc pentru câini", 600).tip_amenajare == "parc_caini"


def test_bicycle_loop_track():
    s = build_scene("pista_biciclete", 600)
    assert sum(e.tip == "pista" and "latura" in e.nume for e in s.elemente) == 4


def test_rejects_non_positive_area():
    with pytest.raises(ValueError):
        build_scene("skatepark", 0)


def test_svg_is_valid_and_carries_title_and_disclaimer():
    s = build_scene("loc de joacă", 276, 12.0)
    svg = build_plan_svg(s, 'Teren „Balea” <CF 440964> & co')
    root = ET.fromstring(svg)
    ns = "{http://www.w3.org/2000/svg}"
    assert root.tag == f"{ns}svg" and root.get("viewBox")
    assert LAYERS <= {g.get("id") for g in root.iter(f"{ns}g")}
    text = "".join(root.itertext())
    assert "<CF 440964> & co" in text and "Plan schematic orientativ" in text
    assert len(root.findall(f".//{ns}rect[@id]")) == len(s.elemente)


def _pairs(dxf: str) -> list[tuple[int, str]]:
    lines = dxf.split("\n")[:-1]
    assert len(lines) % 2 == 0
    return [(int(lines[i]), lines[i + 1]) for i in range(0, len(lines), 2)]


def test_dxf_is_ascii_r12_with_the_four_layers():
    s = build_scene("gradina_comunitara", 276, 12.0)
    dxf = build_plan_dxf(s, "Grădină comunitară – Ronaț")
    dxf.encode("ascii")  # R12 text is ASCII
    pairs = _pairs(dxf)
    assert pairs[-1] == (0, "EOF") and (1, "AC1009") in pairs
    declared = {pairs[i + 1][1] for i, p in enumerate(pairs) if p == (0, "LAYER")}
    assert declared == LAYERS
    assert {v for c, v in pairs if c == 8} == LAYERS  # every entity is on one of them
    kinds = {v for c, v in pairs if c == 0}
    assert not kinds & {"LWPOLYLINE", "DIMENSION", "MTEXT"}  # not R12
    assert {"POLYLINE", "VERTEX", "SEQEND", "LINE", "TEXT"} <= kinds
    polylines = [i for i, p in enumerate(pairs) if p == (0, "POLYLINE")]
    assert len(polylines) * 4 == sum(p == (0, "VERTEX") for p in pairs)
    assert all((70, "1") in pairs[i:i + 8] for i in polylines)  # closed
    assert "Gradina comunitara - Ronat" in dxf


def test_ascii_text():
    assert ascii_text("Zonă de joacă – 3 × 4 m, „ș” Ț") == 'Zona de joaca - 3 x 4 m, "s" T'


def test_disclaimer_is_constant_and_on_every_scene():
    assert build_scene("skatepark", 600).disclaimer == PLAN_DISCLAIMER
    assert "Nu este un proiect tehnic" in PLAN_DISCLAIMER
