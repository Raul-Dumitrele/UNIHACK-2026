"""The whole chain of a proposal, in one place:

    analiza(tip_amenajare, suprafata_mp, space, descriere) -> dict   # specification + feasibility (fast, for the wizard)
    build_proiect(idea, space, tip_amenajare, suprafata_mp, descriere) -> dict  # everything the Proiect row stores

specificatie -> plan schematic -> fezabilitate -> referinte -> lista materiale -> cost (interval + suma) -> acte ->
memoriu -> dosar. The specification is computed once and stored, so plan, materials, documents and 3D all agree.
Never raises on AI problems: every AI step has a deterministic fallback.
"""
from typing import Any

from backend.ai.costs import estimate_cost
from backend.ai.proiect import generate_dosar
from backend.ai.proiect.acte import ACTE_DISCLAIMER, cereri_tip, lista_acte
from backend.ai.proiect.design import build_scene
from backend.ai.proiect.fezabilitate import analizeaza
from backend.ai.proiect.materiale import lista_materiale
from backend.ai.proiect.memoriu import genereaza_memoriu
from backend.ai.proiect.plots import LOT_WIDTH_M, from_city_hall_list
from backend.ai.proiect.spec import get_specificatie
from backend.ai.references import find_references


def _get(obj: Any, *names: str, default: Any = None) -> Any:
    if obj is None:
        return default
    for name in names:
        value = obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)
        if value not in (None, "", [], {}):
            return value
    return default


def _scene(spec, suprafata_mp: float | None, space: Any):
    if not suprafata_mp:
        return None
    listed = space is not None and from_city_hall_list(space)
    return build_scene(spec.tip_amenajare, float(suprafata_mp), LOT_WIDTH_M if listed else None, spec)


def analiza(tip_amenajare: str, suprafata_mp: float | None, space: Any = None, descriere: str | None = None) -> dict:
    spec = get_specificatie(tip_amenajare, suprafata_mp, descriere)
    scene = _scene(spec, suprafata_mp, space)
    fez = analizeaza(spec, suprafata_mp, space, scene)
    return {
        "tip_amenajare": spec.tip_amenajare, "eticheta": spec.eticheta,
        "specificatie": spec.model_dump(mode="json"), "fezabilitate": fez.model_dump(mode="json"),
        "plan_complet": scene.complet if scene else None,
        "omise": [o.model_dump() for o in scene.omise] if scene else [],
    }


def build_proiect(idea: Any, space: Any, tip_amenajare: str, suprafata_mp: float | None,
                  descriere: str | None = None, use_llm: bool = True) -> dict:
    spec = get_specificatie(tip_amenajare, suprafata_mp, descriere or _get(idea, "descriere", "text"))
    scene = _scene(spec, suprafata_mp, space)
    fez = analizeaza(spec, suprafata_mp, space, scene)
    refs = find_references(spec.tip_amenajare, suprafata_mp)
    lista = lista_materiale(scene, spec) if scene else None
    cost = estimate_cost(refs, suprafata_mp, lista)
    acte = lista_acte(spec, space)
    teren = fez.teren
    if use_llm:
        dosar = generate_dosar(idea, space, spec.eticheta, suprafata_mp, refs, cost)
    else:
        from backend.ai.proiect import template_dosar
        dosar = template_dosar(idea, space, spec.eticheta, suprafata_mp, refs, cost)
    memoriu = genereaza_memoriu(dosar.titlu, descriere or _get(idea, "descriere", "text"), spec, fez, acte, teren,
                                suprafata_mp, use_llm=use_llm)
    d = dosar.model_dump(mode="json")
    d["memoriu"] = memoriu
    d["acte"] = [a.model_dump() for a in acte]
    d["acte_disclaimer"] = ACTE_DISCLAIMER
    d["cereri_tip"] = [c.model_dump() for c in cereri_tip(spec, space, {"dosar": d, "suprafata_mp": suprafata_mp})]
    # The specification's own components complete the dossier's list when the model wrote something vaguer.
    oblig = [c.nume for c in spec.componente if c.obligatoriu]
    for name in oblig:
        if not any(name.split()[0].lower() in x.lower() for x in d["componente"]):
            d["componente"].append(name)
    return {
        "tip_amenajare": spec.tip_amenajare, "eticheta": spec.eticheta,
        "specificatie": spec.model_dump(mode="json"), "fezabilitate": fez.model_dump(mode="json"),
        "referinte": [r.model_dump(mode="json") for r in refs], "cost": cost.model_dump(mode="json"),
        "dosar": d,
    }
