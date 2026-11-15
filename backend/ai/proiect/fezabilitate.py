"""analizeaza(spec, suprafata_mp, space, scene=None) -> Fezabilitate: is the proposal realistic on this plot?

Deterministic rules over the specification and the plot. Nothing is rejected silently: an unrealistic proposal
gets nivel="nerealist" with the reasons and what would make it work. Utilities are never claimed to exist: the
app has no data about networks, so they are listed as "de verificat".
"""
from typing import Any, Literal

from pydantic import BaseModel

from backend.ai.proiect.spec.model import Specificatie

Nivel = Literal["ok", "atentie", "nerealist"]


class Utilitate(BaseModel):
    nume: str
    stare: str = "de verificat"  # the app never knows; the operator confirms
    detaliu: str = ""


class Fezabilitate(BaseModel):
    nivel: Nivel
    scor: int  # 0-100, orientative
    rezumat: str
    motive: list[str]
    recomandari: list[str]
    beneficii: list[str]
    utilitati: list[Utilitate]
    suprafata_mp: float | None
    suprafata_minima_mp: float
    suprafata_recomandata_mp: float | None
    teren: dict
    disclaimer: str = ("Analiză orientativă, din reguli simple ale aplicației. Nu înlocuiește studiul de fezabilitate, "
                       "certificatul de urbanism sau avizele operatorilor de utilități.")


def _get(obj: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        value = obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)
        if value not in (None, "", [], {}):
            return value
    return default


def _teren(space: Any) -> dict:
    if space is None:
        return {}
    return {"id": _get(space, "id"), "nume": _get(space, "nume", "name"), "sursa": _get(space, "sursa", "source"),
            "cartier": _get(space, "cartier", "neighborhood"), "suprafata_mp": _get(space, "suprafata_mp"),
            "status_verificare": _get(space, "status_verificare")}


def analizeaza(spec: Specificatie, suprafata_mp: float | None, space: Any = None, scene: Any = None) -> Fezabilitate:
    motive: list[str] = []
    reco: list[str] = []
    score = 100
    area = float(suprafata_mp) if suprafata_mp else None
    minim, rec = spec.suprafata_minima_mp, spec.suprafata_recomandata_mp

    if area is None:
        score -= 40
        motive.append("Suprafața terenului nu este cunoscută.")
        reco.append("Alege un teren cu suprafața cunoscută sau introdu suprafața de care ai nevoie.")
    elif area < minim:
        score -= 60
        motive.append(f"Terenul are {area:g} mp, sub minimul de {minim:g} mp pe care aplicația îl consideră necesar "
                      f"pentru „{spec.eticheta}”.")
        reco.append(f"Caută un teren de cel puțin {minim:g} mp" + (f" (recomandat {rec:g} mp)" if rec else "") +
                    " sau propune o variantă mai mică a obiectivului.")
    elif rec and area < rec:
        score -= 15
        motive.append(f"Terenul ({area:g} mp) e sub suprafața recomandată de {rec:g} mp: amenajarea va fi redusă.")
        reco.append("Verifică pe plan ce componente încap; cele omise apar la „Nu încape”.")
    elif rec and area > rec * 10:
        score -= 5
        motive.append(f"Terenul ({area:g} mp) e mult mai mare decât are nevoie obiectivul ({rec:g} mp recomandat).")
        reco.append("Propune o folosire și pentru restul terenului sau un obiectiv mai amplu.")

    if scene is not None and not getattr(scene, "complet", True):
        lipsa = [o.nume for o in getattr(scene, "omise", []) if getattr(o, "obligatoriu", False)]
        score -= 25
        motive.append("Pe planul schematic nu încap componentele obligatorii: " + ", ".join(lipsa) + ".")
        reco.append("Un teren mai mare sau mai lat; ori renunțarea la unele componente.")

    utils = [Utilitate(nume=u, detaliu="aplicația nu are date despre rețele; se cere aviz de la operator")
             for u in spec.utilitati_toate()]
    if utils:
        score -= 5 * min(len(utils), 3)
        motive.append("Necesită racord la: " + ", ".join(u.nume for u in utils) +
                      ". Disponibilitatea și costul racordului le confirmă operatorii.")
        reco.append("Cere Primăriei / operatorilor informații despre rețelele din apropiere înainte de proiectare.")

    sursa = _get(space, "sursa", "source") if space is not None else None
    if sursa == "lista_primarie":
        score -= 15
        motive.append("Terenul e din lista Primăriei pentru Legea 15/2003 (locuințe pentru tineri): folosirea lui "
                      "pentru o amenajare publică cere o decizie a Consiliului Local.")
        reco.append("Întreabă Primăria dacă lotul poate primi altă destinație sau alege un alt teren.")
    elif sursa in ("osm", "marcat_de_utilizator"):
        score -= 10
        motive.append("Proprietarul, regimul juridic și disponibilitatea terenului nu sunt cunoscute.")
        reco.append("Primăria verifică în cartea funciară și în planul urbanistic cine deține terenul și ce permite.")
    elif sursa == "demo":
        motive.append("Teren demonstrativ (exemplu).")

    if spec.sursa_specificatie == "generic":
        score -= 20
        motive.append("Aplicația nu are un model tehnic pentru acest tip de obiectiv: specificația e generică.")
        reco.append("Descrie mai precis ce vrei (componente, pentru cine) sau alege un tip apropiat din listă.")
    elif spec.sursa_specificatie == "llm":
        score -= 10
        motive.append("Specificația a fost propusă automat și nu a fost verificată de un proiectant.")

    score = max(0, min(100, score))
    nivel: Nivel = "nerealist" if (area is not None and area < minim) else "atentie" if score < 75 else "ok"
    if nivel == "nerealist":
        rezumat = f"Propunerea nu este realistă pe acest teren: „{spec.eticheta}” are nevoie de cel puțin {minim:g} mp."
    elif nivel == "atentie":
        rezumat = "Propunerea este posibilă, dar sunt aspecte de clarificat înainte de proiectare."
    else:
        rezumat = "Propunerea pare realistă pe acest teren, în limitele unei analize orientative."
    return Fezabilitate(nivel=nivel, scor=score, rezumat=rezumat, motive=motive, recomandari=reco,
                        beneficii=list(spec.beneficii), utilitati=utils, suprafata_mp=area, suprafata_minima_mp=minim,
                        suprafata_recomandata_mp=rec, teren=_teren(space))
