# Date - Loc Comun

Sursele de date, ce e real și ce e generat, cum se calculează potrivirile și tabloul de impact. Responsabil: P3.

## Atribuire
Spațiile și cartierele provin din OpenStreetMap: **© OpenStreetMap contributors (ODbL)**.
Datele sunt disponibile sub licența Open Database License 1.0 (https://opendatacommons.org/licenses/odbl/).
Atribuirea trebuie afișată în UI oriunde apar spațiile sau harta (de ex. în subsolul listei și pe hartă).

## Surse
| Fișier | Conținut | Origine |
|---|---|---|
| `backend/seed/data/osm_spaces.json` | 87 de spații din Timișoara (nume, tip, coordonate, adresă dacă există) | OSM prin Overpass, descărcat pe 2026-11-13T21:19:58Z |
| `backend/seed/data/neighborhoods.json` | 44 de cartiere, cu centrul lor (lat, lon) | OSM (`place=suburb/quarter/neighbourhood`), descărcat pe 2026-11-13 |
| `backend/seed/data/demo.json` | 8 utilizatori, 7 idei, interese și rezervări, toate fictive | scrise manual |
| `backend/ai/eval_ideas.json` | 42 de idei etichetate manual, pentru măsurarea AI | scrise manual |
| `backend/seed/data/examples/*.json` | exemple de răspunsuri (idei, potriviri, notificări, impact) pentru web/mobil | generate: `python -m backend.seed.export_examples` |

Interogările complete și zona (bbox 45.70, 21.14 - 45.81, 21.32) sunt salvate în fișierele JSON.
Tipuri OSM incluse pentru spații:
- `amenity`: `community_centre`, `social_centre`, `library`, `arts_centre`, `cultural_centre`, `coworking_space`;
- `leisure`: `sports_centre`, `sports_hall`.

Sălile de fitness sunt excluse, fiind în mare parte lanțuri comerciale.
La cartiere, dublurile de nume (de ex. „Braytim - Timișoara Sud” / „Braytim-Timișoara Sud”) sunt unificate, iar zonele comerciale (Cora, Metro, zone industriale) sunt scoase.

## Fluxul datelor
1. `python -m backend.seed.fetch_osm` (spații) și `python -m backend.seed.fetch_osm neighborhoods` (cartiere) rulează **o singură dată**, folosesc rețeaua, iar fișierele rezultate se pun în git. Dacă primul server Overpass răspunde cu eroare, scriptul încearcă un server de rezervă.
2. `python -m backend.seed.run` merge **doar offline**:
   - citește JSON-urile;
   - generează înregistrările (`build.py` și `scenario.py`);
   - face upsert după id (`session.merge`).

   Poate fi rulat de oricâte ori: rezultatul e același în aceeași zi.

   Fiecare listă se scrie în modelul cu același nume din `backend.app.models` (User, Space, Slot, Idea, Interest, Booking, Notification). Se scriu doar câmpurile pe care modelul le are; modelele care lipsesc sunt sărite, cu un mesaj.

## Ce e real și ce e generat
Toate înregistrările din seed au `is_demo=true` și apar în UI cu insigna „exemplu”.

| Câmp | Real (OSM) | Generat |
|---|---|---|
| nume, tip, coordonate, adresă | da | - |
| cartier | - | cel mai apropiat centru de cartier din OSM |
| capacitate | - | valoare de bază per tip + 0-20, derivată din hash-ul id-ului |
| dotări (`amenities`) | - | 3 dotări de bază per tip + altele alese după hash; „acces persoane cu dizabilități” dacă OSM are `wheelchair=yes` |
| interior/exterior | - | bazele sportive cu „teren/bază/ștrand/arena” în nume sunt exterior |
| proprietar | - | unul dintre utilizatorii fictivi `demo-user-6..8` |
| sloturi | - | 3 zile pe săptămână, o fereastră orară, pentru următoarele 14 zile de la data rulării; `is_free=false` dacă slotul are o rezervare aprobată |
| utilizatori, idei, interese, rezervări, notificări | - | fictive; dosarele ideilor demo vin din fallback-ul determinist (fără Gemini) |

Ferestrele sloturilor (de ex. 18:00-20:00) sunt în ora locală a Timișoarei și sunt salvate în UTC. Pentru conversie folosim un decalaj fix +02:00 (ora de iarnă), pentru că mediul Windows nu are `tzdata`. Ora de vară (+03:00) e ignorată.

**Proprietarii și disponibilitatea sunt fictive.** Locurile există, dar nu au acceptat să fie pe platformă.
Locurile comerciale evidente (karting, paintball, săli de fitness, librării) sunt filtrate din seed.

## Scenariul demo
Demo-ul pornește cu idei în fiecare stare, ca toate ecranele să aibă conținut:

| Idee | Stare | Ce s-a întâmplat |
|---|---|---|
| demo-idea-1 (atelier biciclete) | `rezervata` | 4 interese, rezervare aprobată |
| demo-idea-2 (club de lectură) | `prag_atins` | 3 interese, rezervare cerută și încă nedecisă |
| demo-idea-3 (curs de programare) | `deschisa` | 2 interese, sub prag |
| demo-idea-4 (baschet 3x3) | `rezervata` | refuzată în primul spațiu, aprobată în al doilea |
| demo-idea-5..7 | `rezervata` | evenimente din ultimele 3 săptămâni, pentru istoricul din tabloul de impact |

- Spațiul fiecărei rezervări e ales cu `match_spaces`, pornind din cartierul autorului.
- Pragul de interes e 3, o **propunere**; P1 decide pragul real.
- Notificările generate:
  - `prag_atins`, către autor;
  - `cerere_rezervare`, către proprietar;
  - `rezervare_aprobata` / `rezervare_refuzata`, către autor.

  Fiecare are text în română și `read=false`.
- Valorile stărilor sunt **propuneri** pentru contract:
  - `IdeaStatus`: `deschisa`, `prag_atins`, `rezervata`;
  - `BookingStatus`: `ceruta`, `aprobata`, `refuzata`.

## Id-uri stabile
| Entitate | Format | Exemplu |
|---|---|---|
| Spațiu | `osm-<tip>-<id OSM>` | `osm-way-123456` |
| Utilizator | `demo-user-<n>` | `demo-user-1` |
| Idee | `demo-idea-<n>` | `demo-idea-1` |
| Slot | `<id spațiu>-slot-<AAAA-LL-ZZ>-<HHMM>` (dată și oră locale) | `osm-way-123456-slot-2026-11-21-1000` |
| Interes | `<id idee>-interest-<id utilizator>` | `demo-idea-1-interest-demo-user-2` |
| Rezervare | `demo-booking-<n>` | `demo-booking-1` |
| Notificare | `<id idee sau rezervare>-notif-<tip>` | `demo-booking-1-notif-aprobata` |

Tipul OSM (`node`/`way`/`relation`) face parte din id, pentru că OSM numerotează separat nodurile, căile și relațiile. Fără el, două elemente ar putea primi același id.
`fetch_osm.py` refuză să scrie fișierul dacă apar id-uri duplicate.

## Dosarul ideii (AI)
`backend.ai.structure_idea(text)` returnează `IdeaDossier`, cu `source` = `gemini` sau `fallback`.
- Modelul vine din `GEMINI_MODEL` (implicit `gemini-3.5-flash-lite`).
- Timeout-ul e de 10 s (minimul acceptat de API), fără reîncercări.
- Fallback-ul determinist e **cazul obișnuit**. Se folosește când:
  - lipsește cheia;
  - se depășește cota (pe nivelul gratuit apare des `429 RESOURCE_EXHAUSTED`);
  - se depășește timpul;
  - JSON-ul e invalid;
  - textul e gol.

  Fallback-ul folosește reguli pe cuvinte cheie în română (cu sau fără diacritice) și numere din text („15 oameni”, „3 ore”).

### Cât de bine merge (`python -m backend.ai.evaluate [--gemini]`)
| Set | Categorie | Participanți | Interior/exterior |
|---|---|---|---|
| fallback, set de ajustare (30 de idei) | 30/30 | 16/16 | 7/7 |
| fallback, **set nevăzut** (12 idei) | **9/12 (75%)** | 5/6 | 4/4 |
| Gemini `gemini-3.5-flash-lite`, toate cele 42 (2026-11-14, cu pauză de 4 s între cereri) | 39/42 (93%); 1 fără răspuns | 22/22 | 10/10 |

Gemini a răspuns în medie în 1,2 s. Fără pauze între cereri, nivelul gratuit a refuzat 12 din 30 de cereri (429), așa că în aplicație fallback-ul va fi folosit des.

Cifra cinstită pentru fallback este cea de pe setul nevăzut. Setul de ajustare a fost folosit la corectarea cuvintelor cheie, deci pe el rezultatul e prea optimist.
Testele (`tests/ai/test_eval.py`) cer cel puțin 90% pe setul de ajustare și 70% pe cel nevăzut, ca modificările să nu strice calitatea fără să observăm.

## Potrivirea spațiilor
`backend.ai.match_spaces(dosar, spații, origine, limit=10)` returnează o listă ordonată de `Match`. Fiecare `Match` conține `space_id`, `score` (0-100), `reason` (text în română), `distance_km`, `neighborhood` și `missing_needs`.
- Calculul e determinist și nu folosește Gemini.
- `origine` poate fi coordonate (lat, lon) sau numele unui cartier, de obicei cel al autorului.
- Funcția acceptă și obiecte ORM, nu doar dicționare.

| Criteriu | Puncte | Regulă |
|---|---|---|
| capacitate | 30 | încap toți: 30; încape cel puțin 80%: 15; peste 4× mai mare decât e nevoie: 20; sub 80%: **exclus** |
| dotări | 35 | 35 × (dotări cerute pe care spațiul le are / dotări cerute recunoscute); nicio dotare cerută: 35 |
| interior/exterior | 15 | compatibil sau „oricare”: 15; altfel 0 |
| tipul spațiului | 10 | tip potrivit categoriei (de ex. sport → bază sportivă): 10 |
| distanță | 10 | ≤ 1 km: 10, apoi scade liniar până la 0 la 8 km; fără origine: 5 |

- Ordinea: scor descrescător, apoi distanță, apoi id.
- Cererile pe care niciun spațiu nu le are în listă (de ex. „ceai”) nu scad scorul, dar apar în motiv: „de verificat cu proprietarul”.
- Funcția nu filtrează sloturile. P1 trebuie să trimită doar spațiile care mai au sloturi libere.

## Tabloul de impact
`backend.impact.compute_impact(rezervări_aprobate)`. Doar rezervările **aprobate** intră în calcul.
Pentru maparea rândurilor din baza de date în `ApprovedBooking`, exemplul de referință e `backend.seed.scenario.approved_for_impact`.

| Indicator | Formulă |
|---|---|
| `idei_realizate` | numărul de idei distincte cu cel puțin o rezervare aprobată |
| `spatii_activate` | numărul de spații distincte cu cel puțin o rezervare aprobată |
| `rezervari_aprobate` | numărul de rezervări aprobate |
| `ore_folosite` | Σ (sfârșit - început) în ore |
| `participanti` | Σ participanți pe rezervare (numărul de interese exprimate pentru idee) |
| `km_economisiti` | vezi mai jos - **ESTIMARE** |
| `pe_cartiere` | rezervări aprobate pe cartierul spațiului |
| `pe_tip_spatiu` | rezervări aprobate pe tipul spațiului (bibliotecă, centru comunitar...) |
| `pe_saptamani` | rezervări, ore și participanți pe săptămână ISO (`2026-W47`) |

### `km_economisiti` este o estimare
Valoarea se calculează dus-întors, pentru fiecare participant:
- Dacă îi știm cartierul: `max(0, distanța cartier→Cetate - distanța cartier→spațiu) × 2`. **Ipoteza** e că, fără spațiul local, participantul ar fi mers la un spațiu din centru (Cetate), cu mașina, și că distanța e în linie dreaptă.
- Dacă nu îi știm cartierul: `KM_PER_PARTICIPANT` = 4 km, o **ipoteză nemăsurată**.

Detalii pentru implementare și afișare:
- Rezultatul nu e niciodată negativ: cine merge mai departe decât în centru nu adaugă nimic.
- Răspunsul are `km_economisiti_estimare: true` și descrie metoda în `ipoteze`.
- UI-ul trebuie să afișeze valoarea ca „estimare” (de ex. „≈ 8 km economisiți (estimare)”).
