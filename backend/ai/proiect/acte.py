"""lista_acte(spec, space) -> list[Act]: the public documents a proposal of this kind usually needs, in order,
with who issues them and the legal basis. cereri_tip(...) -> pre-filled request texts.

Deterministic. The app does NOT issue any permit and never claims one exists: every row is marked
"de confirmat" because the exact list is set by the city hall through the urbanism certificate
(Legea 50/1991, republicată, cu modificările ulterioare). Articles are cited at the level we are sure of.
"""
from typing import Any

from pydantic import BaseModel

from backend.ai.proiect.spec.model import Specificatie

LEGEA_50 = "Legea nr. 50/1991 privind autorizarea executării lucrărilor de construcții (republicată)"
NORME_50 = "Normele metodologice de aplicare a Legii nr. 50/1991 (Ordinul MDRL nr. 839/2009)"
ACTE_DISCLAIMER = ("Listă orientativă a documentelor publice uzuale pentru acest tip de lucrare. Lista exactă, "
                   "avizele cerute și încadrarea (cu sau fără autorizație de construire) le stabilește Primăria prin "
                   "certificatul de urbanism. Aplicația nu emite și nu deține niciun aviz sau autorizație, iar lista "
                   "nu garantează obținerea lor.")


class Act(BaseModel):
    ordine: int
    nume: str
    emitent: str
    descriere: str
    temei: str
    conditie: str = ""  # when it applies ("dacă lucrarea afectează circulația")
    de_confirmat: bool = True
    grup: str = "uzual"  # uzual | dupa_caz (applies only in some situations; listed last)
    url: str | None = None  # only pages on legislatie.just.ro that were opened when the row was written


class CerereTip(BaseModel):
    titlu: str
    catre: str
    text: str


def _get(obj: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        value = obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)
        if value not in (None, "", [], {}):
            return value
    return default


