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

   Înregistrările interne sunt convertite în forma din contract (`backend/seed/contract.py`) și scrise în modelele lui P1 din `backend.app.models`: User, Space, Idea, Interest, Booking, Proiect, ProiectEveniment, Notification. Un model care lipsește e sărit, cu un mesaj.

## Legătura cu contractul (docs/CONTRACT.md)
Funcțiile pe care le apelează P1, prin `backend/app/p3.py`:

| Funcție | Ce face |
|---|---|
| `backend.ai.structure_idea(text) -> Structurat` | Construiește dosarul intern (Gemini sau fallback) și îl traduce în `Structurat`. Categoria: atelier → `creativ`, comunitate și mediu → `social`, temele IT → `tehnologie`. `persoane`; `dotari` în vocabularul contractului. `program` e completat **mereu**, pentru că potrivirea lui P1 se calculează pe el: zilele și orele din text („sâmbătă 10-13”, „joi seara”, „în weekend”); fără zi în text, se propune weekendul, la ora din text (altfel 10:00), cu durata estimată. `zgomot` din cuvinte cheie; `rezumat` de cel mult 80 de caractere, fiindcă e titlul implicit. |
| `backend.ai.owner_message(idea, space, slot) -> str` | Scrie cererea politicoasă către proprietar: ideea, numărul de vecini interesați, spațiul, ziua și ora, dotările necesare. |
| `backend.impact.compute_impact(session) -> Impact` | Citește tabelele lui P1, cu aceleași definiții ca `backend/app/services/impact.py` al lui P1. `ore_recuperate` = orele rezervărilor `aprobat`. `oameni_conectati` = utilizatorii distincți interesați de ideile cu rezervare aprobată. `km_economisiti` = ESTIMARE, pe fiecare participant (`Idea.interesati`): distanța dus-întors economisită pentru cei care locuiesc în oraș (sub 25 km de Cetate), altfel 4 km. `proiecte_active` = ideile `prag_atins` sau `rezervata`. `proiecte_trimise` și `proiecte_cu_acord` vin din tabelul `Proiect`. |

Calculul detaliat (pe cartiere, pe săptămâni, proiecte trimise) rămâne disponibil intern, ca `backend.impact.impact_report`.

Seed-ul în forma contractului:
- **Roluri:** `locuitor` devine `cetatean`; `proprietar`, `primarie` și `verificator` rămân la fel.
- **Teren liber și proiect:** terenul liber e un `Space` cu `tip = teren_liber` (valoarea din contract) și `suprafata_mp`. Proiectul demo are `verificator_id` = contul de verificator care l-a preluat. Evenimentele lui și notificările cu `proiect_id` intră și ele în baza de date.
- **Utilizatori:** `lat`/`lng` sunt centrul cartierului.
- **Spații:** `tip` = eticheta în română (bibliotecă, centru comunitar...), cu excepția terenului liber, care are `teren_liber`; `dotari` sunt traduse în vocabularul contractului.
- **Sloturi:** `sloturi` e programul săptămânal, în ora Timișoarei, fără sloturile ocupate de rezervările aprobate.
- **Rezervări:** `slot` e intervalul săptămânal; `stare` e `cerut`, `aprobat` sau `refuzat`.
- **Exemple pentru web/mobil:** `backend/seed/data/examples/*.json` au forma din contract. `impact.json` e calculat cu `compute_impact` pe o bază temporară.

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
| `proiecte_trimise` | proiectele trimise către Primărie: orice stare în afară de `draft` |
| `proiecte_cu_acord` | proiectele în starea `acord_de_principiu` (acord **simulat** în aplicație) |

Pentru proiecte, apelul este `compute_impact(rezervări_aprobate, proiecte)`. `proiecte` poate conține rânduri, dicționare sau direct stările. Parametrul e opțional, deci apelurile vechi rămân valabile.

### `km_economisiti` este o estimare
Valoarea se calculează dus-întors, pentru fiecare participant:
- Dacă îi știm cartierul: `max(0, distanța cartier→Cetate - distanța cartier→spațiu) × 2`. **Ipoteza** e că, fără spațiul local, participantul ar fi mers la un spațiu din centru (Cetate), cu mașina, și că distanța e în linie dreaptă.
- Dacă nu îi știm cartierul: `KM_PER_PARTICIPANT` = 4 km, o **ipoteză nemăsurată**.

Detalii pentru implementare și afișare:
- Rezultatul nu e niciodată negativ: cine merge mai departe decât în centru nu adaugă nimic.
- Răspunsul are `km_economisiti_estimare: true` și descrie metoda în `ipoteze`.
- UI-ul trebuie să afișeze valoarea ca „estimare” (de ex. „≈ 8 km economisiți (estimare)”).

## Propunere către Primărie
Fluxul complet: o idee care a atins pragul devine o propunere de amenajare pe un teren liber. Propunerea are un dosar generat automat, proiecte de referință reale și o estimare de cost.

### Orice propunere
Propunerea poate fi despre **orice**: skatepark, parc acvatic, fântână arteziană, bibliotecă stradală, observator astronomic etc. Nu există o listă închisă.

Pentru P1 există o singură funcție: `backend.ai.proposal.prepare_proiect(idea, space, suprafata_mp, tip_amenajare=None)`. Ea întoarce `tip_amenajare`, `eticheta`, `referinte`, `cost` și `dosar`, adică exact câmpurile de proiect de care răspunde P3. Pașii:

1. **Încadrare** (`classify_proposal(text)`), sărită dacă tipul e dat explicit:
   - Gemini citește textul ideii și dă o etichetă scurtă, de ex. „parc acvatic”, plus cuvinte de căutare.
   - Fără Gemini, regulile pe cuvinte cheie recunosc formulările obișnuite. Pentru orice altceva, eticheta e obiectul din prima frază („Vrem un aquapark pentru copii” → „aquapark”).
   - Sinonimele ajung la același tip, deci „parc pentru câini”, „loc de joacă pentru câini” și „dog park” dau toate `parc_caini`.
