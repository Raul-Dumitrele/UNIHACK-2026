# Date - Loc Comun

Sursele de date, ce e real și ce e generat, și formulele din tabloul de impact. Responsabil: P3.

## Atribuire
Spațiile provin din OpenStreetMap: **© OpenStreetMap contributors (ODbL)**.
Datele sunt disponibile sub licența Open Database License 1.0 (https://opendatacommons.org/licenses/odbl/).
Atribuirea trebuie afișată în UI oriunde apar spațiile sau harta (de ex. în subsolul listei și pe hartă).

## Surse
| Fișier | Conținut | Origine |
|---|---|---|
| `backend/seed/data/osm_spaces.json` | 87 de spații din Timișoara (nume, tip, coordonate, adresă dacă există) | OSM prin Overpass API, descărcat o singură dată pe 2026-11-13T21:19:58Z |
| `backend/seed/data/demo.json` | 8 utilizatori fictivi și 4 idei fictive | scrise manual |

Interogarea completă și zona (bbox 45.70, 21.14 - 45.81, 21.32) sunt salvate în `osm_spaces.json`.
Tipuri OSM incluse:
- `amenity`: `community_centre`, `social_centre`, `library`, `arts_centre`, `cultural_centre`, `coworking_space`;
- `leisure`: `sports_centre`, `sports_hall`.

Sălile de fitness (`fitness_centre`) sunt excluse, fiind în mare parte lanțuri comerciale.

## Fluxul datelor
1. `python -m backend.seed.fetch_osm` rulează **o singură dată** (folosește rețeaua) și rescrie `osm_spaces.json`. Fișierul se pune în git.
2. `python -m backend.seed.run` merge **doar offline**:
   - citește cele două JSON-uri;
   - generează înregistrările (`backend/seed/build.py`);
   - face upsert după id (`session.merge`).

   Poate fi rulat de oricâte ori: rezultatul e același.

## Ce e real și ce e generat
Toate înregistrările din seed au `is_demo=true` și apar în UI cu insigna „exemplu”.

| Câmp | Real (OSM) | Generat |
|---|---|---|
| nume, tip, coordonate, adresă | da | - |
| capacitate | - | valoare de bază per tip + 0-20, derivată din hash-ul id-ului |
| dotări (`amenities`) | - | 3 dotări de bază per tip + altele alese după hash; „acces persoane cu dizabilități” dacă OSM are `wheelchair=yes` |
| interior/exterior | - | bazele sportive cu „teren/bază/ștrand/arena” în nume sunt exterior |
| proprietar | - | unul dintre utilizatorii fictivi `demo-user-6..8` |
| sloturi libere | - | 3 zile pe săptămână, o fereastră orară (ora locală a Timișoarei, salvată în UTC), pentru următoarele 14 zile de la data rulării |
| utilizatori, idei | - | fictivi; dosarele ideilor demo vin din fallback-ul determinist (fără Gemini) |

Ferestrele sloturilor (de ex. 18:00-20:00) sunt în ora locală. Pentru conversia în UTC folosim un decalaj fix +02:00 (ora de iarnă), pentru că mediul Windows nu are `tzdata`. Ora de vară (+03:00) e ignorată.
Id-ul slotului conține data și ora locale.

**Proprietarii și disponibilitatea sunt fictive.** Locurile există, dar nu au acceptat să fie pe platformă.
Locurile comerciale evidente (karting, paintball, săli de fitness, librării) sunt filtrate din seed.

## Id-uri stabile
| Entitate | Format | Exemplu |
|---|---|---|
| Spațiu | `osm-<tip>-<id OSM>` | `osm-way-123456` |
| Utilizator | `demo-user-<n>` | `demo-user-1` |
| Idee demo | `demo-idea-<n>` | `demo-idea-1` |
| Slot | `<id spațiu>-slot-<AAAA-LL-ZZ>-<HHMM>` | `osm-way-123456-slot-2026-11-21-1000` |

Tipul OSM (`node`/`way`/`relation`) face parte din id, pentru că OSM numerotează separat nodurile, căile și relațiile. Fără el, două elemente ar putea primi același id.
`fetch_osm.py` refuză să scrie fișierul dacă apar id-uri duplicate.

## Dosarul ideii (AI)
`backend.ai.structure_idea(text)` returnează `IdeaDossier`, cu `source` = `gemini` sau `fallback`.
- Modelul vine din `GEMINI_MODEL` (implicit `gemini-3.5-flash-lite`).
- Timeout-ul e de 10 s (minimul acceptat de API), fără reîncercări.
- Fallback-ul determinist e **cazul obișnuit**. Se folosește când:
  - lipsește cheia;
  - se depășește cota sau timpul;
  - JSON-ul e invalid;
  - textul e gol.

  Fallback-ul folosește reguli pe cuvinte cheie în română (cu sau fără diacritice) și numere din text („15 oameni”, „3 ore”).

## Tabloul de impact
`backend.impact.compute_impact(rezervări_aprobate)`. Doar rezervările **aprobate** intră în calcul.

| Indicator | Formulă |
|---|---|
| `idei_realizate` | numărul de idei distincte cu cel puțin o rezervare aprobată |
| `spatii_activate` | numărul de spații distincte cu cel puțin o rezervare aprobată |
| `rezervari_aprobate` | numărul de rezervări aprobate |
| `ore_folosite` | Σ (sfârșit - început) în ore, pe rezervările aprobate |
| `participanti` | Σ participanți pe rezervare (numărul de interese exprimate pentru idee) |
| `km_economisiti` | `participanti × 4 km` - **ESTIMARE** |

### `km_economisiti` este o estimare
Pornim de la o **ipoteză, nemăsurată**: fiecare participant care folosește un spațiu din zona lui, în loc să meargă la un spațiu central, evită în medie 4 km cu mașina (dus-întors).
- Constanta e `KM_PER_PARTICIPANT` din `backend/impact/core.py`.
- Răspunsul are `km_economisiti_estimare: true` și conține ipoteza în `ipoteze`.
- UI-ul trebuie să afișeze valoarea ca „estimare” (de ex. „≈ 160 km economisiți (estimare)”).
