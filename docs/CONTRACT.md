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
teren liber (hartă, căutare sau marcat de utilizator) -> analiză de fezabilitate -> proiect complet generat dintr-o specificație tehnică (memoriu, cost = interval din referințe + suma articolelor cu preț, planșe A3 SVG/DXF/PDF, vedere 3D, listă de materiale XLSX/CSV cu sursa fiecărui preț, documente și avize necesare, cereri-tip) -> publicat -> vot al comunității (un vot per utilizator per proiect) -> la prag, trimis automat la Primărie -> verificator -> acord de principiu (simulat) / clarificări / respins
Fluxul vechi (idei cu prag de interes, potrivire cu spații existente, rezervări) rămâne în API, dar nu mai e folosit în UI.

## Vocabulare
| Nume | Valori |
|---|---|
| zi | luni, marti, miercuri, joi, vineri, sambata, duminica |
| categorie | sport, cultura, educatie, social, creativ, tehnologie, altele |
| zgomot | scazut, mediu, ridicat |
| dotari | scaune, mese, proiector, wifi, scena, oglinzi, vestiare, bucatarie, acces_rampa, curte, priza, tabla |
| tip_amenajare | **text liber** (2–80 caractere); sugestii: skatepark, loc_de_joaca, parc_caini, pista_biciclete, gradina_comunitara, teren_sport |

`Slot` = `{zi, de_la: "HH:MM", pana_la: "HH:MM"}` (`de_la` < `pana_la`, aceeași zi).

## Enum-uri
| Enum | Valori |
|---|---|
| IdeaStatus | deschisa, prag_atins, rezervata |
| BookingStatus | cerut, aprobat, refuzat |
| UserRole | cetatean, proprietar, primarie, verificator |
| ProiectStare | draft, publicat, trimis, in_verificare, clarificari, acord_de_principiu, respins |