2. **Referințe** (`find_references`): întâi baza locală; dacă are prea puține date, căutarea live.
3. **Documentare** (`research_notes`), doar cu căutarea live pornită: AI-ul caută ce presupune de obicei un astfel de proiect (componente, capacitate, etape, studii, riscuri). Notițele sunt trimise lui Gemini pentru dosar, iar propozițiile cu sume de bani sunt scoase înainte.
4. **Cost și dosar**: `estimate_cost` și `generate_dosar`, ca mai jos.

Dacă nu există date, rezultatul e tot un dosar complet: cost „date insuficiente” cu motiv, componente, etape, riscuri și lista de verificare. Nu se inventează nicio cifră.

### Baza de referințe
Baza e formată din proiecte realizate, licitate sau aprobate în alte orașe din România. Le folosim ca termen de comparație și pentru cost.

- **Unde:** `backend/ai/references/data/<tip_amenajare>.json`, câte un fișier pentru fiecare tip. Fiecare intrare are forma `Referinta`.
- **Colectare:** manuală, pe 2026-11-14. Fiecare pagină a fost deschisă și citită. PDF-urile primăriilor au fost citite local, cu `pdftotext`.
- **Regula:** o cifră care nu apare în sursă rămâne `null`; nu estimăm. Componentele sunt scrise cu cuvintele noastre.

| Tip | Intrări valide | Cu cost și suprafață | Surse |
|---|---|---|---|
| `skatepark` | 6 | 6 | presă locală (economica.net, zf.ro, alba24.ro, economedia.ro) |
| `loc_de_joaca` | 6 | 5 | presă locală, comunicatul Primăriei Carei |
| `pista_biciclete` | 5 | 3 | presă locală (bzi.ro, alba24.ro), comunicatul Primăriei Călărași |
| `parc_caini` | 3 | 0 | presă (g4media.ro, actualdecluj.ro) |
| `teren_sport` | 2 | 1 | presă (alba24.ro, bzi.ro) |
| `gradina_comunitara`, `foisor` | 0 | 0 | nu s-au găsit surse cu cifre; acoperite de căutarea live |

### Limite
- Majoritatea sumelor sunt **valori estimate din licitații sau bugete aprobate**, nu costuri finale.
- TVA-ul e precizat rar.
- Uneori suprafața e a întregului amplasament (parc cu skatepark, parc cu loc de joacă), nu doar a amenajării.
- La valorile date în sursă cu „peste” sau „aproape”, am păstrat cifra rotundă din sursă: Sibiu, „peste 10.000 mp”; Timișoara, „aproape 4.300 mp” și „peste 11 mil. lei”.
- Unele surse nu au putut fi folosite pentru cost:
  - Alba Iulia, Dealul Mamut: suprafața e dată pe tronsoane, nu total;
  - Sibiu, parcuri pentru câini: 3 × 300 mp, fără total;
  - Răducăneni: costul include și o sală de sport;
  - Alba Iulia, Vasile Goldiș: valoarea e doar pentru proiectare.

  Acolo cifra lipsă rămâne `null`.
- Iași, CUG II: suma de 3.459.693 lei este **varianta 1** din două propuse consiliului local. Sursa nu spune care variantă a fost aprobată.
- Galda de Jos: suprafața publicată (10.076 mp) e aproape dublul produsului lungime × lățime (2.520 m × 2 m), deci costul pe mp iese probabil subestimat. Cifra e păstrată exact cum apare în sursă.
- Sumele în euro nu sunt convertite (nu inventăm un curs).
- Populațiile pentru departajare sunt în `data/_populatie.json` (Recensământul 2021, cu link). Comunele lipsesc și ajung ultimele la departajare.

### Cum se adaugă o intrare
1. Deschide pagina sursei și copiază doar ce scrie acolo: orașul, anul, suprafața în mp și valoarea în lei.
2. Adaugă intrarea în `data/<tip>.json`:
   - `id`: `<tip>-<oras>-<an>`;
   - `sursa_url`: linkul paginii;
   - `sursa_tip`: una dintre `achizitie_publica`, `hotarare_consiliu`, `comunicat_primarie`, `date_deschise`, `presa`;
   - `data_accesarii`: data de azi.
3. Rulează `python -m backend.ai.references.validate`. Comanda iese cu cod 1 dacă vreo intrare e respinsă și spune de ce.

### `find_references(tip_amenajare, suprafata_mp, k=5)`
- `tip_amenajare` poate fi orice text. Sinonimele cunoscute ajung la tipul din contract („Parc pentru câini” → `parc_caini`); restul e transformat în identificator („Fântână arteziană” → `fantana_arteziana`). Pentru tipurile fără date întoarce `[]` (sau ce găsește căutarea live).
- Ordinea:
  1. diferența relativă de suprafață față de cea cerută, `|a − b| / max(a, b)`, rotunjită la 0,01; intrările fără suprafață ajung la final;
  2. la egalitate, anul (cel mai recent primul);
  3. apoi mărimea orașului, cel mai apropiat de Timișoara primul;
  4. apoi id-ul.

### Căutarea live
Căutarea live e **pornită implicit** când există o cheie Gemini. `REFERENCES_LIVE_SEARCH=false` o oprește; testele, seed-ul și e2e o țin oprită. Proiectele se caută doar când baza locală are sub 2 intrări cu cost și suprafață.

