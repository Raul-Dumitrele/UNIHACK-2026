# Contract API - Loc Comun

Sursa unică de adevăr între backend (P1), web/mobil (P2) și AI/seed/impact (P3).
Orice schimbare se agreează în echipă; după schimbare: `make openapi` (sau `backend/.venv/Scripts/python scripts/export_openapi.py`) și regenerați tipurile TS din `docs/openapi.json`.

> STARE: schelet. Elementele marcate **TBD** trebuie fixate de echipă înainte de implementare.

## Convenții
- JSON, câmpuri `snake_case`, date ISO 8601 (UTC).
- Utilizator demo: header `X-User-Id` (selector de utilizator demo în UI). Fără autentificare reală.
- Elementele de demonstrație au `is_demo: true` și se afișează cu insigna „exemplu”.
- Erori: TBD (propunere: `{"detail": "<mesaj>"}`, formatul implicit FastAPI).

## Flux
idee -> dosar structurat de AI -> spații potrivite -> interes din comunitate -> aprobare rezervare de către proprietar -> tablou de impact

## Entități
| Entitate | Câmpuri | Stare |
|---|---|---|
| User | TBD | TBD |
| Idea | TBD (conține dosarul structurat de AI) | TBD |
| Space | TBD, inclusiv `is_demo` | TBD |
| Interest | TBD (un singur interes per utilizator per idee) | TBD |
| Booking | TBD | TBD |
| Notification | TBD (în aplicație, la schimbarea stării ideii/rezervării) | TBD |
| Impact | TBD | TBD |

## Enum-uri
| Enum | Valori |
|---|---|
| IdeaStatus | TBD (include `prag_atins`) |
| BookingStatus | TBD (cerută / aprobată / refuzată - de confirmat) |

## Endpointuri
| Metodă | Rută | Zonă | Descriere |
|---|---|---|---|
| GET | /health | P1 | verificare pornire (implementat) |
| POST | /ideas | P1 | creează idee; apelează `ai.structure_idea` (fallback fără Gemini) |
| GET | /ideas/{id}/matches | P1 + P3 | spații potrivite, cu scor și motiv în text |
| POST | /ideas/{id}/interest | P1 | un interes per utilizator; trece ideea la `prag_atins` la prag |
| POST | /bookings | P1 | cerere de rezervare pe un slot |
| PATCH | /bookings/{id} | P1 | doar proprietarul spațiului aprobă/refuză; slotul ocupat dispare |
| GET | /impact | P1 + P3 | rezultatul `impact.compute_impact` |

## Funcții între module (P3 -> P1)
- `backend.ai.structure_idea(text) -> <model Pydantic TBD>`: validare Pydantic, fallback determinist fără Gemini.
- `backend.impact.compute_impact(...) -> <TBD>`
- Formula de scor pentru potrivire: în backend, TBD.

## Variabile de mediu
`DATABASE_URL`, `GEMINI_API_KEY`, `CORS_ORIGINS`, `VITE_API_URL`, `EXPO_PUBLIC_API_URL` (vezi `.env.example`).
