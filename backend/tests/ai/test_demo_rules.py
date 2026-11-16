"""Rules that keep the demo honest: no misleading cost headline, vague or oversized proposals are called out,
the plot score agrees with the feasibility analysis, permits are grouped and carry only checked legal bases."""
from backend.ai.costs import NOTA_PRINCIPALE, TITLU_FARA, TITLU_INTERVAL, estimate_cost
from backend.ai.proiect import template_dosar
from backend.ai.proiect.acte import ACTE_DISCLAIMER, lista_acte
from backend.ai.proiect.fezabilitate import GENERIC_MOTIV
from backend.ai.proiect.pipeline import analiza, build_proiect
from backend.ai.proiect.plots import score_plot
from backend.ai.proiect.spec import get_specificatie


def _plot(area, sursa=None, pid="t1", **extra):
    return {"id": pid, "nume": "Teren", "tip": "teren_liber", "suprafata_mp": area, "lat": 45.75, "lng": 21.22,
            "sursa": sursa, "is_demo": False, **extra}


def test_partial_sum_is_never_the_cost_headline():
    p = build_proiect({"titlu": "Aqua park", "descriere": "piscine și tobogane"}, _plot(6000, "osm"), "parc acvatic",
                      6000, use_llm=False)
    cost = p["cost"]
    assert not cost["suficient"] and cost["titlu"] == TITLU_FARA and cost["motiv"]
    assert cost["min_lei"] is None and cost["mediana_lei"] is None
    assert cost["lipsesc_principale"] and cost["nota_suma"] == NOTA_PRINCIPALE
    assert "bazin principal" in cost["articole_necotate"]
    assert cost["eticheta_suma"].startswith("Suma articolelor cotate (") and "cost" not in cost["eticheta_suma"].lower()


def test_reference_interval_keeps_its_own_headline():
    p = build_proiect({"titlu": "Skatepark", "descriere": "rampe"}, _plot(600), "skatepark", 600, use_llm=False)
    assert p["cost"]["suficient"] and p["cost"]["titlu"] == TITLU_INTERVAL and p["cost"]["mediana_lei"]


def test_cost_without_a_material_list_has_a_headline_and_no_note():
    cost = estimate_cost([], 500)
    assert cost.titlu == TITLU_FARA and cost.nota_suma is None and not cost.lipsesc_principale


def test_generic_proposal_is_flagged_first_and_never_ok():
    a = analiza("ceva frumos pentru copii", 2000, _plot(2000))
    fez = a["fezabilitate"]
    assert a["specificatie"]["sursa_specificatie"] == "generic"
    assert fez["nivel"] == "atentie" and fez["motive"][0] == GENERIC_MOTIV


def test_concrete_proposal_is_interpreted_as_typed():
    fez = analiza("loc de joacă", 400, _plot(400))["fezabilitate"]
    assert fez["interpretare"] == "Am interpretat propunerea ca: loc de joacă"
    assert not fez["interpretare_diferita"] and fez["nivel"] in ("ok", "atentie")
    assert GENERIC_MOTIV not in fez["motive"]


def test_a_different_interpretation_is_said_out_loud():
    spec = get_specificatie("ștrand cu tobogane de apă")
    fez = analiza("ștrand cu tobogane de apă", 12000, _plot(12000))["fezabilitate"]
    assert spec.tip_amenajare == "aquapark"
    assert fez["interpretare"] == "Am interpretat propunerea ca: parc acvatic" and fez["interpretare_diferita"]


def test_plot_under_half_of_the_recommended_area_is_unrealistic():
    fez = analiza("parc acvatic", 3064, _plot(3064, "osm"))["fezabilitate"]  # recommended: 10000 mp
    assert fez["nivel"] == "nerealist" and fez["scor"] <= 35
    assert "5000 mp" in fez["rezumat"] and "10000 mp" in fez["rezumat"]
    assert analiza("parc acvatic", 6000, _plot(6000, "osm"))["fezabilitate"]["nivel"] != "nerealist"


