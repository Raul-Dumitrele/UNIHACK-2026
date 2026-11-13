# STPT: endpoint-uri live (nedocumentate, fără cheie API)
Sursă: clientul open-source stpt-mcp 0.3.7. Sunt endpoint-urile site-ului live.stpt.ro, nu un API publicat; pot dispărea sau se pot schimba.
Autentificare: doar header `Referer: https://live.stpt.ro/` (plus un User-Agent propriu). Fără token sau login.

- Sosiri pentru o stație: https://live.stpt.ro/proxy-smtt-cache.php?stopid=<STOP_ID>
- Poziții vehicule: https://live.stpt.ro/gtfs-vehicles.php
- Alerte de serviciu: https://live.stpt.ro/proxy-alerts.php
- Stații, trasee, secvențe (JSON): https://live.stpt.ro/gtfs-data/stops-index.json , route-manifest.json , stop-sequences.json
- GTFS static: https://smtt.ro/transit/gtfs/maps/smtt-timisoara-ro.zip (și în Mobility Database, feed mdb-2868)

Reguli: cache, rate-limit mic, nu republica fluxul brut, păstrează un snapshot în data/.