## Entități
| Entitate | Câmpuri |
|---|---|
| User | id, nume, rol (UserRole), cartier, lat, lng |
| Space | id, nume, tip (text liber; include `teren_liber`), lat, lng, capacitate, dotari[], sloturi[Slot], owner_id, is_demo, suprafata_mp? (int), cartier? (text), sursa? (text, ex. `lista_primarie`), sursa_detalii? (text), status_verificare? (text, ex. `neverificat`), descriere? (text) |
| Idea | id, author_id, titlu, descriere, structurat (Structurat), prag (implicit 5), interesati, stare (IdeaStatus), is_demo, created_at |
| Structurat | categorie, persoane, dotari[], program[Slot], zgomot, rezumat |
| Interest | id, user_id, idea_id, created_at; unic pe (user_id, idea_id) |
| Booking | id, idea_id, space_id, slot, stare (BookingStatus), created_at, mesaj? (text) |
| Notification | id, user_id, idea_id, booking_id?, proiect_id?, mesaj, citita, created_at |
| Match | space (Space), scor (0-100), motiv, suprapunere[Slot] |
| Impact | ore_recuperate, oameni_conectati, km_economisiti (estimare), proiecte_active, proiecte_trimise, proiecte_cu_acord, proiecte_propuse, proiecte_publicate, proiecte_peste_prag, voturi_total, oameni_implicati, terenuri_libere |
| Referinta | id, tip_amenajare, oras, an, suprafata_mp?, cost_total_lei?, componente[], sursa_url, sursa_tip, data_accesarii |
| Cost | suficient (bool: există intervalul din referințe), min_lei?, mediana_lei?, max_lei?, moneda ("RON"), ipoteze[], referinte_folosite[], motiv?, **suma_cotata_lei?** (suma articolelor cu preț din lista de materiale), articole_cotate, articole_necotate[], pe_surse{tip_sursa: n}, eticheta_suma, metoda, **titlu** (titlul blocului de cost: „Cost estimat din proiecte de referință” sau „Cost total: nu poate fi estimat din datele disponibile”), **lipsesc_principale** (bool), **nota_suma?** („Suma nu include elementele principale ale amenajării.”). Suma parțială nu e niciodată cifra principală și nu se numește „cost”. Costul e MEREU prezent: intervalul când există ≥ 2 referințe, suma cotată de câte ori există o listă de materiale |
| Etapa | nume, durata_luni |
| Dosar | titlu, descriere, justificare, componente[], etape[Etapa], riscuri[], lista_verificare[], referinte_citate[], memoriu{date_generale, situatia_existenta, solutia_propusa, specificatii_tehnice, utilitati_energie, accesibilitate, intretinere, impact_comunitate, documente_necesare}, acte[Act], acte_disclaimer, cereri_tip[CerereTip] |
| Proiect | id, idea_id, space_id, autor_id, tip_amenajare, suprafata_mp, stare (ProiectStare), dosar (Dosar), referinte[Referinta], cost (Cost), created_at, updated_at, verificator_id? (**adaugat de P1**, vezi nota), is_demo (bool, implicit false; **adaugat de P1**), voturi (int), prag_voturi (int, implicit 3), specificatie? (Specificatie, JSON), fezabilitate? (Fezabilitate, JSON) |
| ProiectEveniment | id, proiect_id, user_id, stare_noua, mesaj?, created_at |
| Vot | id, proiect_id, user_id, created_at; unic pe (user_id, proiect_id) |
| Specificatie | tip_amenajare, eticheta, suprafata_minima_mp, suprafata_recomandata_mp?, utilitati_necesare[], categorie_lucrare[], componente[{nume, categorie, cantitate, unitate, latime_m?, lungime_m?, inaltime_m?, zona_libera_m, rol, obligatoriu, pe_plan, tip_desen, utilitati[], articol?, derivat_din}], beneficii[], riscuri_specifice[], ipoteze[], surse[], sursa_specificatie (model_verificat\|llm\|generic), disclaimer (`backend/ai/proiect/spec/model.py`) |
| Fezabilitate | nivel (ok\|atentie\|nerealist), scor (0-100, orientativ), rezumat, motive[], recomandari[], beneficii[], utilitati[{nume, stare, detaliu}], suprafata_mp?, suprafata_minima_mp, suprafata_recomandata_mp?, teren{}, disclaimer, **interpretare** („Am interpretat propunerea ca: <eticheta>”), **interpretare_diferita** (bool: eticheta diferă de ce a scris utilizatorul; UI cere confirmare). `nerealist` și când terenul e sub minim sau sub 50% din suprafața recomandată; specificația generică dă cel mult `atentie`, cu primul motiv „Propunerea e prea generală…” |
| Act | ordine, nume, emitent, descriere, temei, conditie?, de_confirmat, **grup** (uzual \| dupa_caz; cele „după caz” sunt ultimele), **url?** (doar pagini legislatie.just.ro deschise la scrierea rândului) |
| CerereTip | titlu, catre, text |

Nota: `Proiect.verificator_id` (opțional) nu era în lista inițială; e necesar ca să știm cine e desemnat (`GET /proiecte` pentru verificator, `decizie`). Se setează la `inainteaza`.

## Endpointuri
Autentificat = necesită `X-User-Id` valid (altfel 401).