1. Gemini cu Google Search caută proiecte de tipul cerut, întâi în România. Dacă găsește mai puțin de 3, caută și în alte țări europene: proiectele de acolo apar ca exemple (oraș, țară), dar **nu intră în calculul costului**. A doua cerere Gemini extrage proiectele în JSON.
2. Fiecare proiect trebuie să indice una dintre sursele returnate de căutare. Linkurile scrise de model sunt ignorate.
3. Serverul deschide sursa și urmează redirecționările pas cu pas. Fiecare adresă e verificată înainte: doar http(s), doar adrese IP publice (protecție SSRF). Limite: 8 s, 2 MB.
4. O cifră e păstrată doar dacă **apare în pagină**:
   - costul, lângă „lei”/„RON”, inclusiv formele „11 mil. lei” și „1.250.000,00 RON”;
   - suprafața, lângă „mp”/„m²”.

   Altfel cifra rămâne `null`. Intrările cu cifre confirmate primesc `sursa_tip = cautare_ai_verificata`, iar celelalte `cautare_ai`.
5. Rezultatele se salvează în `backend/ai/references/cache/<tip>.json` (ignorat de git), pentru 7 zile.
6. Căutarea are o limită de timp totală (`REFERENCES_SEARCH_BUDGET_S`, implicit 25 s). Când se termină, se folosesc candidații verificați până atunci și nu se salvează nimic în cache, ca o cerere ulterioară să termine căutarea. Orice eroare (cotă 429, timeout) întoarce `[]` și se folosește baza locală. Pentru demo e recomandat `REFERENCES_LIVE_SEARCH=false`, ca nimic să nu depindă de rețea.

### `estimate_cost(referinte, suprafata_mp)`
Calculul e determinist și nu folosește AI.

- Pentru fiecare referință cu **cost și suprafață**: `cost pe mp = cost_total_lei / suprafata_mp`.
- Rezultatul: `min`, `mediană` și `max` din costurile pe mp, înmulțite cu suprafața propusă și rotunjite la 100 de lei.
- **Sub 2 referințe utilizabile:** `suficient = false`, fără nicio cifră, cu `motiv`.
- `ipoteze` descrie de unde vin cifrele: numărul de proiecte, anii și orașele; prețuri nominale, fără inflație; TVA așa cum apare în sursă; estimări din licitații. Dacă au fost folosite intrări găsite live, o spune și pe asta.
- Exemplu: skatepark de 600 mp, pe baza locală de azi: între 175.700 și 1.534.900 lei, mediană 733.300 lei, din 5 proiecte. Intervalul e mare pentru că proiectele de referință diferă mult ca dotări.

### `generate_dosar(idea, space, tip_amenajare, suprafata_mp, referinte, cost)`
- Gemini scrie textul pornind de la idee, spațiu și componentele referințelor. **Nu vede nicio cifră de cost**, nici pe cele ale referințelor, ci doar dacă estimarea e disponibilă.
- Răspunsul e validat cu Pydantic. Dacă textul conține o sumă de bani (lei, RON, euro, €, „mii/milioane de lei”), răspunsul e respins. Se încearcă **încă o dată**, apoi se folosește **șablonul de rezervă**, care are aceeași formă și nu folosește Gemini.
- Codul adaugă apoi:
  - textul obligatoriu (regula 10 din contract), la finalul `justificare`: „Estimare orientativă, bazată pe proiecte de referință. Nu reprezintă o autorizație; acordul din aplicație este un acord de principiu simulat.”;
  - **nicio cifră de cost în textul dosarului**: costul stă doar în obiectul `Cost` (interval, mediană, ipoteze sau `motiv`), pe care UI-ul îl afișează separat. Dacă estimarea nu e posibilă, motivul e tot în `Cost.motiv`.
  - punctele de bază din `lista_verificare` (cine administrează terenul, planurile urbanistice, eventualele avize, finanțarea, întreținerea), formulate ca întrebări de clarificat, fără afirmații legale ferme.
- `referinte_citate` păstrează doar id-uri din lista primită.
- Contractul cere lei și mp ca numere întregi: la ieșire, `cost_total_lei` și `suprafata_mp` sunt rotunjite, iar baza păstrează zecimalele din sursă.
- Sumele scrise de utilizator în textul ideii nu sunt copiate în dosar.

### Datele demo
Fișier: `backend/seed/data/proiect_demo.json`, construit de `backend/seed/proiect_demo.py`. Totul are `is_demo=true`.

- **Utilizatori:** `demo-user-9` (`primarie`) și `demo-user-10` (`verificator`).
- **Teren liber:** `demo-space-teren-1`, `kind=teren_liber`, 600 mp, în Fabric, deținut de contul de primărie. Locul e fictiv: coordonatele sunt centrul cartierului. Nu are sloturi și nu apare la potriviri (capacitate 0).
- **Idee:** `demo-idea-8` (skatepark), cu 4 interese, deci în starea `prag_atins`.
- **Proiect:** `demo-proiect-1`, în starea `in_verificare`, cu evenimentele `draft → trimis → in_verificare`.
  - Dosarul e generat din șablon, iar referințele vin doar din baza locală, deci seed-ul nu folosește rețeaua.
  - Notificări: `proiect_trimis` către autor și primărie, `proiect_in_verificare` către autor.
- Seed-ul scrie `Proiect` și `ProiectEveniment` în modelele lui P1. Exemple pentru web/mobil: `backend/seed/data/examples/proiecte.json`, `proiect_evenimente.json` și `teren_liber.json`.

### Comenzi
```
python -m backend.ai.references.validate     # verifică baza de referințe
python -m backend.seed.run                   # seed (offline, idempotent)
python -m backend.seed.export_examples       # regenerează exemplele pentru web/mobil
python -m pytest backend/tests tests/e2e     # teste (fără Gemini live, fără rețea)
```

## Terenuri din lista Primăriei (Legea 15/2003)
**Ipoteză de lucru a echipei:** terenurile din lista validată de Consiliul Local pentru Legea 15/2003 sunt folosite în aplicație ca terenuri libere ale Primăriei. În aplicație apar doar ca „din lista Primăriei, de confirmat”.

**Atenție la două lucruri:**
- Legea 15/2003 destinează aceste parcele **locuințelor tinerilor**.
- Parcelele pot fi **atribuite între timp**.

