import csv
import io
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET

import pytest

from backend.ai.proiect import preturi
from backend.ai.proiect.design import build_scene
from backend.ai.proiect.documente import (
    MEDIA, build_documente, build_dosar_pdf, materiale_csv, materiale_json, plan_json, scene_for,
)
from backend.ai.proiect.documente.pdf import Pdf, encode, wrap
from backend.ai.proiect.materiale import MATERIALE_DISCLAIMER, lista_materiale

PROIECT = {
    "id": "p1", "tip_amenajare": "loc_de_joaca", "suprafata_mp": 600, "stare": "in_verificare", "is_demo": True,
    "dosar": {"titlu": "Loc de joacă în Fabric (test)", "descriere": "Descriere (cu paranteze) și \\ backslash.",
              "justificare": "Pentru copiii din cartier.", "componente": ["leagăne", "tobogan"],
              "etape": [{"nume": "Proiectare", "durata_luni": 3}, {"nume": "Recepție", "durata_luni": 1}],
              "riscuri": ["Vecinii pot avea obiecții."], "lista_verificare": ["Cine administrează terenul"] * 12,
              "referinte_citate": []},
    "cost": {"suficient": False, "moneda": "RON", "ipoteze": [], "referinte_folosite": [],
             "motiv": "Date insuficiente: mai puțin de 2 proiecte de referință."},
    "referinte": [],
}
SPACE = {"id": "demo-space-teren-1", "nume": "Teren liber (exemplu)", "cartier": "Fabric", "suprafata_mp": 600}
LISTED = {"id": "lista-2019-440964", "nume": "Teren din lista Primăriei", "suprafata_mp": 276,
          "sursa": "lista_primarie"}


def _obs(article, prices):
    return [{"articol": article, "pret_unitar_ron": p, "numar_da": f"DA{article}{i}", "data": "2025-10-01"}
            for i, p in enumerate(prices)]


@pytest.fixture
def prices(monkeypatch):
    rows = _obs("banca", [800, 1000, 1200]) + _obs("gard", [150, 200])  # gard stays below MIN_OBS
    monkeypatch.setattr(preturi, "_load", lambda: {"observatii": rows})


# --- materials ----------------------------------------------------------------------------------------------
def test_material_lines_priced_or_de_cotat(prices):
    lista = lista_materiale(build_scene("loc_de_joaca", 600))
    bench = next(l for l in lista.linii if l.articol == "banca")
    assert bench.stare == "cotat" and bench.pret_unitar.mediana_lei == 1000
    assert bench.valoare_lei == bench.cantitate * 1000
    fence = next(l for l in lista.linii if l.articol == "gard")
    assert fence.stare == "de_cotat" and fence.valoare_lei is None and "doar 2 observații" in fence.motiv
    sand = next(l for l in lista.linii if l.nume == "nisipar")
    assert sand.articol is None and "nu are o sursă de preț" in sand.motiv
    assert all(l.ipoteza for l in lista.linii)
    assert lista.subtotal_cotat_lei == sum(l.valoare_lei for l in lista.linii if l.valoare_lei is not None)
    assert lista.eticheta_subtotal == f"Subtotal articole cotate (incomplet: {lista.linii_de_cotat} articole de cotat)"
    assert lista.disclaimer == MATERIALE_DISCLAIMER and "nu este costul proiectului" in lista.disclaimer


def test_quantities_come_from_the_plan(prices):
    scene = build_scene("loc_de_joaca", 600)
    lista = lista_materiale(scene)
    benches = sum(e.tip == "banca" for e in scene.elemente)
    assert next(l for l in lista.linii if l.articol == "banca").cantitate == benches
    fence = next(l for l in lista.linii if l.articol == "gard")
    assert fence.cantitate == round(2 * (scene.latime_m + scene.lungime_m), 1)


def test_no_prices_means_everything_de_cotat(monkeypatch):
    monkeypatch.setattr(preturi, "_load", lambda: {"observatii": []})
    lista = lista_materiale(build_scene("skatepark", 600))
    assert lista.subtotal_cotat_lei == 0 and lista.linii_de_cotat == len(lista.linii)


# --- PDF writer ---------------------------------------------------------------------------------------------
def test_romanian_letters_are_encoded_not_dropped():
    assert encode("ăâîșțĂÂÎȘȚ şţ „x” – ≈ → €") == bytes(
        [0x80, 0xE2, 0xEE, 0x8D, 0x8F, 0x81, 0xC2, 0xCE, 0x8E, 0x90, 0x20, 0x8D, 0x8F, 0x20, 0x84, 0x78, 0x94,
         0x20, 0x96, 0x20]) + b"~ -> EUR"
    assert encode("中") == b"?"