def lista_acte(spec: Specificatie, space: Any = None) -> list[Act]:
    tags = set(spec.categorie_lucrare)
    utils = set(spec.utilitati_toate())
    acte: list[Act] = []

    def add(nume, emitent, descriere, temei, conditie="", grup="uzual", url=None):
        acte.append(Act(ordine=len(acte) + 1, nume=nume, emitent=emitent, descriere=descriere, temei=temei,
                        conditie=conditie, grup=grup, url=url))

    add("Dovada dreptului asupra terenului (extras de carte funciară; pentru teren public, hotărâre a Consiliului "
        "Local de aprobare a folosinței)",
        "Oficiul de Cadastru și Publicitate Imobiliară; Consiliul Local",
        "Cine deține terenul și dacă poate primi această destinație. Pentru o propunere a comunității pe teren "
        "public, Primăria inițiază proiectul sau aprobă folosința.",
        LEGEA_50 + ", condițiile de emitere a autorizației (titlul asupra imobilului)")
    if _get(space, "sursa", "source") == "lista_primarie" if space is not None else False:
        add("Hotărâre a Consiliului Local privind schimbarea destinației lotului (lista Legea 15/2003)",
            "Consiliul Local Timișoara",
            "Lotul este rezervat locuințelor pentru tineri; altă folosință cere decizia Consiliului Local.",
            "Legea nr. 15/2003 privind sprijinul acordat tinerilor pentru construirea unei locuințe")
    add("Certificat de urbanism",
        "Primăria Municipiului Timișoara – Direcția Urbanism",
        "Actul de informare: regimul juridic, economic și tehnic al terenului, ce se poate construi și lista "
        "avizelor necesare. Se cere cu o cerere-tip, planuri de încadrare și extras CF.",
        LEGEA_50 + ", art. 6 (certificatul de urbanism)")
    add("Studiu topografic și, după caz, studiu geotehnic",
        "Topograf autorizat / inginer geotehnician",
        "Ridicarea exactă a terenului; pentru platforme, bazine și construcții, natura solului.",
        NORME_50 + " (conținutul documentației tehnice)",
        "obligatoriu pentru construcții și platforme din beton" if tags & {"constructie", "bazine", "platforma_beton"} else
        "dacă se cere prin certificatul de urbanism")
    if "energie electrică" in utils or "instalatie_electrica" in tags or "iluminat" in tags:
        add("Aviz tehnic de racordare (ATR) și aviz de amplasament",
            "Operatorul de distribuție a energiei electrice din zonă",
            "Puterea disponibilă, soluția de racordare și tariful de racordare; amplasamentul față de rețelele existente.",
            "Legea energiei electrice și a gazelor naturale nr. 123/2012; reglementările în vigoare privind "
            "racordarea, de confirmat prin certificatul de urbanism")
    if "apă potabilă" in utils or "instalatie_apa" in tags:
        add("Aviz de amplasament și aviz de branșare la rețeaua de apă",
            "Operatorul regional de apă-canal (în Timișoara, Aquatim)",
            "Punctul de branșare, contorizarea și condițiile tehnice.",
            "Legea serviciului de alimentare cu apă și de canalizare nr. 241/2006")
    if "canalizare" in utils or "canalizare" in tags:
        add("Aviz de racordare la canalizare",
            "Operatorul regional de apă-canal",
            "Evacuarea apelor; pentru bazine, condițiile de deversare a apei tratate.",
            "Legea nr. 241/2006")
    if tags & {"instalatie_apa", "bazine"} or "fantana_publica" == spec.tip_amenajare:
        add("Aviz / notificare sanitară pentru apa potabilă sau apa de îmbăiere",
            "Direcția de Sănătate Publică Timiș",
            "Calitatea apei oferite publicului.",
            "Ordonanța Guvernului nr. 7/2023 privind calitatea apei destinate consumului uman (a abrogat Legea "
            "nr. 458/2002). Pentru apa de îmbăiere: legislația în vigoare privind normele de igienă pentru bazine, "
            "de confirmat prin certificatul de urbanism.",
            url="https://legislatie.just.ro/public/DetaliiDocument/264337")
    add("Aviz de mediu (clasare sau acord de mediu)",
        "Agenția pentru Protecția Mediului Timiș",
        "Dacă lucrarea are impact asupra mediului; amenajările mici primesc de obicei o decizie de clasare.",
        "Legea nr. 292/2018 privind evaluarea impactului anumitor proiecte asupra mediului",
        "după caz, stabilit prin certificatul de urbanism")
    if tags & {"parcare", "semnalizare"} or spec.tip_amenajare == "statie_incarcare":
        add("Aviz al Comisiei de Circulație",
            "Primăria Municipiului Timișoara – Comisia de Circulație / Poliția Rutieră",
            "Locurile de parcare, accesele auto și semnalizarea rutieră.",
            "OUG nr. 195/2002 privind circulația pe drumurile publice; reglementările locale, de confirmat prin "
            "certificatul de urbanism")
    if tags & {"constructie", "bazine"} or any((c.inaltime_m or 0) >= 2.5 and c.categorie == "constructie"
                                                  for c in spec.componente):
        add("Aviz de securitate la incendiu",
            "Inspectoratul pentru Situații de Urgență „Banat” Timiș",
            "Pentru clădiri și spații cu public (vestiare, clădiri tehnice).",
            "Legea nr. 307/2006 privind apărarea împotriva incendiilor", "dacă se cere prin certificatul de urbanism")
    add("Documentație tehnică pentru autorizarea executării lucrărilor (DTAC), întocmită de proiectant autorizat",
        "Arhitect / inginer cu drept de semnătură",
        "Planuri, memorii, breviar de calcul, devize. Schițele aplicației sunt doar punct de pornire.",
        LEGEA_50 + ", art. 7 și anexa nr. 1 (conținutul-cadru al documentației)")
    if spec.tip_amenajare == "loc_de_joaca" or "echipamente_joaca" in tags:
        add("Certificate de conformitate pentru echipamentele de joacă și raport de inspecție după montaj",
            "Furnizorul echipamentelor; organism de inspecție",
            "Echipamentele trebuie să respecte standardul european pentru spații de joacă.",
            "HG nr. 435/2010 privind regimul de introducere pe piață și de exploatare a echipamentelor pentru "
            "agrement; SR EN 1176")
    add("Autorizație de construire (sau încadrarea lucrării ca executabilă fără autorizație)",
        "Primăria Municipiului Timișoara – Direcția Urbanism",
        "Actul final care permite începerea lucrărilor. Lucrările mărunte de întreținere și unele amenajări pot fi "
        "scutite de autorizație; încadrarea o face Primăria.",
        LEGEA_50 + ", art. 3 (lucrări care necesită autorizație) și art. 11 (lucrări care se pot executa fără)")
    add("Anunțul de începere a lucrărilor și recepția la terminarea lucrărilor",
        "Primăria; Inspectoratul de Stat în Construcții",
        "Comunicarea datei de început, apoi procesul-verbal de recepție.",
        LEGEA_50 + "; Regulamentul privind recepția construcțiilor, aprobat prin HG nr. 273/1994, cu modificările "
        "aduse de HG nr. 343/2017",
        url="https://legislatie.just.ro/Public/DetaliiDocumentAfis/189596")
    add("Aviz al Direcției Județene pentru Cultură",
        "Direcția Județeană pentru Cultură Timiș",
        "Numai dacă terenul e în zona protejată a unui monument istoric sau în zona construită protejată.",
        "Legea nr. 422/2001 privind protejarea monumentelor istorice", "numai în zone protejate",
        grup="dupa_caz")
    return acte


