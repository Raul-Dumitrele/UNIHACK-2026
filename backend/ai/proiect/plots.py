"""find_plots(tip_amenajare, suprafata_minima, cartier=None) -> list[PlotCandidate]: free plots that suit a
proposal, best first, each with a score (0-100) and a reason in Romanian. Deterministic, no AI.

Candidates are the Spaces of kind teren_liber: by default the seed's (the city hall's Legea 15/2003 list,
ids lista-2019-*, and the demo plot); P1 can pass its own rows (dicts or ORM objects) as `spaces`.

| Criterion | Points | Rule |
|---|---|---|
| fit | 60 | 45 if every mandatory element of the schematic plan fits (build_scene), + 15 × optional pieces placed |
| place | 30 | in the district: 30; else ≤ 1 km: 30, falling linearly to 0 at 8 km; no or unknown district: 15 |
| size | 10 | ≤ 2× the minimum area: 10; ≤ 4×: 5; larger: 0 (a big plot is better kept for a bigger project) |

Penalties, so that the score agrees with the feasibility analysis (fezabilitate.py) and says why:
| Case | Points | Reason given |
|---|---|---|
| city hall list (Legea 15/2003) | −15 | reserved for young people's housing: needs a Local Council decision |
| below the recommended area of the kind | −10 | the project would be reduced |
| below half of the recommended area | score capped at 35 | unrealistic here (same rule as fezabilitate.PREA_MIC) |
| unconfirmed source (OpenStreetMap, marked by a user) or demo plot | −10 | owner and legal status unknown / example |
The score stays within 0-100. OpenStreetMap plots are candidates, never called free or owned by the city hall.

Plots smaller than suprafata_minima are excluded. Listed lots are drawn LOT_WIDTH_M wide, as on the map
(the annex gives only the area); their reason always says they are to be confirmed. Lots are never merged:
their positions are schematic, so adjacency would be invented.
"""
import json
from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel

from backend.ai.fallback import normalize
from backend.ai.geo import distance_km, neighborhood_point
from backend.ai.proiect.design import Scene, build_scene
from backend.ai.proiect.design.catalog import CATALOG, generic
from backend.ai.proiect.design.scene import fmt

LOT_WIDTH_M = 12.0  # same schematic lot width as backend/seed/terenuri.py
NEAR_KM, FAR_KM = 1.0, 8.0


class PlotCandidate(BaseModel):
    space_id: str
    nume: str
    cartier: str | None
    suprafata_mp: float
    scor: int
    motiv: str
    complet: bool  # the main element(s) fit on the schematic plan
    din_lista_primarie: bool
    is_demo: bool
    distanta_km: float | None = None


def _get(obj: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        value = obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)
        if value not in (None, ""):
            return value
    return default


def default_spaces() -> list[dict]:
    """The seed's free plots (offline): the Legea 15/2003 list, the OSM candidates and the demo plot."""
    from backend.seed.proiect_demo import FILE, build_teren  # seed layer, loaded on demand
    from backend.seed.terenuri import DATA, build_terenuri_lista, build_terenuri_osm

    extra = json.loads((DATA / FILE).read_text(encoding="utf-8"))
    return [*build_terenuri_lista(), *build_terenuri_osm(), build_teren(extra)]


def from_city_hall_list(space: Any) -> bool:
    return _get(space, "sursa", "source") == "lista_primarie" or str(_get(space, "id", default="")).startswith("lista-")


def _optional_pieces(scene: Scene) -> tuple[int, int]:
    specs = CATALOG.get(scene.tip_amenajare) or generic(scene.eticheta, 1, 1)
    total = sum(s.bucati for s in specs if not s.obligatoriu)
    missing = sum(o.bucati for o in scene.omise if not o.obligatoriu)
    return total - missing, total


def _place(space: Any, cartier: str | None) -> tuple[int, float | None, str]:
    if not cartier:
        return 15, None, ""
    hood = _get(space, "neighborhood", "cartier")
    if hood and normalize(hood) == normalize(cartier):
        return 30, 0.0, f"în cartierul {hood}"
    centre = neighborhood_point(cartier)
    lat, lon = _get(space, "lat"), _get(space, "lon", "lng")
    if centre is None or lat is None or lon is None:
        return 15, None, f"cartierul „{cartier}” nu e cunoscut, distanța nu e calculată"
    d = distance_km(centre, (float(lat), float(lon)))
    share = 1.0 if d <= NEAR_KM else max(0.0, 1 - (d - NEAR_KM) / (FAR_KM - NEAR_KM))
    return round(30 * share), round(d, 2), f"la {fmt(round(d, 1))} km de centrul cartierului {cartier}"