| Metodă | Rută | Cerere | Răspuns | Note |
|---|---|---|---|---|
| GET | /health | - | `{status}` | |
| GET | /users | - | User[] | pentru selectorul demo |
| GET | /spaces | filtre: `tip` (ex. `teren_liber`), `categorie`, `dotari` (repetat), `capacitate_min` | Space[] | |
| POST | /spaces | `{nume, lat, lng, suprafata_mp, descriere?}` | Space (201) | autentificat; teren liber marcat pe hartă; regula 14 |
| GET | /spaces/{id}/proiecte | - | Proiect[] | public; proiectele trimise (≠ draft) pe teren + ciornele proprii (dacă e trimis `X-User-Id`) |
| POST | /ideas | `{descriere, titlu?, prag?}` | Idea (201) | autentificat; vezi regula 1 |
| GET | /ideas | - | Idea[] | |
| GET | /ideas/{id} | - | Idea | 404 dacă nu există |
| GET | /ideas/{id}/matches | - | Match[] | sortat descrescător după scor |
| POST | /ideas/{id}/interest | - | Idea (201) | autentificat; 409 la duplicat |
| POST | /ideas/{id}/owner-message | `{space_id, slot}` | `{mesaj}` | autentificat; text generat de `ai.owner_message` |
| GET | /bookings | - | Booking[] | autentificat; cererile utilizatorului (ca autor al ideii) plus cele pentru spațiile lui (ca proprietar); cele mai noi primele |
| POST | /bookings | `{idea_id, space_id, slot, mesaj?}` | Booking (201) | autentificat; regula 3 |
| PATCH | /bookings/{id} | `{stare: aprobat\|refuzat}` | Booking | autentificat; regula 4 |
| GET | /notifications | - | Notification[] | autentificat; ale utilizatorului curent |
| PATCH | /notifications/{id}/read | - | Notification | autentificat; doar a utilizatorului |
| GET | /impact | - | Impact | rezultatul `impact.compute_impact` |
| POST | /ideas/{id}/proiect | `{space_id, tip_amenajare, suprafata_mp?}` | Proiect draft (201) | autentificat; regula 6 |
| GET | /proiecte | - | Proiect[] | autentificat; filtrat după rol (regula 7) |
| GET | /proiecte/{id} | - | Proiect + `evenimente[]` + `votat_de_mine` | ciorna doar pentru autor (403 altfel, inclusiv anonim); orice proiect ≠ draft e public |
| POST | /proiecte/{id}/trimite | `{mesaj?}` | Proiect | autentificat; autor; regula 8 |
| POST | /proiecte/{id}/inainteaza | `{verificator_id}` | Proiect | autentificat; primarie; regula 8 |
| POST | /proiecte/{id}/decizie | `{stare: acord_de_principiu\|respins\|clarificari, mesaj}` | Proiect | autentificat; verificator desemnat; regula 8 |
| POST | /proiecte/analiza | `{tip_amenajare, descriere?, suprafata_mp?, space_id?}` | AnalizaOut `{tip_amenajare, eticheta, specificatie, fezabilitate, plan_complet?, omise[]}` | autentificat; rapid, fără dosar; regula 16 |
| GET | /proiecte/publice | - | Proiect[] | public; toate proiectele ≠ draft |
| POST | /proiecte/{id}/publica | - | Proiect | autentificat; autor; draft -> publicat |
| POST | /proiecte/{id}/vot | - | VotOut `{proiect_id, voturi, prag_voturi, stare, votat_de_mine}` (201) | autentificat; 409 la al doilea vot, pe draft sau după decizie; regula 17 |
| GET | /terenuri/potrivite | `tip_amenajare` (obligatoriu), `suprafata_minima?`, `cartier?`, `limit?` (implicit 10) | PlotCandidate[] | terenuri libere potrivite, cel mai bun primul; regula 11 |
| POST | /proiecte | `{space_id, tip_amenajare, descriere, suprafata_mp?}` | Proiect draft + `evenimente[]` (201) | autentificat; proiect direct pe teren, fără idee și fără prag; regula 12 |
| GET | /proiecte/{id}/plan | - | Plan | autentificat; vizibilitate ca la GET /proiecte/{id} |
| GET | /proiecte/{id}/materiale | - | ListaMateriale | autentificat; vizibilitate ca la GET /proiecte/{id} |
| GET | /proiecte/{id}/documente/{nume} | `nume` ∈ plan.svg, plan.dxf, plansa.pdf, dosar.pdf, materiale.xlsx, materiale.csv | fișier | `Content-Disposition: attachment; filename="proiect-<id>-<nume>"`; alt nume -> 404; vizibilitate ca la GET /proiecte/{id} |

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
   - `GET /proiecte/{id}`: vizibil pentru autor, pentru `primarie` (dacă stare != `draft`) și pentru verificatorul desemnat; altfel 403.
