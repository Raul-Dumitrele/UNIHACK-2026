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