def test_plot_score_agrees_with_feasibility():
    small = score_plot(_plot(3064, "osm"), "parc acvatic", 3000)
    assert small.scor <= 35 and "nerealist" in small.motiv
    listed = score_plot(_plot(276, "lista_primarie", pid="lista-2019-1"), "loc de joacă", 100)
    free = score_plot(_plot(276), "loc de joacă", 100)
    # a listed lot is drawn 12 m wide, so its fit may differ too; it must never beat the same plot without the flag
    assert listed.scor < free.scor and "hotărâre a Consiliului Local" in listed.motiv
    osm = score_plot(_plot(276, "osm"), "loc de joacă", 100)
    assert osm.scor == free.scor - 10 and "neconfirmat" in osm.motiv
    assert "liber" not in osm.motiv.lower().replace("teren liber", "")


def test_permits_optional_group_is_last_and_bases_are_checked():
    acte = lista_acte(get_specificatie("parc acvatic"), _plot(6000, "osm"))
    assert [a.ordine for a in acte] == list(range(1, len(acte) + 1))
    assert acte[-1].nume.startswith("Aviz al Direcției Județene pentru Cultură") and acte[-1].grup == "dupa_caz"
    assert all(a.grup == "uzual" for a in acte[:-1]) and all(a.de_confirmat for a in acte)
    water = next(a for a in acte if a.emitent.startswith("Direcția de Sănătate Publică"))
    assert "Ordonanța Guvernului nr. 7/2023" in water.temei and water.url.startswith("https://legislatie.just.ro/")
    assert "nu garantează" in ACTE_DISCLAIMER
    assert all(a.url is None or a.url.startswith("https://legislatie.just.ro/") for a in acte)


def test_supporters_are_counted_in_correct_romanian():
    one = template_dosar({"titlu": "Idee", "interesati": 1}, _plot(600), "skatepark", 600, [], estimate_cost([], 600))
    many = template_dosar({"titlu": "Idee", "interesati": 4}, _plot(600), "skatepark", 600, [], estimate_cost([], 600))
    assert "susținută de o persoană din comunitate" in one.justificare and "1 persoane" not in one.justificare
    assert "susținută de 4 persoane din comunitate" in many.justificare


def test_aqua_park_layout_is_functional_and_never_overlaps():
    from backend.ai.proiect.design import build_plan_svg, build_scene

    spec = get_specificatie("parc acvatic")
    for area in (3000, 3064, 6000, 10000):
        scene = build_scene("parc acvatic", area, None, spec)
        assert scene.complet and scene == build_scene("parc acvatic", area, None, spec)  # deterministic
        els = {e.nume: e for e in scene.elemente}
        parcare, bazin, turn = els["parcare"], els["bazin principal"], els["turn cu tobogane acvatice"]
        assert parcare.y < bazin.y  # parking sits on the access side (y = 0)
        assert abs(turn.y - bazin.y) <= bazin.lungime_m + 2 * bazin.zona_libera_m + 6  # tower in the pool's row or the next
        assert bazin.latime_m == 25 and turn.latime_m == 10  # sizes are untouched
        for i, a in enumerate(scene.elemente):
            for b in scene.elemente[i + 1:]:
                assert not (a.x < b.x + b.latime_m - 1e-6 and b.x < a.x + a.latime_m - 1e-6 and
                            a.y < b.y + b.lungime_m - 1e-6 and b.y < a.y + a.lungime_m - 1e-6), (area, a.nume, b.nume)
    scene = build_scene("parc acvatic", 6000, None, spec)
    assert abs(els["turn cu tobogane acvatice"].y - els["bazin principal"].y) < 3  # same row when the plot is wide enough
    svg = build_plan_svg(scene, "Plan")
    assert ">11–13<" in svg or ">9–10<" in svg  # small repeated items share one label outside the shapes


def test_pdf_dossier_follows_the_same_cost_rule():
    from backend.ai.proiect.documente import build_documente

    space = _plot(6000, "osm")
    p = build_proiect({"titlu": "Aqua park", "descriere": "piscine"}, space, "parc acvatic", 6000, use_llm=False)
    pdf = build_documente({"id": "t", "stare": "draft", "suprafata_mp": 6000, "is_demo": False, **p}, space)["dosar.pdf"][0]
    assert pdf.startswith(b"%PDF")
    assert b"Cost total: nu poate fi estimat" in pdf  # the headline, as in the UI
    assert b"Informa" in pdf and b"Suma nu include elementele principale" in pdf  # the partial sum is labelled as partial
