# Contract API - Loc Comun

Sursa unică de adevăr între backend (P1), web/mobil (P2) și AI/seed/impact (P3).
Orice schimbare se agreează în echipă; după schimbare: `make openapi` (sau `backend/.venv/Scripts/python scripts/export_openapi.py`) și regenerați tipurile TS din `docs/openapi.json`.

## Convenții
- JSON, câmpuri `snake_case`, date ISO 8601 (UTC, sufix `Z`).
- Id-uri: string. În seed sunt stabile (`osm-<id>`, `demo-user-1`); pentru obiecte noi, UUID.
- Utilizator demo: header `X-User-Id` (selector de utilizator demo în UI). Fără autentificare reală.
- Elementele de demonstrație au `is_demo: true` și se afișează cu insigna „exemplu”.
- Erori: `{"detail": "<mesaj în română>"}`; coduri 400, 401 (`X-User-Id` lipsă sau necunoscut, unde e necesar), 403, 404, 409, 422.
- Notificările sunt doar în aplicație (stare idee/rezervare), nu alerte despre oraș.

## Flux
idee -> dosar structurat de AI -> spații potrivite -> interes din comunitate -> aprobare rezervare de către proprietar -> tablou de impact

## Vocabulare
| Nume | Valori |
|---|---|
| zi | luni, marti, miercuri, joi, vineri, sambata, duminica |
| categorie | sport, cultura, educatie, social, creativ, tehnologie, altele |
| zgomot | scazut, mediu, ridicat |
| dotari | scaune, mese, proiector, wifi, scena, oglinzi, vestiare, bucatarie, acces_rampa, curte, priza, tabla |
| tip_amenajare | skatepark, loc_de_joaca, parc_caini, pista_biciclete, gradina_comunitara, teren_sport |

`Slot` = `{zi, de_la: "HH:MM", pana_la: "HH:MM"}` (`de_la` < `pana_la`, aceeași zi).

## Enum-uri
| Enum | Valori |
|---|---|
| IdeaStatus | deschisa, prag_atins, rezervata |
| BookingStatus | cerut, aprobat, refuzat |
| UserRole | cetatean, proprietar, primarie, verificator |
| ProiectStare | draft, trimis, in_verificare, clarificari, acord_de_principiu, respins |

## Entități
| Entitate | Câmpuri |
|---|---|
| User | id, nume, rol (UserRole), cartier, lat, lng |
| Space | id, nume, tip (text liber; include `teren_liber`), lat, lng, capacitate, dotari[], sloturi[Slot], owner_id, is_demo, suprafata_mp? (int) |
| Idea | id, author_id, titlu, descriere, structurat (Structurat), prag (implicit 5), interesati, stare (IdeaStatus), is_demo, created_at |
| Structurat | categorie, persoane, dotari[], program[Slot], zgomot, rezumat |
| Interest | id, user_id, idea_id, created_at; unic pe (user_id, idea_id) |
| Booking | id, idea_id, space_id, slot, stare (BookingStatus), created_at, mesaj? (text) |
| Notification | id, user_id, idea_id, booking_id?, proiect_id?, mesaj, citita, created_at |
| Match | space (Space), scor (0-100), motiv, suprapunere[Slot] |
| Impact | ore_recuperate, oameni_conectati, km_economisiti (estimare), proiecte_active, proiecte_trimise, proiecte_cu_acord |
| Referinta | id, tip_amenajare, oras, an, suprafata_mp?, cost_total_lei?, componente[], sursa_url, sursa_tip, data_accesarii |
| Cost | suficient (bool), min_lei?, mediana_lei?, max_lei?, moneda ("RON"), ipoteze[], referinte_folosite[], motiv? |
| Etapa | nume, durata_luni |
| Dosar | titlu, descriere, justificare, componente[], etape[Etapa], riscuri[], lista_verificare[], referinte_citate[] |
| Proiect | id, idea_id, space_id, autor_id, tip_amenajare, suprafata_mp, stare (ProiectStare), dosar (Dosar), referinte[Referinta], cost (Cost), created_at, updated_at, verificator_id? (**adaugat de P1**, vezi nota) |
| ProiectEveniment | id, proiect_id, user_id, stare_noua, mesaj?, created_at |

Nota: `Proiect.verificator_id` (opțional) nu era în lista inițială; e necesar ca să știm cine e desemnat (`GET /proiecte` pentru verificator, `decizie`). Se setează la `inainteaza`.

## Endpointuri
Autentificat = necesită `X-User-Id` valid (altfel 401).

| Metodă | Rută | Cerere | Răspuns | Note |
|---|---|---|---|---|
| GET | /health | - | `{status}` | |
| GET | /users | - | User[] | pentru selectorul demo |
| GET | /spaces | filtre: `categorie`, `dotari` (repetat), `capacitate_min` | Space[] | |
| POST | /ideas | `{descriere, titlu?, prag?}` | Idea (201) | autentificat; vezi regula 1 |
| GET | /ideas | - | Idea[] | |
| GET | /ideas/{id} | - | Idea | 404 dacă nu există |
| GET | /ideas/{id}/matches | - | Match[] | sortat descrescător după scor |
| POST | /ideas/{id}/interest | - | Idea (201) | autentificat; 409 la duplicat |
| POST | /ideas/{id}/owner-message | `{space_id, slot}` | `{mesaj}` | autentificat; text generat de `ai.owner_message` |
| POST | /bookings | `{idea_id, space_id, slot, mesaj?}` | Booking (201) | autentificat; regula 3 |
| PATCH | /bookings/{id} | `{stare: aprobat\|refuzat}` | Booking | autentificat; regula 4 |
| GET | /notifications | - | Notification[] | autentificat; ale utilizatorului curent |
| PATCH | /notifications/{id}/read | - | Notification | autentificat; doar a utilizatorului |
| GET | /impact | - | Impact | rezultatul `impact.compute_impact` |
| POST | /ideas/{id}/proiect | `{space_id, tip_amenajare, suprafata_mp?}` | Proiect draft (201) | autentificat; regula 6 |
| GET | /proiecte | - | Proiect[] | autentificat; filtrat după rol (regula 7) |
| GET | /proiecte/{id} | - | Proiect + `evenimente[]` | autentificat |
| POST | /proiecte/{id}/trimite | `{mesaj?}` | Proiect | autentificat; autor; regula 8 |
| POST | /proiecte/{id}/inainteaza | `{verificator_id}` | Proiect | autentificat; primarie; regula 8 |
| POST | /proiecte/{id}/decizie | `{stare: acord_de_principiu\|respins\|clarificari, mesaj}` | Proiect | autentificat; verificator desemnat; regula 8 |