def cereri_tip(spec: Specificatie, space: Any, proiect: Any = None) -> list[CerereTip]:
    nume_teren = _get(space, "nume", "name", default="terenul propus") if space is not None else "terenul propus"
    cartier = _get(space, "cartier", "neighborhood", default="") if space is not None else ""
    area = _get(proiect, "suprafata_mp") if proiect is not None else None
    area = area or (_get(space, "suprafata_mp") if space is not None else None)
    titlu = (_get(_get(proiect, "dosar", default={}) or {}, "titlu") if proiect is not None else None) or \
        f"Amenajare: {spec.eticheta}"
    loc = f"{nume_teren}" + (f", cartierul {cartier}" if cartier else "") + (f", circa {area:g} mp" if area else "")
    return [
        CerereTip(
            titlu="Cerere pentru emiterea certificatului de urbanism",
            catre="Primăria Municipiului Timișoara – Direcția Urbanism",
            text=(f"Subsemnatul/Subsemnata ______________________, domiciliat(ă) în ______________________, "
                  f"în calitate de reprezentant al grupului de locuitori din cartierul {cartier or '________'}, "
                  f"solicit emiterea certificatului de urbanism pentru imobilul situat la: {loc}, "
                  f"în scopul: {titlu}.\n\n"
                  "Anexez: plan de încadrare în zonă, plan de situație (schița orientativă generată de aplicația "
                  "Loc Comun, care nu este documentație tehnică), extras de carte funciară (dacă este cazul) și dovada "
                  "achitării taxei.\n\nData ____________            Semnătura ____________\n\n"
                  f"Formular-tip conform {NORME_50}, anexa nr. 1 (F.1).")),
        CerereTip(
            titlu="Solicitare adresată Consiliului Local privind folosința terenului",
            catre="Consiliul Local al Municipiului Timișoara",
            text=(f"Grupul de locuitori din cartierul {cartier or '________'} solicită Consiliului Local analizarea "
                  f"propunerii „{titlu}” pe terenul {loc} și, dacă terenul aparține domeniului public sau privat al "
                  "municipiului, aprobarea folosinței lui pentru această amenajare de interes comunitar.\n\n"
                  "Anexăm dosarul propunerii (memoriu, estimare orientativă de cost din proiecte de referință, plan "
                  "schematic, lista documentelor necesare) și lista persoanelor care susțin propunerea.\n\n"
                  "Precizăm că estimările din dosar sunt orientative și că acordul de principiu din aplicație este "
                  "simulat; solicităm îndrumare privind pașii oficiali.")),
    ]
