"""lista_materiale(scene) -> ListaMateriale: quantities taken from the schematic plan × unit prices observed in
SEAP direct purchases (backend.ai.proiect.preturi). Deterministic, no AI.

Every line says where its quantity comes from (ipoteza). A line gets a value only when its article has a price
(at least MIN_OBS observations); everything else is "de cotat", with the reason. The subtotal covers only the
priced lines and is always labelled as incomplete: it is never the cost of the project (that estimate is
backend.ai.costs.Cost, from reference projects).
"""
from pydantic import BaseModel

from backend.ai.proiect.design import Scene
from backend.ai.proiect.design.scene import fmt
from backend.ai.proiect.preturi import ARTICOLE, MIN_OBS, SURSA, TVA, PretUnitar, observatii, pret_unitar

MATERIALE_DISCLAIMER = (
    "Listă orientativă. Cantitățile rezultă din planul schematic, iar prețurile unitare sunt mediane ale unor "
    "achiziții directe publice din SEAP, nu oferte. Subtotalul nu este costul proiectului: articolele „de cotat” "
    "lipsesc din el, iar manopera, transportul și proiectarea pot să nu fie incluse.")

# Element kinds whose pieces map to one article (count = pieces on the plan).
PIECES = {"banca": "banca", "cos": "cos_gunoi_stradal", "rastel": "rastel_biciclete", "foisor": "foisor",
          "masa": "masa_picnic", "compost": "compostor"}
PLAY = [("leag", "leagan"), ("balansoar", "balansoar"), ("tobogan", "complex_joaca")]  # name fragment -> article


class LinieMaterial(BaseModel):
    articol: str | None  # key in preturi.ARTICOLE, None when the app has no price source for it
    nume: str
    unitate: str
    cantitate: float
    ipoteza: str
    pret_unitar: PretUnitar | None = None
    valoare_lei: int | None = None
    stare: str  # cotat | de_cotat
    motiv: str = ""


class ListaMateriale(BaseModel):
    linii: list[LinieMaterial]
    subtotal_cotat_lei: int
    linii_de_cotat: int
    eticheta_subtotal: str
    sursa_preturi: str = SURSA
    tva: str = TVA
    ipoteze: list[str]
    disclaimer: str = MATERIALE_DISCLAIMER


def _line(articol: str | None, nume: str, unitate: str, cantitate: float, ipoteza: str) -> LinieMaterial:
    cantitate = round(cantitate) if unitate == "buc" else round(cantitate, 1)
    price = pret_unitar(articol) if articol else None
    if price:
        return LinieMaterial(articol=articol, nume=price.nume, unitate=unitate, cantitate=cantitate,
                             ipoteza=ipoteza, pret_unitar=price, valoare_lei=round(cantitate * price.mediana_lei),
                             stare="cotat")
    if articol:
        n = len(observatii(articol))
        motiv = f"doar {n} observații în SEAP pentru acest articol (minimum {MIN_OBS})"
    else:
        motiv = "aplicația nu are o sursă de preț pentru acest articol"
    return LinieMaterial(articol=articol, nume=ARTICOLE[articol].nume if articol else nume, unitate=unitate,
                         cantitate=cantitate, ipoteza=ipoteza, stare="de_cotat", motiv=motiv)


def _counts(scene: Scene) -> dict[tuple[str | None, str, str], int]:
    """(articol, name, kind) -> pieces, in plan order."""
    out: dict[tuple[str | None, str, str], int] = {}
    for e in scene.elemente:
        if e.tip in PIECES:
            key = (PIECES[e.tip], e.nume.rstrip(" 0123456789"), e.tip)
            if "dozator" in e.nume:
                key = (None, "dozator de pungi", e.tip)
        elif e.tip == "joaca":
            art = next((a for frag, a in PLAY if frag in e.nume), None)
            key = (art, e.nume.rstrip(" 0123456789"), e.tip)
        elif e.tip in ("strat", "magazie", "apa"):
            key = (None, e.nume.rstrip(" 0123456789"), e.tip)
        else:
            continue
        out[key] = out.get(key, 0) + 1
    return out


def lista_materiale(scene: Scene) -> ListaMateriale:
    lines: list[LinieMaterial] = []
    for (art, name, _kind), n in _counts(scene).items():
        lines.append(_line(art, name, "buc", n, f"{n} pe planul schematic"))

    by_kind: dict[str, float] = {}
    for e in scene.elemente:
        by_kind[e.tip] = by_kind.get(e.tip, 0.0) + e.suprafata_mp
    play_zone = sum((e.latime_m + 2 * e.zona_libera_m) * (e.lungime_m + 2 * e.zona_libera_m)
                    for e in scene.elemente if e.tip == "joaca" and "nisipar" not in e.nume)
    if by_kind.get("alee"):
        lines.append(_line("pavaj", "alee", "mp", by_kind["alee"], "suprafața aleii de acces din plan, pavată"))
    if play_zone:
        lines.append(_line("pardoseala_cauciuc", "pardoseală de protecție", "mp", play_zone,
                           "echipamentele de joacă împreună cu zona liberă din jurul lor (ipoteză de plan)"))
    for kind, nume in (("skate", "suprafață și module de skate"), ("sport", "suprafață teren de sport"),
                       ("caini", "amenajare zone pentru câini"), ("pista", "îmbrăcăminte pistă de biciclete"),
                       ("zona", "zona propusă (lucrări specifice)")):
        if by_kind.get(kind):
            lines.append(_line(None, nume, "mp", by_kind[kind], "suprafața din planul schematic"))
    perimeter = 2 * (scene.latime_m + scene.lungime_m)
    lines.append(_line("gard", "împrejmuire", "ml", perimeter, "împrejmuire pe tot conturul terenului (ipoteză)"))
    green = scene.suprafata_mp - scene.suprafata_ocupata_mp - max(0.0, play_zone - by_kind.get("joaca", 0.0))
    if green > 0:
        lines.append(_line("gazon_rulou", "spațiu verde", "mp", green,
                           "suprafața rămasă liberă pe plan, înierbată (ipoteză)"))

    priced = [l for l in lines if l.valoare_lei is not None]
    todo = len(lines) - len(priced)
    subtotal = sum(l.valoare_lei for l in priced)
    return ListaMateriale(
        linii=lines, subtotal_cotat_lei=subtotal, linii_de_cotat=todo,
        eticheta_subtotal=f"Subtotal articole cotate (incomplet: {todo} articole de cotat)",
        ipoteze=[*scene.ipoteze,
                 f"Împrejmuirea are {fmt(perimeter)} m (perimetrul dreptunghiului din plan).",
                 "Prețul unitar este mediana prețurilor plătite în achizițiile directe găsite; intervalul min–max "
                 "arată cât de mult diferă produsele între ele."],
    )
