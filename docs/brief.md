# Brief detaliat (componente, echipă, plan)

## Componente
1. Ingestie: colectori per sursă, OCR pentru PDF-uri scanate, deduplicare
2. Extracție LLM -> JSON: tip, ce, locație (stradă, număr, stație, linie), început, sfârșit estimat, încredere 0-1, sursă (URL), necitit. Se abține când nu e sigur
3. Geocodare OSM: diacritice, abrevieri, intervale de numere -> clădiri sau zone
4. Motor transport: GTFS static + alerte + vehicule live -> serviciu efectiv per stație, stații fantomă, alternative sub ~300 m
5. Abonări pe adresă / linie / stație -> alerte (web push sau bot Telegram, simulat ca notificare City App)
6. UI mobil-first (PWA): hartă, "ce s-a schimbat lângă mine", pagina stației, badge de încredere, cronologia anunțului
7. Integrare City App: API REST (OpenAPI), widget embeddable, endpoint-tool pentru Timi, machetă tab nou
8. Evaluare: 30 de anunțuri reale etichetate manual, acuratețea în pitch
9. Dacă rămâne timp: buton "Mi-a revenit căldura", alerte în engleză, mod asociație

## Echipă (contract JSON fixat în ora 0-1; UI pe mock de la ora 1)
- Persoana 1, Raul (backend/ML): ingestie, OCR, extracție, geocodare, API
- Persoana 2 (front-end/UX): PWA, hartă, abonări, notificări, machetă City App
- Persoana 3 (date/transport/prezentare): motor GTFS+live, set de evaluare, pitch, video de rezervă
- Sync la 12, 24 și 36 de ore; fiecare scrie 2 slide-uri din pitch

## Plan
Ore 0-1 contract și repo | 1-6 ingestie și extracție | 6-20 hartă, abonări, motor transport | 20-34 integrare, evaluare, City App | 34-42 polish | 42-48 pitch, repetiții, video de rezervă. Freeze de cod la ora 42

## Demo (3 minute)
10 anunțuri reale -> JSON -> hartă -> abonare pe o clădire -> alertă -> stație fantomă live

## Surse de anunțuri
STPT (alerte + comunicate), Colterm (comunicate, Facebook), Rețele Electrice Banat (întreruperi planificate PDF), Aquatim (de identificat), Primăria (restricții, lucrări)

## Plan B (dacă testul de 30 de minute pică)
Auditor de accesibilitate civică: axe-core/Lighthouse pe site-uri de instituții, raport în română simplă

## Nu face
Aplicație cu ETA, agregator de evenimente, reporter de incidente, chatbot-wrapper; nu inventa date; nu cere hardware sau API intern City App