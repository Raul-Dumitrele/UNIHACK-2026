import os, shutil, subprocess, urllib.request, urllib.parse, urllib.error

UA = "Mozilla/5.0 (compatible; unihack-2026-team)"

def load_env():
    env = dict(os.environ)
    if os.path.exists(".env"):
        for line in open(".env", encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env

def fetch(url, headers=None, method="GET"):
    req = urllib.request.Request(url, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            body = r.read(200) if method == "GET" else b""
            return r.status, r.headers.get("Content-Type"), body
    except urllib.error.HTTPError as e:
        return e.code, None, b""
    except Exception as e:
        return None, None, str(e).encode()

def show(name, res):
    status, ctype, body = res
    ok = "OK  " if status and 200 <= status < 300 else "FAIL"
    print(f"[{ok}] {name}: status={status} type={ctype}")
    if body:
        print("       ", body[:150].decode("utf-8", "replace").replace("\n", " "))

env = load_env()
print("== Unelte ==")
for t in ["git", "python", "node", "npm", "claude", "tesseract"]:
    print(f"[{'OK  ' if shutil.which(t) else 'FAIL'}] {t}")

print("\n== Chei ==")
print(f"[{'OK  ' if env.get('GEMINI_API_KEY') else 'FAIL'}] GEMINI_API_KEY {'setata' if env.get('GEMINI_API_KEY') else 'lipseste'}")

print("\n== GitHub ==")
print(subprocess.run(["git", "remote", "-v"], capture_output=True, text=True).stdout or "fara remote")

print("== STPT ==")
h = {"Referer": env.get("STPT_REFERER", "https://live.stpt.ro/"), "User-Agent": UA}
base = "https://live.stpt.ro/"
for name, path in [("alerte", "proxy-alerts.php"), ("vehicule", "gtfs-vehicles.php"),
                   ("stops-index", "gtfs-data/stops-index.json"),
                   ("route-manifest", "gtfs-data/route-manifest.json"),
                   ("stop-sequences", "gtfs-data/stop-sequences.json")]:
    show(name, fetch(base + path, h))
show("GTFS static (HEAD)", fetch("https://smtt.ro/transit/gtfs/maps/smtt-timisoara-ro.zip", {"User-Agent": UA}, "HEAD"))

print("\n== Geocodare OSM ==")
q = urllib.parse.quote("Strada GÄƒrii, TimiÈ™oara")
show("Nominatim", fetch(f"https://nominatim.openstreetmap.org/search?q={q}&format=json&limit=1",
     {"User-Agent": env.get("GEOCODER_USER_AGENT", UA)}))
