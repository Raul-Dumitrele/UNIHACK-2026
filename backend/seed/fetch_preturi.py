"""One-off, network: unit-price observations from SEAP direct purchases (data.gov.ro, CC BY 4.0).
    python -m backend.seed.fetch_preturi [--years 2023 2024 2025 2026] [--cache DIR]
Writes backend/ai/proiect/data/preturi_seap.json (committed). The app, the seed and the tests never download.

For every "Achiziții directe" resource of the datasets achizitii-publice-<year> it streams the file (CSV with
| quoting, or XLSX read with the standard library) and keeps only the rows that backend.ai.proiect.preturi.extract
accepts (one article, one explicit quantity in the article's unit). Legacy .xls (BIFF) and .ods files are
skipped and listed in the output. Rows are deduplicated on the DA number; cancelled/rejected rows and rows
without an awarded value are ignored. Raw downloads go to --cache (default: the system temp folder).
"""
import argparse
import csv
import json
import re
import sys
import tempfile
import urllib.request
import zipfile
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from xml.etree.ElementTree import iterparse

from backend.ai.proiect.preturi import ARTICOLE, DATA_FILE, MIN_OBS, SURSA, TVA, extract

CKAN = "https://data.gov.ro/api/3/action/package_show?id=achizitii-publice-{year}"
DATASET_PAGE = "https://data.gov.ro/dataset/achizitii-publice-{year}"
LICENSE = "Creative Commons Attribution 4.0 (CC BY 4.0)"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REJECTED_STATES = re.compile(r"anulat|respins|revocat|neatribuit", re.I)
USER_AGENT = "LocComun-hackathon-data-fetch"


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def resources(year: int) -> list[dict]:
    """Direct-purchase resources of one yearly dataset: {name, url, kind (csv|xlsx|skip)}."""
    pkg = json.loads(_get(CKAN.format(year=year)))["result"]
    out, seen = [], set()
    for r in pkg["resources"]:
        name = (r.get("name") or "").strip()
        low = name.lower()
        if "direct" not in low or "notific" in low or r["url"] in seen:
            continue
        seen.add(r["url"])
        ext = Path(r["url"].split("?")[0]).suffix.lower()  # the CKAN 'format' field is not reliable
        out.append({"name": name, "url": r["url"], "kind": {".csv": "csv", ".xlsx": "xlsx"}.get(ext, "skip"),
                    "year": year})
    return out


def download(url: str, cache: Path) -> Path:
    path = cache / Path(url.split("?")[0]).name
    if not path.exists() or path.stat().st_size == 0:
        tmp = path.with_suffix(path.suffix + ".part")
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=600) as r, open(tmp, "wb") as f:
            while chunk := r.read(1 << 20):
                f.write(chunk)
        tmp.replace(path)
    return path