9. **Booking.mesaj** se salvează la `POST /bookings` (preluat din `owner-message` dacă e trimis).
10. **Text obligatoriu** în dosar și în UI: „Estimare orientativă, bazată pe proiecte de referință. Nu reprezintă o autorizație; acordul din aplicație este un acord de principiu simulat.”
11. **Terenuri potrivite.** `GET /terenuri/potrivite` apelează `find_plots` (P3) peste spațiile cu `tip = teren_liber`. PlotCandidate: `{space_id, nume, cartier?, suprafata_mp, scor (0-100), motiv, complet, din_lista_primarie, is_demo, distanta_km?, avertisment?}`. Terenurile mai mici decât `suprafata_minima` sunt excluse. Pentru terenurile din lista Primăriei (Legea 15/2003, destinate locuințelor pentru tineri) `avertisment` spune că folosirea pentru o amenajare publică trebuie aprobată de Primărie.
12. **Proiect direct pe teren.** `POST /proiecte` structurează `descriere` (`structure_idea`), creează o idee internă a autorului (stare `prag_atins`, prag 1) și apoi același lanț ca la regula 6. 404 spațiu inexistent, 422 fără suprafață sau `tip_amenajare` necunoscut.
13. **Plan, materiale, documente** (P3, deterministe, fără AI): Plan = `{tip_amenajare, eticheta, suprafata_mp, latime_m, lungime_m, elemente[], omise[], complet, ..., suprafata_ocupata_mp}`; ListaMateriale = `{linii[{articol, nume, unitate, cantitate, ipoteza, pret_unitar{mediana_lei, min_lei, max_lei, observatii, surse[], perioada}?, valoare_lei?, stare: cotat|de_cotat, motiv}], subtotal_cotat_lei, linii_de_cotat, eticheta_subtotal, sursa_preturi, tva, ipoteze[], disclaimer}`. Forma exactă: `docs/openapi.json`. Planul e o schiță orientativă, nu un proiect tehnic.
14. **Teren marcat de utilizator.** `POST /spaces` creează un `Space` cu `tip = teren_liber`, `is_demo = false`, `owner_id` = utilizatorul, `sursa = marcat_de_utilizator`, `status_verificare = neverificat`, `cartier` = cel mai apropiat cartier (dacă se poate calcula). Coordonatele trebuie să fie în zona Timișoarei (lat 45.6–45.9, lng 21.0–21.45), altfel 422. Proprietarul real, regimul juridic și disponibilitatea NU sunt cunoscute; UI-ul le afișează ca „de verificat cu Primăria”.
15. **Ce NU oferă API-ul:** firme reale (dosarul descrie doar documentele și pașii; profilul firmei nu e generat), avize sau autorizații (aplicația nu emite nimic), prețuri inventate (un articol fără sursă rămâne „de cotat”).
16. **Specificație și fezabilitate.** Orice proiect pornește din `Specificatie` (modele scrise de mână pentru skatepark, loc de joacă, parc câini, pistă biciclete, grădină comunitară, teren sport, foișor, stație de încărcare EV, fântână publică, parc acvatic; LLM cu schemă strictă și fără prețuri pentru orice alt tip; generic marcat ca atare dacă niciun model nu răspunde). Planul, materialele, dosarul, planșele și vederea 3D se construiesc din aceeași specificație, stocată pe Proiect. `Fezabilitate` vine din reguli deterministe (suprafață minimă/recomandată, componente care nu încap, utilități de verificat, sursa terenului); nivelul `nerealist` nu respinge tăcut: explică și recomandă.
17. **Comunitate.** `publica`: autor, draft -> publicat (vizibil tuturor). `vot`: un vot per utilizator per proiect (409 la dublură); permis din publicat până la decizie. La `voturi >= prag_voturi` (implicit 3) proiectul trece automat în `trimis`, cu eveniment și notificări către autor și Primărie. `trimite` rămâne pentru trimiterea directă (draft, publicat) și pentru retrimiterea după clarificări. La decizie sunt notificați autorul, Primăria și toți votanții.
18. **Prețuri cu sursă.** Fiecare `PretUnitar` are `tip_sursa` (seap | plafon | catalog), `sursa_url?`, `data_accesarii?`, `nota?`. Ordinea: SEAP (≥ 3 achiziții directe), plafon de program oficial (afișat ca plafon, nu preț), preț de catalog verificat în pagina sursei de scriptul offline. Fără sursă -> `de_cotat` cu motiv. Textul obligatoriu al planșelor: „Schiță orientativă generată de Loc Comun – nu este documentație tehnică (DTAC)”.

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

- `backend.ai.proiect.find_plots(tip_amenajare, suprafata_minima, cartier=None, spaces=None, limit=10) -> list[PlotCandidate]`
- `backend.ai.proiect.documente.plan_json(proiect, space) -> dict`, `materiale_json(proiect, space) -> dict`, `build_documente(proiect, space) -> dict[nume, (bytes, media_type)]`

## Variabile de mediu
`DATABASE_URL`, `GEMINI_API_KEY`, `GEMINI_MODEL` (implicit `gemini-3.5-flash-lite`), `CORS_ORIGINS`, `VITE_API_URL`, `EXPO_PUBLIC_API_URL` (vezi `.env.example`).
