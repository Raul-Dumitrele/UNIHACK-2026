"""build_plan_dxf(scene, titlu) -> str: the schematic plan as an ASCII DXF R12 (AC1009) drawing, written by
hand (ezdxf needs numpy, a compiled dependency). Units: metres, origin at the bottom-left corner of the plot.

Only R12 entities: closed POLYLINE/VERTEX/SEQEND, LINE and TEXT (no LWPOLYLINE, no DIMENSION; the dimension
lines are LINE + TEXT). Layers: TEREN (plot boundary), ELEMENTE (elements and their free zones), COTE
(dimensions), TEXT (labels, title, notes). R12 text is ASCII, so Romanian diacritics are transliterated.
"""
import unicodedata

from backend.ai.proiect.design.scene import Scene, fmt

LAYERS = {"TEREN": 3, "ELEMENTE": 5, "COTE": 1, "TEXT": 7}  # name -> ACI colour
ZONE_COLOR = 8  # grey, for free zones
PUNCT = str.maketrans({"„": '"', "”": '"', "“": '"', "–": "-", "—": "-", "×": "x", "·": "-", "’": "'"})


def ascii_text(text: str) -> str:
    """'Zonă de joacă – 3 × 4 m' -> 'Zona de joaca - 3 x 4 m' (R12 has no Unicode text)."""
    decomposed = unicodedata.normalize("NFKD", text.translate(PUNCT))
    return "".join(c for c in decomposed if ord(c) < 128 and c.isprintable())


class _Dxf:
    def __init__(self) -> None:
        self.rows: list[str] = []

    def g(self, code: int, value) -> None:
        if isinstance(value, float):
            value = f"{value:.4f}"
        self.rows += [f"{code:>3}", str(value)]

    def polyline(self, layer: str, points: list[tuple[float, float]], color: int | None = None) -> None:
        self.g(0, "POLYLINE"); self.g(8, layer)
        if color is not None:
            self.g(62, color)
        self.g(66, 1); self.g(10, 0.0); self.g(20, 0.0); self.g(30, 0.0); self.g(70, 1)  # closed
        for x, y in points:
            self.g(0, "VERTEX"); self.g(8, layer); self.g(10, float(x)); self.g(20, float(y)); self.g(30, 0.0)
        self.g(0, "SEQEND"); self.g(8, layer)

    def rect(self, layer: str, x: float, y: float, w: float, h: float, color: int | None = None) -> None:
        self.polyline(layer, [(x, y), (x + w, y), (x + w, y + h), (x, y + h)], color)

    def line(self, layer: str, x1: float, y1: float, x2: float, y2: float) -> None:
        self.g(0, "LINE"); self.g(8, layer)
        self.g(10, float(x1)); self.g(20, float(y1)); self.g(30, 0.0)
        self.g(11, float(x2)); self.g(21, float(y2)); self.g(31, 0.0)

    def text(self, layer: str, x: float, y: float, height: float, value: str, rotation: float = 0.0) -> None:
        self.g(0, "TEXT"); self.g(8, layer)
        self.g(10, float(x)); self.g(20, float(y)); self.g(30, 0.0); self.g(40, float(height))
        self.g(1, ascii_text(value)[:250])
        if rotation:
            self.g(50, float(rotation))


def build_plan_dxf(scene: Scene, titlu: str) -> str:
    w, h = scene.latime_m, scene.lungime_m
    th = round(min(max(max(w, h) / 80, 0.2), 2.0), 2)  # text height in metres
    gap = th * 3
    notes = [f"{i}. {e.nume} ({fmt(e.latime_m)} x {fmt(e.lungime_m)} m)" for i, e in enumerate(scene.elemente, 1)]
    notes += [f"Nu incape: {o.nume} - {o.motiv}" for o in scene.omise]
    notes += [*scene.ipoteze, scene.disclaimer]
    bottom = -gap * 2 - th * 1.6 * (len(notes) + 1)

    d = _Dxf()
    d.g(0, "SECTION"); d.g(2, "HEADER")
    d.g(9, "$ACADVER"); d.g(1, "AC1009")
    d.g(9, "$EXTMIN"); d.g(10, -gap * 3); d.g(20, bottom); d.g(30, 0.0)
    d.g(9, "$EXTMAX"); d.g(10, max(w, 40 * th)); d.g(20, h + gap * 3); d.g(30, 0.0)
    d.g(0, "ENDSEC")
    d.g(0, "SECTION"); d.g(2, "TABLES")
    d.g(0, "TABLE"); d.g(2, "LTYPE"); d.g(70, 1)
    d.g(0, "LTYPE"); d.g(2, "CONTINUOUS"); d.g(70, 0); d.g(3, "Solid line"); d.g(72, 65); d.g(73, 0); d.g(40, 0.0)
    d.g(0, "ENDTAB")
    d.g(0, "TABLE"); d.g(2, "LAYER"); d.g(70, len(LAYERS))
    for name, color in LAYERS.items():
        d.g(0, "LAYER"); d.g(2, name); d.g(70, 0); d.g(62, color); d.g(6, "CONTINUOUS")
    d.g(0, "ENDTAB")
    d.g(0, "ENDSEC")

    d.g(0, "SECTION"); d.g(2, "ENTITIES")
    d.rect("TEREN", 0.0, 0.0, w, h)
    for i, e in enumerate(scene.elemente, 1):
        if e.zona_libera_m:
            z = e.zona_libera_m
            d.rect("ELEMENTE", e.x - z, e.y - z, e.latime_m + 2 * z, e.lungime_m + 2 * z, ZONE_COLOR)
        d.rect("ELEMENTE", e.x, e.y, e.latime_m, e.lungime_m)
        d.text("TEXT", e.x + e.latime_m / 2 - th / 2, e.y + e.lungime_m / 2 - th / 2, th, str(i))
    # Dimension lines: width below the plot, length to its left.
    d.line("COTE", 0.0, -gap, w, -gap)
    d.line("COTE", 0.0, -gap - th / 2, 0.0, -gap + th / 2)
    d.line("COTE", w, -gap - th / 2, w, -gap + th / 2)
    d.text("COTE", w / 2, -gap - th * 1.6, th, f"{fmt(w)} m")
    d.line("COTE", -gap, 0.0, -gap, h)
    d.line("COTE", -gap - th / 2, 0.0, -gap + th / 2, 0.0)
    d.line("COTE", -gap - th / 2, h, -gap + th / 2, h)
    d.text("COTE", -gap - th * 0.6, h / 2, th, f"{fmt(h)} m", rotation=90.0)
    d.text("TEXT", 0.0, h + gap * 2, th * 1.6, titlu)
    d.text("TEXT", 0.0, h + gap, th, f"{scene.eticheta} - teren de {fmt(scene.suprafata_mp)} mp "
                                     f"({fmt(w)} x {fmt(h)} m) - plan schematic, unitati: metri")
    y = -gap * 2 - th * 1.6
    for line in notes:
        d.text("TEXT", 0.0, y, th * 0.8, line)
        y -= th * 1.6
    d.g(0, "ENDSEC")
    d.g(0, "EOF")
    return "\n".join(d.rows) + "\n"