def _key(header: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", header.strip().upper()).strip("_")


def rows_csv(path: Path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f, delimiter=",", quotechar="|")
        head = [_key(h) for h in next(reader)]
        for row in reader:
            if len(row) == len(head):
                yield dict(zip(head, row))


def _col(ref: str) -> int:
    n = 0
    for ch in re.match(r"[A-Z]+", ref).group():
        n = n * 26 + ord(ch) - 64
    return n - 1


def rows_xlsx(path: Path):
    """Stream the first sheet with the standard library; values as strings (numbers raw, dates as serials).
    The header strings may sit at the end of sharedStrings, so the whole table is loaded first."""
    with zipfile.ZipFile(path) as z:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            for _, el in iterparse(z.open("xl/sharedStrings.xml")):
                if el.tag == f"{NS}si":
                    shared.append("".join(t.text or "" for t in el.iter(f"{NS}t")))
                    el.clear()
        sheet = next(n for n in sorted(z.namelist()) if n.startswith("xl/worksheets/sheet"))
        head = None
        context = iterparse(z.open(sheet), events=("start", "end"))
        _, root = next(context)
        for event, el in context:
            if event != "end" or el.tag != f"{NS}row":
                continue
            values: dict[int, str] = {}
            for c in el.iter(f"{NS}c"):
                t, v = c.get("t"), c.find(f"{NS}v")
                if t == "s" and v is not None:
                    values[_col(c.get("r"))] = shared[int(v.text)]
                elif t == "inlineStr":
                    values[_col(c.get("r"))] = "".join(x.text or "" for x in c.iter(f"{NS}t"))
                elif v is not None:
                    values[_col(c.get("r"))] = v.text or ""
            root.clear()  # keep memory flat on 400 MB sheets
            if head is None:
                head = {i: _key(h) for i, h in values.items()}
                continue
            yield {name: values.get(i, "") for i, name in head.items()}


def _day(raw: str) -> str:
    raw = (raw or "").strip()
    if re.fullmatch(r"\d+(\.\d+)?", raw):  # Excel serial
        return (date(1899, 12, 30) + timedelta(days=float(raw))).isoformat()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(raw[:26], fmt).date().isoformat()
        except ValueError:
            continue
    return raw[:10]


def _value(raw: str) -> float | None:
    raw = (raw or "").strip().replace(" ", "")
    if "," in raw and "." in raw:
        raw = raw.replace(".", "").replace(",", ".")
    elif "," in raw:
        raw = raw.replace(",", ".")
    try:
        return float(raw) if raw else None
    except ValueError:
        return None


# Column names differ between yearly exports (2023 CSV vs 2025 XLSX): first present name wins.
VALUE_COLS = ("VALOARE_ATRIBUITA_RON", "VALOARE_ACHIZITIE_RON")  # 2025+: value of the finalized purchase
DATE_COLS = ("DATA_ATRIBUIRE_ACHIZITIE", "DATA_FINALIZARE", "DATA_PUBLICARE_ACHIZITIE", "DATA_PUBLICARE")
BUYER_COLS = ("DENUMIRE_AC", "AUTORITATE_CONTRACTANTA")


def _first(row: dict, cols: tuple[str, ...]) -> tuple[str, str]:
    for c in cols:
        if row.get(c):
            return c, row[c]
    return "", ""


def observations(rows, states: Counter, used: Counter | None = None) -> list[dict]:
    out = []
    for row in rows:
        state = row.get("STARE_ACHIZITIE", "")
        states[state] += 1
        if REJECTED_STATES.search(state):
            continue
        name = row.get("DENUMIRE_ACHIZITIE", "")
        cpv = row.get("COD_CPV", "")
        col, raw = _first(row, VALUE_COLS)
        value = _value(raw)
        hit = extract(name, cpv, value)
        if hit:
            if used is not None:
                used[col] += 1
            out.append({**hit, "numar_da": row.get("NUMAR_ACHIZITIE_DIRECTA", "").strip(),
                        "data": _day(_first(row, DATE_COLS)[1]), "cpv": cpv, "denumire": name.strip(),
                        "valoare_ron": value, "coloana_valoare": col,
                        "autoritate": _first(row, BUYER_COLS)[1].strip()})
    return out


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser()
    p.add_argument("--years", nargs="+", type=int, default=[2023, 2024, 2025, 2026])
    p.add_argument("--cache", type=Path, default=Path(tempfile.gettempdir()) / "loc-comun-seap")
    args = p.parse_args(argv)
    args.cache.mkdir(parents=True, exist_ok=True)

    files, skipped, found = [], [], {}
    for year in args.years:
        for res in resources(year):
            if res["kind"] == "skip":
                skipped.append({"an": year, "nume": res["name"], "url": res["url"], "motiv": "format .xls/.ods"})
                continue
            path = download(res["url"], args.cache)
            states: Counter = Counter()
            reader = rows_csv(path) if res["kind"] == "csv" else rows_xlsx(path)
            obs = observations(reader, states)
            for o in obs:
                found.setdefault(o["numar_da"] or f"{o['denumire']}|{o['data']}", o)
            files.append({"an": year, "nume": res["name"], "url": res["url"], "randuri": sum(states.values()),
                          "observatii": len(obs), "stari": dict(states.most_common(6))})
            print(f"{year} {res['name']}: {sum(states.values())} rânduri, {len(obs)} observații", flush=True)

    rows = sorted(found.values(), key=lambda o: (o["articol"], o["data"], o["numar_da"]))
    per = Counter(o["articol"] for o in rows)
    doc = {
        "sursa": SURSA, "licenta": LICENSE, "atribuire": "Autoritatea pentru Digitalizarea României, data.gov.ro",
        "seturi": [DATASET_PAGE.format(year=y) for y in args.years], "colectat": date.today().isoformat(),
        "tva": TVA, "prag_observatii": MIN_OBS,
        "regula": "un singur articol în denumire, o singură cantitate explicită în unitatea articolului; fără "
                  "pachete, seturi, loturi, reparații; preț unitar = valoarea atribuită / cantitate",
        "fisiere": files, "fisiere_sarite": skipped,
        "pe_articol": {k: per.get(k, 0) for k in ARTICOLE},
        "observatii": rows,
    }
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_bytes((json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    print(f"{len(rows)} observații -> {DATA_FILE}")
    for k in ARTICOLE:
        print(f"  {k}: {per.get(k, 0)}" + ("" if per.get(k, 0) >= MIN_OBS else "  (de cotat)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