def test_wrap_respects_width():
    lines = wrap("cuvânt " * 60, 200, 10)
    assert len(lines) > 3 and all(len(l) < 60 for l in lines)


def _xref_ok(data: bytes) -> int:
    start = int(re.search(rb"startxref\n(\d+)\n%%EOF\n$", data).group(1))
    assert data[start:start + 4] == b"xref"
    table = data[start:].split(b"\n")
    count = int(table[1].split()[1])
    for i in range(1, count):
        offset = int(table[2 + i][:10])
        assert data[offset:].startswith(f"{i} 0 obj".encode()), i
    return count


def test_pdf_structure_and_escaping():
    pdf = Pdf(footer="test")
    pdf.paragraph("Text (cu paranteze) și \\ backslash")
    data = pdf.to_bytes()
    assert data.startswith(b"%PDF-1.4") and _xref_ok(data) > 6
    assert rb"\(cu paranteze\)" in data and b"\\\\ backslash" in data
    assert b"/Differences [128 /abreve 129 /Abreve 141 /scommaaccent" in data
    assert b"CreationDate" not in data


def test_dossier_pdf_is_deterministic_and_paginates(prices):
    a = build_dosar_pdf(PROIECT, SPACE)
    assert a == build_dosar_pdf(PROIECT, SPACE)
    _xref_ok(a)
    assert int(re.search(rb"/Count (\d+)", a).group(1)) >= 3  # text, plan, materials


@pytest.mark.skipif(not shutil.which("pdftotext"), reason="poppler pdftotext not installed")
def test_dossier_pdf_text_roundtrip(prices, tmp_path):
    path = tmp_path / "dosar.pdf"
    path.write_bytes(build_dosar_pdf(PROIECT, LISTED))
    text = subprocess.run(["pdftotext", "-enc", "UTF-8", str(path), "-"], capture_output=True, check=True).stdout.decode()
    for needle in ("Loc de joacă în Fabric (test)", "Descriere (cu paranteze) și", "Plan schematic",
                   "Listă de materiale", "de cotat", "Subtotal articole cotate", "Legea 15/2003",
                   "Nu reprezintă o autorizație", "TVA: neprecizat", "exemplu"):
        assert needle in " ".join(text.split()), needle


# --- bundle --------------------------------------------------------------------------------------------------
def test_build_documente_bundle(prices):
    docs = build_documente(PROIECT, SPACE)
    assert set(docs) == set(MEDIA) == {"plan.svg", "plan.dxf", "dosar.pdf", "materiale.csv"}
    for name, (content, media) in docs.items():
        assert content and media == MEDIA[name]
    ET.fromstring(docs["plan.svg"][0])
    docs["plan.dxf"][0].decode("ascii")
    assert docs == build_documente(PROIECT, SPACE)


def test_csv_opens_in_romanian_excel(prices):
    raw = materiale_csv(lista_materiale(build_scene("loc_de_joaca", 600)))
    assert raw.startswith("﻿".encode())
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig")), delimiter=";"))
    assert rows[0][:4] == ["articol", "denumire", "cantitate", "unitate"]
    bench = next(r for r in rows if r and r[0] == "banca")
    assert bench[4] == "1000" and bench[9] == "cotat"
    assert any(r and r[0].startswith("Subtotal articole cotate") for r in rows)


def test_listed_plot_is_drawn_12_m_wide_and_json_shapes(prices):
    assert scene_for(PROIECT | {"suprafata_mp": 276}, LISTED).latime_m == 12.0
    plan = plan_json(PROIECT, SPACE)
    assert {"elemente", "omise", "ipoteze", "disclaimer", "suprafata_ocupata_mp"} <= set(plan)
    mat = materiale_json(PROIECT, SPACE)
    assert {"linii", "subtotal_cotat_lei", "linii_de_cotat", "eticheta_subtotal", "tva", "sursa_preturi"} <= set(mat)


def test_area_falls_back_to_the_space_and_is_required():
    assert scene_for(PROIECT | {"suprafata_mp": None}, SPACE).suprafata_mp == 600
    with pytest.raises(ValueError):
        scene_for(PROIECT | {"suprafata_mp": None}, {"id": "x"})


def test_dossier_as_json_text_and_orm_row(prices):
    import json
    from types import SimpleNamespace

    row = SimpleNamespace(**{**PROIECT, "dosar": json.dumps(PROIECT["dosar"]), "cost": json.dumps(PROIECT["cost"])})
    assert build_dosar_pdf(row, SPACE) == build_dosar_pdf(PROIECT, SPACE)