### Sursele (colectate pe 2026-11-14)
- **Site-ul oficial:** [primariatm.ro/hcl](https://www.primariatm.ro/hcl). `hcl.usr.ro` nu a fost folosit, pentru că interzice accesul automat (`robots.txt`: `Disallow: /`).
- **[HCL 20/29.01.2019](https://www.primariatm.ro/hcl/2019/20), Anexa nr. 1:** lista comisiei pentru Legea 15/2003, nr. SC2019-276. Are text, deci a putut fi extrasă: **128 de parcele**, toate pe str. Lt. Ovidiu Balea (Ronaț), cu 276 mp (80 de parcele) și 252 mp (48). Anexa dă doar CF-ul și numărul cadastral, fără număr de stradă.
- **[HCL 25/2020](https://www.primariatm.ro/hcl/2020/25):** documentele sunt **scanate** (imagini fără text) și nu au putut fi citite automat.
- **Ediții 2021–2026:** nu au fost găsite publicate.
- **Documentele originale** sunt în `backend/seed/data/sursa/l15/`, cu `manifest.json` (URL-ul oficial al fiecărui document). Scanările din 2020 nu sunt comise. Lista extrasă e în `backend/seed/data/terenuri_l15_2019.json`.

### Locația
- Geocodarea s-a făcut o singură dată, cu Nominatim (OpenStreetMap, ODbL), cu cel mult 1 cerere pe secundă. Rezultatul e în cache, în `backend/seed/data/geocode_cache.json`.
- Strada nu există ca obiect separat în OSM. Punctul folosit e o adresă de pe aceeași stradă, marcat `locatie_aproximativa`.
- **Pe hartă**, parcelele sunt așezate **una lângă alta**: un rând de loturi alăturate de circa 12 m (un lot de 276 mp are aproximativ 12 m × 23 m), în ordinea din listă, centrat pe punctul străzii. Anexa nu publică poziția fiecărei parcele, deci așezarea e **schematică** (`pozitie_schematica` în `sursa_detalii`). Limitele reale sunt în cadastru, după CF și numărul cadastral.

### Regula din seed (`backend/seed/terenuri.py`)
- **Filtrul:** suprafață de cel puțin **250 mp** (prag stabilit de echipă; inițial 300 mp, pe care nu-l atingea nicio parcelă) și locație găsită.
- **Selecția:** cele mai bune **15** (suprafața cea mai mare, apoi ordinea din listă). Dacă rămân sub 5, nu se adaugă nimic.
- **Fiecare teren** e un `Space` cu:
  - `tip = teren_liber`, `suprafata_mp`, `sloturi = []`, `capacitate = 0`, deci nu apare la potriviri;
  - proprietar contul de primărie (`demo-user-9`) și **`is_demo = false`**;
  - `sursa = lista_primarie` și `sursa_detalii = „HCL 20/2019, anexa nr. 1, poz. <n>; locatie_aproximativa”`;
  - id-ul `lista-2019-<cf>`.
- **Câmpurile `sursa` și `sursa_detalii`** nu sunt încă în contract. Seed-ul le trimite, iar ele se salvează imediat ce P1 le adaugă în modelul `Space`.
- **Dosarul:** pentru aceste terenuri, `generate_dosar` pune primul în `lista_verificare` punctul: „Confirmarea faptului că terenul nu a fost atribuit între timp (Legea 15/2003) și a disponibilității lui pentru uz comunitar”.
- **Câmpuri de contract:** au `cartier` (cel mai apropiat centru de cartier din OSM) și `status_verificare = neconfirmat`.

## Cartier și stare de verificare pe toate spațiile din seed
- `Space.cartier` = cartierul calculat de seed (cel mai apropiat centru de cartier OSM), pentru toate spațiile, inclusiv terenurile libere.
- `Space.status_verificare`:
  - `neconfirmat` pentru terenurile din lista Primăriei și pentru cele din OSM;
  - gol pentru spațiile obișnuite și pentru terenul demo (fictiv);
  - `neverificat` pentru terenurile marcate de utilizatori prin `POST /spaces` (P1, regula 14).

## Terenuri libere din OpenStreetMap (lista lui P2)
- **Fișierul:** `backend/seed/data/terenuri_osm.json`, copia identică a listei lui P2 (`web/src/mocks/data/terenuri_osm.json`, ramura `p2-front`, generată cu `web/scripts/terenuri_osm.py`).
  - 8 terenuri, câte unul pe cartier: Bucovina, Cartierul Vienez, Complex Studențesc, Dorobanților, Mehala, Steaua, Tipografilor, Torontalului.
  - Suprafețe între 1.140 și 4.383 mp.
- **Cum au fost alese (de P2, 2026-11-15):**
  - poligoane OSM `landuse=brownfield|greenfield|vacant`, fără nume, de 400–5.000 mp;
  - fiecare privit pe imagini din satelit (Esri World Imagery): au rămas cele care arată libere;
  - **nu s-au verificat** proprietarul, regimul juridic și zonarea;
  - suprafața e calculată din poligon.
- **Atribuire:** © OpenStreetMap contributors, ODbL 1.0.
- **Seed-ul are acum 24 de terenuri libere:** 15 din lista Primăriei, 8 din OSM și cel demo. Cu ele, un skatepark de peste 500 mp are 9 variante, nu doar terenul demo.
- Fără fișier, `build_terenuri_osm()` întoarce `[]`.
- **Format acceptat:** o listă (sau `{"terenuri": [...]}`) de rânduri cu `nume`/`name`, `lat`, `lng`/`lon`, `suprafata_mp` și opțional `id`, `cartier`, `adresa`, `sursa_detalii`.
- **Ce se sare:** rândurile fără coordonate, fără suprafață sau în afara Timișoarei (lat 45,6–45,9, lng 21,0–21,45).
- **Fiecare teren devine un `Space`** cu:
  - `tip = teren_liber`, **`is_demo = true`** (insigna „exemplu”);
  - `sursa = osm`, `status_verificare = neconfirmat`;
  - `cartier` calculat dacă lipsește;
  - id-ul `teren-osm-<id OSM>`;
  - proprietar contul de primărie. Proprietarul real, regimul juridic și disponibilitatea nu sunt cunoscute și apar în `sursa_detalii`.

## Planul schematic (`backend/ai/proiect/design/`)
`backend.ai.proiect` e acum pachet; importurile vechi (`from backend.ai.proiect import generate_dosar`) rămân valabile.

- `build_scene(tip_amenajare, suprafata_mp, latime_m=None) -> Scene`: amplasare deterministă, fără AI. Coordonate în metri, originea în colțul stânga-jos, axa y în sus (ca în CAD).
  - Forma: dreptunghi 2:3 cu suprafața dată; cu `latime_m` (de ex. lot de 12 m) lungimea rezultă din suprafață.
  - Margine liberă de 1 m pe contur, alee de acces de 1,5 m pe latura de jos (la pista de biciclete: buclă de 2,5 m pe contur).
  - Elementele se așază pe rânduri, în ordinea din catalog (elementul principal primul). Fiecare își păstrează zona liberă din jur; ce nu încape nu se desenează, ci apare în `omise`, cu motiv. `complet = false` dacă lipsește un element obligatoriu.
  - Orice tip: tipurile din catalog (cele 6 din contract + foișor) au elemente proprii; orice alt text („fântână arteziană”) primește o zonă propusă și mobilier de bază, fără detalii inventate.
- **Dimensiunile din `catalog.py` sunt ipoteze schematice ale aplicației**, nu valori din standarde sau fișe de produs. Scena le enumeră în `ipoteze`, iar fiecare plan poartă `PLAN_DISCLAIMER`: „Plan schematic orientativ, generat automat. Nu este un proiect tehnic: dimensiunile sunt ipoteze de lucru, iar amplasarea reală o stabilește un proiectant autorizat, după măsurători pe teren.”
- `build_plan_svg(scene, titlu)`: SVG de sine stătător; elementele sunt numerotate, cu legendă, cote și note.
- `build_plan_dxf(scene, titlu)`: DXF ASCII R12 (AC1009), scris manual (`ezdxf` cere numpy). Doar entități R12: POLYLINE închis, LINE, TEXT (cotele sunt LINE + TEXT). Straturi: `TEREN`, `ELEMENTE` (cu zonele libere în gri), `COTE`, `TEXT`. Diacriticele sunt transliterate (R12 are text ASCII).
- Exemple: `python -m backend.seed.export_planuri` scrie `backend/seed/data/exemple/plan_<tip>_<mp>mp.{json,svg,dxf}`: fiecare tip pe 600 mp (terenul demo) și două loturi de 276 mp × 12 m, ca cele din lista Primăriei.

## Alegerea terenului (`find_plots`)
`backend.ai.proiect.find_plots(tip_amenajare, suprafata_minima, cartier=None, spaces=None, limit=10) -> list[PlotCandidate]`. Fiecare candidat are `space_id`, `nume`, `cartier`, `suprafata_mp`, `scor` (0-100), `motiv` (în română), `complet`, `din_lista_primarie`, `is_demo`, `distanta_km`.

- Candidații: Space-urile `teren_liber`. Implicit, cele din seed (cele 15 loturi `lista-2019-*` și terenul demo); P1 poate trimite rândurile din baza de date (dicționare sau obiecte ORM).
- Terenurile sub `suprafata_minima` sunt excluse.

| Criteriu | Puncte | Regulă |
|---|---|---|
| încape | 60 | 45 dacă toate elementele obligatorii încap pe planul schematic, + 15 × fracția dotărilor opționale care încap |
| loc | 30 | în cartier: 30; altfel ≤ 1 km: 30, apoi scade liniar până la 0 la 8 km; fără cartier sau cartier necunoscut: 15 |
| mărime | 10 | ≤ 2× suprafața minimă: 10; ≤ 4×: 5; mai mare: 0 (un teren mare rămâne pentru un proiect mai mare) |

- Ordinea: scor, apoi terenul mai mic, apoi id-ul.
- Loturile din listă sunt desenate cu 12 m lățime, ca pe hartă. Motivul lor spune mereu „din lista Primăriei (Legea 15/2003), de confirmat: poate fi atribuit între timp”.
- Loturile nu se unesc: pozițiile lor sunt schematice, deci alăturarea ar fi inventată. Consecință: un skatepark de peste 276 mp găsește azi doar terenul demo.

## Prețuri unitare (SEAP, date deschise)
**Nu există o sursă publică de prețuri unitare per articol.** Ce am verificat pe 2026-11-14:
- **Standardele de cost** pentru investiții publice (HG 363/2010, HG 1394/2010) au fost **abrogate în 2018**. Ordinul MDLPA 1321/2021 (Anghel Saligny) are plafoane doar pentru apă, canalizare și drumuri.
- **Contractele SEAP și OpenTender** au doar valori totale.
- **Studiile de fezabilitate publicate** dau de obicei doar totalul (de ex. SF Sector 6, skatepark și parc pentru câini: 1.105.529,39 lei fără TVA).

**Sursa folosită:** exporturile „Achiziții directe” din seturile [achizitii-publice-&lt;an&gt;](https://data.gov.ro/dataset/achizitii-publice-2025) de pe data.gov.ro, publicate de Autoritatea pentru Digitalizarea României, cu licența **CC BY 4.0** (2021+). Atribuirea trebuie afișată oriunde apar prețurile.
- **Limita setului:** fiecare achiziție are o denumire liberă, un cod CPV și valoarea, dar **nicio coloană de cantitate**.
- **Regula (`backend/ai/proiect/preturi.py`):** o achiziție devine observație doar dacă denumirea are **un singur articol** și **o singură cantitate explicită** în unitatea articolului: „Achizitie 30 buc. Banci pentru parc”, „MONTAJ PAVELE BETON 100 mp”.
  - Sunt excluse pachetele, seturile, loturile, reparațiile, serviciile și denumirile cu două articole („pergola cu 2 bănci si masa”, „… + remodelare teren”).
  - Sunt excluse și cantitățile pe palet („9,6 MP/PAL”) și materialele care nu sunt articolul (bandă de avertizare, plasă de gard).
  - Fiecare articol are coduri CPV permise.
- **Prețul unitar** = valoarea achiziției / cantitate. Un articol are preț doar cu **cel puțin 3 observații** (prag fixat înainte de rezultate). Se afișează mediana, min–max, numărul de observații, perioada și numerele DA cele mai apropiate de mediană.
- **TVA: neprecizat în setul de date.** Valorile sunt prețuri plătite de cumpărători publici, nu un standard.
- **Colectare:** `python -m backend.seed.fetch_preturi` (o singură dată, cu rețea). Rezultatul e `backend/ai/proiect/data/preturi_seap.json`, cu fiecare observație (DA, dată, CPV, denumirea originală, cantitate, valoare), ca să poată fi verificată rând cu rând. Testele reaplică regulile pe fiecare observație comisă.
  - Fișierele `.xls` vechi și `.ods` sunt sărite (fără dependențe), iar lista lor e în JSON.
  - Coloanele diferă între ani: 2023 T IV are `VALOARE_ATRIBUITA_RON`, 2023 T III are `VALOARE_ACHIZITIE`, 2025+ are `VALOARE_ACHIZITIE_RON`. JSON-ul notează coloana folosită.
  - Formatele diferă și ele: 2023 T IV e CSV cu `,` și ghilimele `|`, 2023 T III e CSV cu `|` și ghilimele `"`, iar 2024 T IV e un XLSX cu rândurile pe 11 foi.
  - `--refilter` reaplică regulile pe fișierul comis, fără rețea; regulile devin doar mai stricte.

**Rezultatul rulării din 2026-11-15:**
- 9 fișiere citite (2023 T III – 2026 T III), circa 5,4 milioane de rânduri; 10 fișiere `.xls`/`.ods` sărite.
- **45 de observații**, fiecare verificată manual după rulare.
- Verificarea manuală a scos potriviri greșite, care au devenit teste negative în `test_preturi.py`:
  - „GARDLOX … SPRAY 30ML”: medicament, iar „ml” înseamnă mililitri;
  - „ROLA DE 1 MP”: mărimea unei role, nu cantitatea cumpărată;
  - reparații, recondiționări, piese de schimb;
  - un „foișor de pază tip container”;
  - covoare industriale din cauciuc;
  - o factură copiată în denumire.

| Articol | Observații | Mediană | Min – max |
|---|---|---|---|
| bancă de parc | 8 | 1.575 lei/buc | 550 – 2.979 |
| coș de gunoi stradal | 3 | 290 lei/buc | 149 – 1.350 |
| pardoseală sintetică (cauciuc / tartan) | 7 | 148,29 lei/mp | 101,01 – 318,19 |
| gazon în rulou | 9 | 25 lei/mp | 13,5 – 38 |
| împrejmuire (gard) | 13 | 345,67 lei/ml | 85,71 – 1.028 |
| leagăn, balansoar, tobogan, structură de joacă, rastel, foișor, masă de picnic, compostor, pavaj | 0 – 2 | **de cotat** | – |

Intervalele sunt mari pentru că produsele diferă mult (bancă simplă din lemn sau bancă de beton; gard din plasă sau gard de 5 m la un teren de sport). De aceea se afișează mereu și min–max.

**Exemple pentru web/mobil:** `python -m backend.seed.export_planuri` scrie și `backend/seed/data/exemple/proiect_demo_*`. Acestea sunt răspunsurile `/plan` și `/materiale` și cele patru documente ale proiectului demo, cu prețurile de mai sus.

## Lista de materiale (`lista_materiale(scene)`)
- Cantitățile vin din planul schematic. Fiecare linie are `ipoteza`, de exemplu:
  - bănci = câte sunt pe plan;
  - alee pavată = suprafața aleii;
  - pardoseală de protecție = echipamentele de joacă cu zona lor liberă;
  - gard = perimetrul;
  - gazon = suprafața rămasă.
- Fără preț (sub 3 observații sau articol fără sursă) linia e **„de cotat”**, cu motivul.
- `subtotal_cotat_lei` acoperă doar liniile cotate și se afișează **doar** ca „Subtotal articole cotate (incomplet: N articole de cotat)”. **Nu este costul proiectului**; estimarea de cost rămâne `Cost` (din proiecte de referință).

## Documente (`backend.ai.proiect.documente`)
- `build_documente(proiect, space) -> {"plan.svg", "plan.dxf", "dosar.pdf", "materiale.csv": (bytes, media type)}`, plus `plan_json` și `materiale_json`.
- Proiectul și spațiul sunt în forma din contract (dicționare sau rânduri ORM; `dosar`/`cost` pot fi și text JSON). Rezultatul e determinist.
- **Dosarul PDF** e scris manual (PDF 1.4, fără dependențe):
  - conținut: textele dosarului, estimarea de cost, referințele, planul desenat vectorial, lista de materiale și textul din regula 10;
  - fonturi: Helvetica standard, cu codificare pentru ă/ș/ț (`/Differences` + `/ToUnicode`, deci copierea și căutarea dau ș/ț corecte);
  - fără dată de creare, ca fișierul să fie identic la fiecare generare.
- **`materiale.csv`:** separator `;`, virgulă zecimală, UTF-8 cu BOM, ca să se deschidă direct în Excel în română.
- Terenurile din lista Primăriei sunt desenate cu 12 m lățime, iar dosarul lor spune „de confirmat”.
- **Cereri către P1** (propunere de contract):
  - `GET /terenuri/potrivite`, `GET /proiecte/{id}/plan`, `GET /proiecte/{id}/materiale`;
  - `GET /proiecte/{id}/documente/{plan.svg|plan.dxf|dosar.pdf|materiale.csv}`;
  - vizibilitatea e aceeași ca la `GET /proiecte/{id}`.

## Stratul LLM: lanț de rezervă peste furnizori gratuiți
Funcțiile `structure_idea`, `owner_message`, `classify_proposal` și `generate_dosar` nu mai depind doar de Gemini. Toate trec prin `backend.ai.llm.generate_json(prompt, schema, system=None, task=..., validator=None)`, care încearcă, în ordine, toate modelele gratuite configurate. Dacă niciunul nu răspunde valid, funcția apelantă folosește fallback-ul determinist de până acum. Semnăturile din contract nu se schimbă.

Căutarea pe web pentru referințe (`references/search.py`, Google Search grounding) rămâne doar pe Gemini, pentru că ceilalți furnizori nu au căutare.

### Registrul (`backend/ai/llm/registry.json`)
- **Sursa:** construit o singură dată, pe 2026-11-14, din [mnfst/awesome-free-llm-apis](https://github.com/mnfst/awesome-free-llm-apis). Lista cerută inițial, `cheahjs/free-llm-api-resources`, nu mai există (404).
- **Aplicația nu descarcă lista;** citește doar registrul comis în repo.
- **Ce conține:** 14 furnizori și toate modelele lor care pot genera text. Lipsesc doar modelele de embeddings, care nu pot răspunde la un prompt.

| Furnizor | Cheie în `.env` | Modele | Limite gratuite | Stare |
|---|---|---|---|---|
| Google Gemini | `GEMINI_API_KEY` | 8 | Google no longer publishes per-model free-tier limits; check quotas in AI Studio. de_verificat | ok |
| Groq | `GROQ_API_KEY` | 3 | 8,000 TPM, 200,000 TPD per model on the Free Plan | ok |
| OpenRouter | `OPENROUTER_API_KEY` | 11 | Counted across ALL free models together; 1,000 RPD after buying 10 credits | ok |
| Cohere | `COHERE_API_KEY` | 11 | Trial key: 1,000 API calls per MONTH; non-commercial use only | ok |
| NVIDIA NIM | `NVIDIA_API_KEY` | 2 | No public table; varies per model and load. de_verificat | ok |
| Cloudflare Workers AI | `CLOUDFLARE_API_KEY + CLOUDFLARE_ACCOUNT_ID` | 7 | 10,000 Neurons/day shared across all models, reset 00:00 UTC; over the limit the request fails (no billing) | ok |
| Z AI (Zhipu) | `ZAI_API_KEY` | 3 | 1 concurrent request per model | de verificat |
| Aion Labs | `AIONLABS_API_KEY` | 4 | 20K tokens/day | de verificat |
| Gonka Broker | `GONKA_API_KEY` | 3 | ~1M tokens/MONTH shared; lower rate on free funds (maxRpm from /test-auth) | ok |
| LLM7.io | `LLM7_API_KEY (opțional; merge și fără)` | 3 | Free token: 1 RPS, 60 RPM, 250 req/hour, 100K tokens/24h; may be reduced without notice | ok |
| Kilo Code gateway | `KILO_API_KEY (opțional; merge și fără)` | 9 | 200 requests/hour per IP for free models | ok |
| OVHcloud AI Endpoints | `niciuna (cu cheie devine plătit; lanțul nu trimite cheie)` | 9 | Anonymous: 2 RPM per IP per model. With a key: 400 RPM but billed pay-as-you-go | ok |
| ModelScope | `MODELSCOPE_API_KEY` | 2 | 2,000 RPD total, <=500 RPD per model (dynamic) | de verificat |
| SiliconFlow | `SILICONFLOW_API_KEY` | 2 | not published | de verificat |

„De verificat” înseamnă că sursa nu confirmă tot: compatibilitatea OpenAI la Z AI și Aion Labs, iar ModelScope și SiliconFlow se pot testa doar din China. Toți intră în lanț când au cheie, iar `check` arată dacă răspund.

**Confidențialitate:**
- Modelele gratuite de la OpenRouter și Kilo, precum și NVIDIA, pot păstra cererile.
- Gemini gratuit le poate folosi pentru antrenare (în afara SEE).
- Termenii Google cer servicii plătite pentru o aplicație folosită de oameni din SEE.

Aplicația trimite doar date demo și textul ideilor. Jurnalele conțin doar furnizorul, modelul, rezultatul și durata, niciodată conținutul sau cheile.

### Cum funcționează lanțul (`chain.py`)
- **Ordinea:**
  1. `LLM_CHAIN` (dacă e setat);
  2. altfel `chain_order.json` (scris de `bench`), filtrat după `LLM_MIN_PASS_RATE`;
  3. altfel ordinea din registru, fără modelele pe care ultimul `check` le-a găsit căzute.
- **Cine intră:** doar furnizorii activi, adică cei cu cheie, plus cei fără cheie doar când `LLM_ALLOW_KEYLESS=true` (implicit e oprit).
- **Cache:** întâi se caută un răspuns salvat (`backend/ai/llm/cache/`, ignorat de git).
- **Trecerea la modelul următor:**
  - 429: furnizorul e sărit până trece `Retry-After`, altfel 60 s;
  - 5xx, timeout, eroare de rețea;
  - JSON invalid sau respins de validator după o reîncercare pe același model (de exemplu, un dosar care conține sume de bani).
- **401/403:** furnizorul e dezactivat până la repornire, cu un mesaj clar în jurnal.
- **Limite:**
  - `LLM_TOTAL_BUDGET_S` de timp total pe cerere și `LLM_MAX_ATTEMPTS` încercări;
  - un model căzut e sărit `LLM_COOLDOWN_S` (5 minute);
  - limita pe minut (RPM) a fiecărui furnizor, din registru.

  Când nimic nu merge, se ridică `LLMUnavailable`, iar apelantul folosește fallback-ul.
- **În teste** lanțul e oprit (sub pytest, sau cu `LLM_ENABLED=false`), deci nicio suită nu apelează furnizori reali.

### Variabile de mediu (de adăugat de P1 în `.env.example`)
| Variabilă | Implicit | Rol |
|---|---|---|
| `GROQ_API_KEY`, `OPENROUTER_API_KEY`, `COHERE_API_KEY`, `NVIDIA_API_KEY`, `CLOUDFLARE_API_KEY`, `CLOUDFLARE_ACCOUNT_ID`, `ZAI_API_KEY`, `AIONLABS_API_KEY`, `GONKA_API_KEY`, `LLM7_API_KEY`, `KILO_API_KEY`, `MODELSCOPE_API_KEY`, `SILICONFLOW_API_KEY` | gol | cheile furnizorilor (`GEMINI_API_KEY` există deja) |
| `LLM_ENABLED` | activ, în afara testelor | `false` oprește lanțul și folosește doar fallback-ul |
| `LLM_CHAIN` | gol | ordine forțată, ex. `groq:openai/gpt-oss-120b,gemini:gemini-3.5-flash-lite` |
| `LLM_TIMEOUT_S` | 15 | timp maxim pe cerere |
| `LLM_TOTAL_BUDGET_S` | 20 | timp total pe apel, cu toate încercările |
| `LLM_MAX_ATTEMPTS` | 4 | încercări pe apel |
| `LLM_MIN_PASS_RATE` | 0.7 | pragul din bench; 0 = toate modelele care răspund |
| `LLM_ALLOW_KEYLESS` | false | `true` adaugă LLM7, Kilo și OVH, care merg fără cheie (implicit oprit: o instalare nouă apelează doar furnizorii cu cheie în `.env`) |
| `LLM_CACHE` | true | cache pe disc pentru răspunsuri |
| `LLM_COOLDOWN_S` | 300 | pauza pentru un model căzut |

### Comenzi
```
python -m backend.ai.llm.check                 # cine răspunde acum -> models_live.json (ignorat de git)
python -m backend.ai.llm.bench --max-models 3  # scor pe modele -> chain_order.json (comis); --write-docs actualizează tabelul de mai jos
python -m backend.ai.llm.pregenerate           # umple cache-ul pentru demo (ideile, mesajele și dosarul demo)
python -m backend.ai.llm.sync_registry         # doar pentru dezvoltare: diferențele față de lista online, nu modifică nimic
```

### Bench
- **Ce testează:** 10 idei etichetate din `eval_ideas.json` (promptul lui `structure_idea`) și 3 cazuri `owner_message`.
- **Ce măsoară:**
  - JSON valid (`pass_rate`);
  - acuratețea față de etichete (categorie, participanți, interior/exterior);
  - limba română: diacritice, fără cuvinte englezești, lungime rezonabilă;
  - latența mediană.
- **Scorul:** `100 × (0.35 JSON + 0.35 acuratețe + 0.15 română + 0.15 viteză)`.
- **Ritmul:** respectă RPM-ul și nu planifică mai mult de 80% din cota zilnică (RPD). La OVH lasă 31 s între cererile către același model.
- **Ordinea și pragul** se schimbă fără un bench nou: `LLM_MIN_PASS_RATE` se aplică la încărcare, iar `LLM_CHAIN` are prioritate.


## Specificație, fezabilitate, prețuri cu sursă, documente (15.11, mod solo)
- `backend/ai/proiect/spec/`: `Specificatie` (Pydantic, strict) e sursa unică pentru plan, materiale, dosar, planșe și 3D.
  Modele scrise de mână (`modele.py`) pentru 10 tipuri: skatepark, loc de joacă, parc câini, pistă biciclete, grădină comunitară,
  teren sport, foișor, **stație de încărcare EV**, **fântână publică**, **parc acvatic**. Orice alt tip: LLM cu schemă strictă
  (fără prețuri, mărimi plafonate, validare), altfel specificație generică marcată ca atare. Toate dimensiunile sunt ipoteze
  schematice declarate, nu standarde.
- `fezabilitate.py`: reguli deterministe (suprafață minimă/recomandată, componente obligatorii care nu încap, utilități
  necunoscute → „de verificat”, sursa terenului). Nivel `nerealist` explică și recomandă; nimic nu e respins tăcut.
- `acte.py`: documentele publice uzuale pe tip de lucrare (Legea 50/1991 art. 3, 6, 7, 11; avize operatori, DSP, APM, ISU,
  circulație, cultură), cu emitent și temei; toate „de confirmat” prin certificatul de urbanism; două cereri-tip precompletate.
  Lista are nevoie de verificare umană înainte de o utilizare reală.
- `preturi_surse.py`: ordinea surselor de preț: SEAP (≥ 3 observații) → `data/plafoane.json` (plafoane de program oficiale,
  afișate ca plafon; acum: ghidul AFM stații de reîncărcare, Ordin 1962/2021, plafon per beneficiar) → `data/preturi_catalog.json`
  (prețuri de catalog verificate în pagină de un script offline; gol la 15.11: magazinele au refuzat accesul automat). Fără
  sursă → „de cotat” cu motiv. Nicio cifră inventată.
- `costs.py`: costul e mereu prezent: intervalul din referințe (când există ≥ 2) + suma articolelor cotate + lista celor necotate.
- `memoriu.py`: memoriu descriptiv pe 9 capitole (LLM în schemă strictă fără sume, șablon determinist altfel).
- `documente/plansa.py`: planșe A3 (plan de situație + detaliu cu elevație): cartuș fără semnătură/ștampilă, nord, scară numerică
  și grafică, axe, hașuri, legendă, bilanț teritorial, POT/CUT propuse (orientative). `documente/xlsx.py`: OOXML scris direct.
- Comunitate: `Vot` (unic per utilizator și proiect), `prag_voturi` implicit 3, trimitere automată la Primărie la prag.
