"""Prepare the demo scenarios through the API of a running backend (idempotent: existing cases are skipped).

    sh scripts/seed.sh && sh scripts/dev.sh          # terminal 1
    backend/.venv/bin/python scripts/demo_cases.py   # terminal 2 (default API: http://localhost:8000)

Three cases for the presentation, plus three that only show the other states:
  1. loc de joacă on an OpenStreetMap candidate plot, published, one supporter  -> the positive case
  2. skatepark: published, 3 supporters -> sent automatically -> forwarded -> agreement in principle (simulated)
  3. parc acvatic: unrealistic on the plot, total cost cannot be estimated      -> the app says what it does not know
  4-6. a draft, a project with clarifications asked, a rejected one
Nothing is written to the database directly: every step is a real API call, as a demo user would make it.
"""
import sys

import httpx

API = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
PRIMARIE, VERIFICATOR = "demo-user-9", "demo-user-10"

# (author, kind as typed, district of the plot, description, script)
CASES = [
    ("demo-user-1", "loc de joacă", "Mehala", "Un loc de joacă pentru copiii de la blocuri, cu leagăne, tobogan și bănci pentru părinți.",
     ["publica", ("vot", "demo-user-2")]),
    ("demo-user-2", "skatepark", "Tipografilor", "Un skatepark mic pentru adolescenții din cartier, cu rampe și bănci.",
     ["publica", ("vot", "demo-user-1"), ("vot", "demo-user-3"), ("vot", "demo-user-4"), "inainteaza",
      ("decizie", "acord_de_principiu", "Propunerea este în regulă pentru etapa următoare.")]),
    ("demo-user-3", "parc acvatic", "Bucovina", "Un parc acvatic cu piscine și tobogane pentru familiile din Timișoara.", ["publica"]),
    ("demo-user-1", "teren de sport", "Torontalului", "Un teren de sport în aer liber pentru tinerii din zonă, deschis seara.", []),
    ("demo-user-4", "grădină comunitară", "Dorobanților", "O grădină comunitară cu rame de plantare pentru locatarii blocurilor din jur.",
     ["trimite", "inainteaza", ("decizie", "clarificari", "Precizați cine întreține grădina după deschidere.")]),
    ("demo-user-5", "pistă de biciclete", "Cartierul Vienez", "O pistă pentru biciclete, pentru copii și începători.",
     ["trimite", "inainteaza", ("decizie", "respins", "Terenul este rezervat altei investiții.")]),
]


def create(api: str = API) -> list[str]:
    """Runs the cases; returns the ids of the projects (existing or new), in the order of CASES."""
    client = httpx.Client(base_url=api, timeout=180)

    def call(method: str, path: str, user: str, **kw):
        r = client.request(method, path, headers={"X-User-Id": user}, **kw)
        r.raise_for_status()
        return r.json()

    plots = call("GET", "/spaces?tip=teren_liber", "demo-user-1")
    ids = []
    for author, tip, cartier, text, steps in CASES:
        plot = next(s for s in plots if s.get("sursa") == "osm" and s.get("cartier") == cartier)
        mine = call("GET", "/proiecte", author)
        existing = next((p for p in mine if p["space_id"] == plot["id"]), None)
        if existing:
            ids.append(existing["id"])
            continue
        pid = call("POST", "/proiecte", author, json={"space_id": plot["id"], "tip_amenajare": tip, "descriere": text})["id"]
        for step in steps:
            if step == "publica":
                call("POST", f"/proiecte/{pid}/publica", author)
            elif step == "trimite":
                call("POST", f"/proiecte/{pid}/trimite", author, json={"mesaj": None})
            elif step == "inainteaza":
                call("POST", f"/proiecte/{pid}/inainteaza", PRIMARIE, json={"verificator_id": VERIFICATOR})
            elif step[0] == "vot":
                call("POST", f"/proiecte/{pid}/vot", step[1])
            elif step[0] == "decizie":
                call("POST", f"/proiecte/{pid}/decizie", VERIFICATOR, json={"stare": step[1], "mesaj": step[2]})
        ids.append(pid)
    return ids


if __name__ == "__main__":
    for pid, case in zip(create(), CASES):
        print(f"{case[1]:20} {pid}")