def _recommended(tip_amenajare: str) -> float | None:
    """Recommended area of a kind that has a hand-written model (no LLM call here: this runs per plot)."""
    from backend.ai.proiect.spec import MODELE, resolve_type  # loaded on demand (spec imports the design layer)

    model = MODELE.get(resolve_type(tip_amenajare))
    return model.suprafata_recomandata_mp if model else None


def score_plot(space: Any, tip_amenajare: str, suprafata_minima: float | None,
               cartier: str | None = None) -> PlotCandidate | None:
    """None when the space is not a free plot or is smaller than suprafata_minima."""
    area = _get(space, "suprafata_mp")
    if _get(space, "kind", "tip") != "teren_liber" or not area or float(area) <= 0:
        return None
    area = float(area)
    if suprafata_minima and area < suprafata_minima:
        return None
    listed = from_city_hall_list(space)
    demo = bool(_get(space, "is_demo", default=False))
    scene = build_scene(tip_amenajare, area, LOT_WIDTH_M if listed else None)
    placed, total = _optional_pieces(scene)
    fit = (45 if scene.complet else 0) + (round(15 * placed / total) if total else 15)
    place, dist, place_text = _place(space, cartier)
    ratio = area / suprafata_minima if suprafata_minima else 1
    size = 10 if ratio <= 2 else 5 if ratio <= 4 else 0
    sursa = _get(space, "sursa", "source")
    rec = _recommended(tip_amenajare)
    penalty, cap, notes = 0, 100, []
    if listed:
        penalty += 15
    if rec and area < rec * 0.5:
        cap = 35
        notes.append(f"sub jumătate din suprafața recomandată de {fmt(rec)} mp: nerealist aici")
    elif rec and area < rec:
        penalty += 10
        notes.append(f"sub suprafața recomandată de {fmt(rec)} mp: amenajarea ar fi redusă")
    if sursa in ("osm", "marcat_de_utilizator") or (demo and not listed):
        penalty += 10

    parts = [f"{fmt(area)} mp"]
    if not scene.complet:
        parts.append("pe planul schematic nu încape: " + ", ".join(o.nume for o in scene.omise if o.obligatoriu))
    elif placed == total:
        parts.append(f"pe planul schematic încape {scene.eticheta}, cu toate dotările")
    else:
        parts.append(f"pe planul schematic încape {scene.eticheta}, cu {placed} din {total} dotări")
    if place_text:
        parts.append(place_text)
    if size == 0:
        parts.append("mult mai mare decât e nevoie")
    parts.extend(notes)
    if listed:
        parts.append("din lista Primăriei (Legea 15/2003), de confirmat: rezervat locuințelor pentru tineri, "
                     "folosirea lui cere o hotărâre a Consiliului Local")
    if sursa == "osm":
        parts.append("candidat din OpenStreetMap, neconfirmat (proprietar și regim juridic necunoscute)")
    elif sursa == "marcat_de_utilizator":
        parts.append("marcat pe hartă de un locuitor, neverificat")
    elif demo and not listed:
        parts.append("teren demonstrativ (exemplu)")
    motiv = "; ".join(parts) + "."
    return PlotCandidate(
        space_id=str(_get(space, "id")), nume=str(_get(space, "name", "nume", default="")),
        cartier=_get(space, "neighborhood", "cartier"), suprafata_mp=area,
        scor=max(0, min(cap, fit + place + size - penalty)),
        motiv=motiv[:1].upper() + motiv[1:], complet=scene.complet, din_lista_primarie=listed, is_demo=demo,
        distanta_km=dist,
    )


def find_plots(tip_amenajare: str, suprafata_minima: float | None, cartier: str | None = None,
               spaces: Iterable[Any] | None = None, limit: int = 10) -> list[PlotCandidate]:
    """Best plots first: score, then the smaller plot (big ones stay free for bigger projects), then id."""
    pool = default_spaces() if spaces is None else spaces
    found = [c for s in pool if (c := score_plot(s, tip_amenajare, suprafata_minima, cartier))]
    found.sort(key=lambda c: (-c.scor, c.suprafata_mp, c.space_id))
    return found[:limit]
