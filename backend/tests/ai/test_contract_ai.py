"""P3 -> contract bridge (backend.ai.contract): Structurat for P1 and owner_message. Offline (no Gemini key)."""
import pytest

from backend.ai import owner_message, structure_idea
from backend.ai.contract import parse_program
from backend.app.schemas import Structurat

VOCAB_DOTARI = {"scaune", "mese", "proiector", "wifi", "scena", "oglinzi", "vestiare", "bucatarie", "acces_rampa",
                "curte", "priza", "tabla"}


@pytest.fixture(autouse=True)
def no_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")


def _slots(program):
    return [(s.zi, s.de_la, s.pana_la) for s in program]


def test_structure_idea_returns_contract_structurat():
    s = structure_idea("Atelier de reparat biciclete, sâmbătă 10-13, 15 oameni, avem nevoie de mese și o priză.")
    assert isinstance(s, Structurat)
    assert s.categorie == "creativ" and s.persoane == 15 and set(s.dotari) <= VOCAB_DOTARI
    assert {"mese", "priza"} <= set(s.dotari)
    assert _slots(s.program) == [("sambata", "10:00", "13:00")]
    assert len(s.rezumat) <= 80 and s.zgomot in {"scazut", "mediu", "ridicat"}


@pytest.mark.parametrize("text, categorie, zgomot", [
    ("Curs de programare pentru copii", "tehnologie", "scazut"),
    ("Concert în curtea blocului", "cultura", "ridicat"),
    ("Întâlnire între vecini", "social", "mediu"),
])
def test_category_and_noise(text, categorie, zgomot):
    s = structure_idea(text)
    assert (s.categorie, s.zgomot) == (categorie, zgomot)


@pytest.mark.parametrize("text, hours, expected", [
    ("joi și vineri între 17 și 19", 2, [("joi", "17:00", "19:00"), ("vineri", "17:00", "19:00")]),
    ("marți seara", 2, [("marti", "18:00", "20:00")]),
    ("în weekend dimineața", 3, [("sambata", "10:00", "13:00"), ("duminica", "10:00", "13:00")]),
    ("duminică de la ora 9:30", 1.5, [("duminica", "09:30", "11:00")]),
    ("fără nicio zi precizată", 2, [("sambata", "10:00", "12:00"), ("duminica", "10:00", "12:00")]),
    ("seara, fără zi", 3, [("sambata", "18:00", "21:00"), ("duminica", "18:00", "21:00")]),
])
def test_program_is_always_filled(text, hours, expected):
    assert _slots(parse_program(text, hours)) == expected


def test_program_never_passes_midnight():
    [slot] = parse_program("vineri ora 22", 5)[:1]
    assert slot.de_la == "22:00" and slot.pana_la == "23:59"


def test_owner_message_from_contract_rows():
    s = structure_idea("Atelier de pictură sâmbătă 10-13 pentru 12 persoane, cu mese")
    idea = {"titlu": "Atelier de pictură", "interesati": 6, "structurat": s.model_dump()}
    text = owner_message(idea, {"nume": "Biblioteca Fabric"}, {"zi": "sambata", "de_la": "10:00", "pana_la": "13:00"})
    assert text.startswith("Bună ziua!") and "„Atelier de pictură”" in text and "6 vecini" in text
    assert "Biblioteca Fabric sâmbătă, între 10:00 și 13:00" in text and "mese" in text


def test_owner_message_accepts_orm_like_objects():
    class Idea:
        titlu, interesati = "Club de șah", 0
        structurat = {"persoane": 8, "dotari": [], "rezumat": "Club de șah"}

    class Space:
        nume = "Centrul comunitar"

    class SlotIn:
        def model_dump(self):
            return {"zi": "joi", "de_la": "17:00", "pana_la": "19:00"}

    text = owner_message(Idea(), Space(), SlotIn())
    assert "Centrul comunitar joi, între 17:00 și 19:00" in text and "8 persoane" in text
