import pytest

from backend.ai.proiect import preturi
from backend.ai.proiect.preturi import MIN_OBS, extract, pret_unitar

# Real purchase names seen in the SEAP direct-purchase exports (2023 T IV, 2025 T IV).
ACCEPTED = [
    ("3 buc foisor cf oferta", "34928400-2", 19983, "foisor", 3, 6661.0),
    ("Achizitie 30 buc. Banci pentru parc, din lemn cu 8 rigle, pentru comuna Letcani,", "39113600-3", 24000,
     "banca", 30, 800.0),
    ("MONTAJ PAVELE BETON 100 mp", "45233222-1", 20899, "pavaj", 100, 208.99),
    ("COȘ GUNOI METALIC EXTERIOR: 1 buc.", "34928480-6", 149, "cos_gunoi_stradal", 1, 149.0),
    ("Trunare tartan 400 mp", "19700000-3", 94800, "pardoseala_cauciuc", 400, 237.0),
    ("Imprejmuire cu plasa bordurata si stalpi metalici 160 ml", "45340000-2", 31405, "gard", 160, 196.28),
    ("Achizitie 4 buc banci", "39113600-3", 8264, "banca", 4, 2066.0),
    ("1.250 mp pavaj", "45233222-1", 125000, "pavaj", 1250, 100.0),
]

REJECTED = [
    ("Pachet Covor cauciuc Electroizolant 6x1000mm: 11ML", "44425300-8", 1258),  # pack, wrong article
    ("pergola cu 2 bănci si masa- 4 bucati", "39113600-3", 20000),  # several articles
    ("Set Covor antiderapant, cauciuc, 1200mm*6M, rosu, 8buc", "39531000-3", 5687),  # set
    ("1 set covorase cauciuc", "39530000-6", 291),
    ("BANCĂ STRADALĂ", "39113600-3", 69750),  # no quantity: price per piece unknown
    ("MONTAJ PAVELE BETON 100 mp PACHET", "45233222-1", 20899),
    ("Banda avertizare imprejmuire alb rosu 200 ml", "34928200-0", 162),  # not a fence
    ("Plasa gard sudata 20ml", "34928200-0", 124),  # material only
    ("PLASA GARD 1.9X50X1200/10ML", "34928200-0", 316),
    ("ELIS PAVAJ PATRAT 40X40CM P4 6CM GRI  (9,6 MP/PAL)", "44111000-1", 15),  # size per pallet
    ("BUC SUPORT BICICLETA 3 LOCURI -5 BUC SCARA ALUMINIU DOUA TRONSOANE", "34928400-2", 2645),  # two items
    ("Executie gard perimetral -825 ml + remodelare teren", "45340000-2", 262317),  # two works
    ("Cos de gunoi din plastic 35 litri", "34928480-6", 639),  # indoor bin, no quantity
    ("LEAGAN PENTRU COPII 2 buc", "44000000-0", 6723),  # CPV outside playground equipment
    ("Reparatii foisor 1 buc", "45000000-7", 2000),
    # Found by reading every row of the 2023-2026 run by hand:
    ("FAGURIA GARDLOX MANUSILVER SPRAY ORAL 30ML ANTIBIOTICE SA", "33690000-3", 518),  # ml = millilitres
    ("GAZON RULOU ROYAL SECETA LA  ROLA DE 1 MP", "03451000-6", 17850),  # roll size, not quantity
    ("Reconditionare 70 buc banca rustica", "39113600-3", 22050),
    ("Banca INALTIME 77 TEAVA DE 48X2 LUNGIME 160 RIGLA DE LEMN 8 BUCATI", "39113600-3", 18000),
    ("Tobogan drept H90 - piesa de schimb pentru echipament de joaca (6 buc)", "37535200-9", 6780),
    ("FOISOR PAZA TIP CONTAINER – 2 BUC", "44211000-2", 38500),
    ("Covor cauciuc cu insertie 3mm - rola 12 mp", "19510000-4", 1200),
    ("DOCUMENTTIE TEHNICA IMPREJMUIRE PINA LA 100 ML", "71320000-7", 10000),
    ("REABILITARE IMPREJMUIRE  SCOALA TATARANI JUDETUL DAMBOVITA - 40 ML", "45340000-2", 55014),
    ("Lucrari de dezafectare imprejmuire Giulesti 210ml", "45340000-2", 56000),
    ("Lucrari de executie soclu gard sediu Anina - c.c.a 70ML", "45340000-2", 68423),
    ("SUPORT BICICLETA 60X38X25 CM BUC 5,00 183,00 768,91 146,09 20 3001192 CAPAC WC ATLANT", "39000000-2", 1598),
]


@pytest.mark.parametrize("name,cpv,value,article,qty,unit_price", ACCEPTED)
def test_accepted(name, cpv, value, article, qty, unit_price):
    hit = extract(name, cpv, value)
    assert hit == {"articol": article, "cantitate": qty, "unitate": preturi.ARTICOLE[article].unitate,
                   "pret_unitar_ron": unit_price}


@pytest.mark.parametrize("name,cpv,value", REJECTED)
def test_rejected(name, cpv, value):
    assert extract(name, cpv, value) is None


def test_no_value_no_observation():
    assert extract("3 buc foisor", "34928400-2", None) is None
    assert extract("3 buc foisor", "34928400-2", 0) is None


def _obs(article, prices):
    return [{"articol": article, "pret_unitar_ron": p, "numar_da": f"DA{i}", "data": f"2025-0{i + 1}-01"}
            for i, p in enumerate(prices)]


def test_price_needs_min_observations(monkeypatch):
    monkeypatch.setattr(preturi, "_load", lambda: {"observatii": _obs("banca", [800, 2066])})
    assert MIN_OBS == 3
    assert pret_unitar("banca") is None


def test_median_range_and_sources(monkeypatch):
    monkeypatch.setattr(preturi, "_load", lambda: {"observatii": _obs("banca", [800, 2066, 1200, 5000])})
    p = pret_unitar("banca")
    assert (p.mediana_lei, p.min_lei, p.max_lei, p.observatii) == (1633.0, 800, 5000, 4)
    assert set(p.surse[:2]) == {"DA1", "DA2"}  # the two closest to the median
    assert p.perioada == "2025-01-01 – 2025-04-01"


def test_committed_observations_match_the_rules():
    """Every committed observation must still pass the current rules with its own raw data."""
    for o in preturi.observatii():
        hit = extract(o["denumire"], o["cpv"], o["valoare_ron"])
        assert hit and hit["articol"] == o["articol"] and hit["pret_unitar_ron"] == o["pret_unitar_ron"], o