## Reguli
1. **Idee.** `POST /ideas` apelează `ai.structure_idea(descriere)`; `titlu` implicit = `structurat.rezumat` (max 80 caractere); `stare = deschisa`; `prag` implicit 5.
2. **Interes.** Un interes per utilizator per idee (409 la duplicat). La `interesati >= prag` și `stare = deschisa` -> `prag_atins` și notificare către autor.
3. **Rezervare (cerere).** Doar autorul ideii (403), doar când `idea.stare = prag_atins` (409), slotul trebuie conținut într-un slot din `Space.sloturi` (409). Notificare către proprietarul spațiului. Stare inițială `cerut`.
4. **Rezervare (decizie).** Doar proprietarul spațiului (403). La `aprobat`: ideea devine `rezervata`, slotul se scoate din `Space.sloturi` (cu împărțire dacă rămân intervale), cererile suprapuse în așteptare devin `refuzat`, notificare către autor. La `refuzat`: notificare către autor. O cerere deja decisă nu se mai schimbă (409).
5. **Potrivire** (în `backend/app`, haversine, fără PostGIS): `scor = 30% capacitate + 30% suprapunere + 20% dotari + 20% distanta`, rezultat 0-100.
   - capacitate = `min(1, capacitate_spatiu / persoane)`
   - suprapunere = minute comune între `structurat.program` și `Space.sloturi` / minute cerute (plafon 1)
   - dotari = fracția dotărilor cerute prezente în spațiu
   - distanță = `max(0, 1 - km_medii / 5)`, km medii față de utilizatorii interesați (dacă nu există, față de autor)
   - `motiv` în română, ex. „40 locuri, liber sâmbătă 10-14, la 600 m de 8 interesați”.

6. **Proiect (creare).** `POST /ideas/{id}/proiect`: doar autorul ideii (403); `idea.stare` în {`prag_atins`, `rezervata`}, altfel 409; suprafața din cerere sau din `Space.suprafata_mp`, altfel 422. Lanț: `find_references` -> `estimate_cost` -> `generate_dosar`. Stare `draft`.
7. **Proiect (listare).** `GET /proiecte`: autor -> ale lui; `primarie` -> toate cu stare != `draft`; `verificator` -> cele pe care e desemnat.
8. **Proiect (tranziții).** Fiecare tranziție scrie un `ProiectEveniment`; rol greșit -> 403, stare greșită -> 409.
   - `trimite`: autor; din `draft` sau `clarificari` -> `trimis`; notificare către toți utilizatorii `primarie`.
   - `inainteaza`: `primarie`; din `trimis` -> `in_verificare`; setează `verificator_id` (utilizator cu rol `verificator`); notificare către verificator.
   - `decizie`: doar verificatorul desemnat; din `in_verificare` -> `acord_de_principiu` | `respins` | `clarificari`; `mesaj` obligatoriu la `respins` și `clarificari` (422); notificare către autor și primarie.
9. **Booking.mesaj** se salvează la `POST /bookings` (preluat din `owner-message` dacă e trimis).
10. **Text obligatoriu** în dosar și în UI: „Estimare orientativă, bazată pe proiecte de referință. Nu reprezintă o autorizație; acordul din aplicație este un acord de principiu simulat.”

## Funcții între module (P3 -> P1)
- `backend.ai.structure_idea(text: str) -> Structurat` (validare Pydantic, fallback determinist fără Gemini)
- `backend.ai.owner_message(idea, space, slot) -> str`
- `backend.impact.compute_impact(session) -> Impact`
- `python -m backend.seed.run` (idempotent; folosește doar câmpurile din contract)
- `tests/e2e/run.ps1`
- `backend.ai.references.find_references(tip_amenajare, suprafata_mp, k=5) -> list[Referinta]`
- `backend.ai.costs.estimate_cost(referinte, suprafata_mp) -> Cost` (determinist, în cod; `suficient=false` dacă sunt mai puțin de 2 referințe cu suprafață și cost)
- `backend.ai.proiect.generate_dosar(idea, space, tip_amenajare, suprafata_mp, referinte, cost) -> Dosar`
- `compute_impact` extins cu `proiecte_trimise` și `proiecte_cu_acord`
- Seed: utilizatori demo `primarie` și `verificator` și un Space `teren_liber` cu `suprafata_mp`, toate `is_demo=true`.

`Structurat` și `Impact` sunt definite în `backend/app/schemas.py` (P1). Până apar modulele reale, P1 oferă stub-uri în `backend/app/stubs/`, înlocuite automat la import.

## Variabile de mediu
`DATABASE_URL`, `GEMINI_API_KEY`, `GEMINI_MODEL` (implicit `gemini-flash-latest`), `CORS_ORIGINS`, `VITE_API_URL`, `EXPO_PUBLIC_API_URL` (vezi `.env.example`).
