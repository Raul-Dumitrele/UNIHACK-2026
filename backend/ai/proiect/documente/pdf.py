"""A small hand-written PDF 1.4 writer (no compiled dependencies): pages of any size (A4 portrait by default,
A3 landscape for drawing sheets), text with word wrap and rotation, rectangles, lines, polylines and hatches.
Deterministic: no creation date, fixed object order.

Fonts: the standard Helvetica and Helvetica-Bold (not embedded). Romanian letters missing from WinAnsi
(ă Ă ș Ș ț Ț) are mapped through a /Differences encoding onto free codes, with their standard glyph names;
the cedilla forms ş ţ use the same comma-below glyphs. Characters outside the encoding are replaced on purpose
(≈ -> ~, → -> ->, € -> EUR), anything else becomes '?'.
"""
import math
import unicodedata

PAGE_W, PAGE_H = 595.28, 841.89  # A4 portrait in points
A3_LANDSCAPE = (1190.55, 841.89)
MARGIN = 50.0
FOOTER_Y = 30.0  # PDF coordinates (from the bottom)

EXTRA = {"ă": (0x80, "abreve"), "Ă": (0x81, "Abreve"), "ș": (0x8D, "scommaaccent"),
         "Ș": (0x8E, "Scommaaccent"), "ț": (0x8F, "tcommaaccent"), "Ț": (0x90, "Tcommaaccent")}
ALIASES = {"ş": "ș", "Ş": "Ș", "ţ": "ț", "Ţ": "Ț", "≈": "~", "→": "->", "€": "EUR", "≤": "<=", "≥": ">=",
           " ": " ", " ": " ", " ": " ", "²": "2"}
WIN_ANSI = {"„": 0x84, "…": 0x85, "‘": 0x91, "’": 0x92, "“": 0x93, "”": 0x94, "•": 0x95, "–": 0x96, "—": 0x97}
# Helvetica widths (1/1000 em) for printable ASCII, from the standard font metrics; used only for wrapping.
_W = ("278 278 355 556 556 889 667 191 333 333 389 584 278 333 278 278 556 556 556 556 556 556 556 556 556 556 "
      "278 278 584 584 584 556 1015 667 667 722 722 667 611 778 722 278 500 667 556 833 722 778 667 778 722 667 "
      "611 722 667 944 667 667 611 278 278 278 469 556 333 556 556 500 556 556 278 556 556 222 222 500 222 833 "
      "556 556 556 556 333 500 278 556 500 722 500 500 500 334 260 334 584")
WIDTHS = {chr(32 + i): int(w) for i, w in enumerate(_W.split())}


def encode(text: str) -> bytes:
    out = bytearray()
    for ch in str(text):
        for c in ALIASES.get(ch, ch):
            if c in EXTRA:
                out.append(EXTRA[c][0])
            elif c in WIN_ANSI:
                out.append(WIN_ANSI[c])
            elif ord(c) < 128 or 0xA0 <= ord(c) <= 0xFF:
                out.append(ord(c))
            else:
                out.append(ord("?"))
    return bytes(out)


def _pdf_string(text: str) -> str:
    raw = encode(text).replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")
    return "(" + raw.decode("latin-1") + ")"


def text_width(text: str, size: float, bold: bool = False) -> float:
    total = 0
    for ch in str(text):
        base = unicodedata.normalize("NFKD", ALIASES.get(ch, ch))[:1] or "?"
        total += WIDTHS.get(base, 556)
    return total * size / 1000 * (1.06 if bold else 1.0)


def wrap(text: str, width: float, size: float, bold: bool = False) -> list[str]:
    lines: list[str] = []
    for para in str(text).split("\n"):
        line = ""
        for word in para.split():
            candidate = f"{line} {word}".strip()
            if text_width(candidate, size, bold) <= width or not line:
                line = candidate
            else:
                lines.append(line)
                line = word
        lines.append(line)
    return lines


def _rgb(color: str) -> str:
    c = color.lstrip("#")
    return " ".join(f"{int(c[i:i + 2], 16) / 255:.3f}" for i in (0, 2, 4))


class Pdf:
    """Cursor-based page builder; y is measured down from the top of the page (converted on output)."""

    def __init__(self, footer: str = "", size: tuple[float, float] = (PAGE_W, PAGE_H)):
        self.pages: list[tuple[tuple[float, float], list[str]]] = []
        self.footer = footer
        self.w, self.h = size
        self.new_page(size)

    def new_page(self, size: tuple[float, float] | None = None) -> None:
        if size:
            self.w, self.h = size
        self.pages.append(((self.w, self.h), []))
        self.y = MARGIN

    def ensure(self, height: float) -> None:
        if self.y + height > self.h - MARGIN - 10:
            self.new_page()

    def _op(self, op: str) -> None:
        self.pages[-1][1].append(op)

    def text_at(self, x: float, y_top: float, text: str, size: float = 10, bold: bool = False,
                color: str = "#000000") -> None:
        y = self.h - y_top - size
        self._op(f"BT /{'F2' if bold else 'F1'} {size:g} Tf {_rgb(color)} rg {x:.2f} {y:.2f} Td "
                 f"{_pdf_string(text)} Tj ET")

    def text_rot(self, x: float, y_top: float, text: str, size: float = 10, angle: float = 90.0,
                 bold: bool = False, color: str = "#000000") -> None:
        """Text rotated counter-clockwise by `angle` degrees around its start point (x, y_top)."""
        a = math.radians(angle)
        c, s = math.cos(a), math.sin(a)
        self._op(f"BT /{'F2' if bold else 'F1'} {size:g} Tf {_rgb(color)} rg {c:.4f} {s:.4f} {-s:.4f} {c:.4f} "
                 f"{x:.2f} {self.h - y_top:.2f} Tm {_pdf_string(text)} Tj ET")

    def text_center(self, cx: float, y_top: float, text: str, size: float = 10, bold: bool = False,
                    color: str = "#000000") -> None:
        self.text_at(cx - text_width(text, size, bold) / 2, y_top, text, size, bold, color)

    def rect(self, x: float, y_top: float, w: float, h: float, fill: str | None = None,
             stroke: str | None = "#333333", width: float = 0.6, dash: bool = False) -> None:
        ops = [f"{width:g} w", "[3 2] 0 d" if dash else "[] 0 d"]
        if fill:
            ops.append(f"{_rgb(fill)} rg")
        if stroke:
            ops.append(f"{_rgb(stroke)} RG")
        paint = "B" if fill and stroke else "f" if fill else "S"
        ops.append(f"{x:.2f} {self.h - y_top - h:.2f} {w:.2f} {h:.2f} re {paint}")
        self._op("q " + " ".join(ops) + " Q")

    def line(self, x1: float, y1: float, x2: float, y2: float, width: float = 0.6, color: str = "#000000",
             dash: bool = False) -> None:
        d = "[3 2] 0 d " if dash else ""
        self._op(f"q {width:g} w {d}{_rgb(color)} RG {x1:.2f} {self.h - y1:.2f} m {x2:.2f} {self.h - y2:.2f} l S Q")

    def polygon(self, points: list[tuple[float, float]], fill: str | None = None, stroke: str | None = "#000000",
                width: float = 0.6) -> None:
        if len(points) < 2:
            return
        ops = [f"{width:g} w"]
        if fill:
            ops.append(f"{_rgb(fill)} rg")
        if stroke:
            ops.append(f"{_rgb(stroke)} RG")
        path = f"{points[0][0]:.2f} {self.h - points[0][1]:.2f} m " + " ".join(
            f"{x:.2f} {self.h - y:.2f} l" for x, y in points[1:]) + " h"
        paint = "B" if fill and stroke else "f" if fill else "S"
        self._op("q " + " ".join(ops) + f" {path} {paint} Q")

    def hatch_rect(self, x: float, y_top: float, w: float, h: float, step: float = 6.0, color: str = "#555555",
                   width: float = 0.4, angle: int = 45) -> None:
        """Diagonal (45°), horizontal (0) or vertical (90) hatch lines clipped to the rectangle."""
        ops = [f"q {x:.2f} {self.h - y_top - h:.2f} {w:.2f} {h:.2f} re W n {width:g} w {_rgb(color)} RG"]
        y0 = self.h - y_top - h
        if angle == 45:
            k = -h
            while k < w:
                ops.append(f"{x + k:.2f} {y0:.2f} m {x + k + h:.2f} {y0 + h:.2f} l S")
                k += step
        elif angle == 0:
            yy = step
            while yy < h:
                ops.append(f"{x:.2f} {y0 + yy:.2f} m {x + w:.2f} {y0 + yy:.2f} l S")
                yy += step
        else:
            xx = step
            while xx < w:
                ops.append(f"{x + xx:.2f} {y0:.2f} m {x + xx:.2f} {y0 + h:.2f} l S")
                xx += step
        ops.append("Q")
        self._op(" ".join(ops))

    def paragraph(self, text: str, size: float = 10, bold: bool = False, indent: float = 0,
                  color: str = "#000000", after: float = 4, bullet: str | None = None, width: float | None = None,
                  x: float | None = None) -> None:
        pad = 12 if bullet else 0
        lead = size * 1.35
        left = (MARGIN if x is None else x) + indent
        avail = (self.w - 2 * MARGIN - indent - pad) if width is None else width - pad
        for i, line in enumerate(wrap(text, avail, size, bold)):
            self.ensure(lead)
            if bullet and i == 0:
                self.text_at(left, self.y, bullet, size, bold, color)
            self.text_at(left + pad, self.y, line, size, bold, color)
            self.y += lead
        self.y += after

    def heading(self, text: str, size: float = 13) -> None:
        self.ensure(size * 4)
        self.y += 6
        self.paragraph(text, size=size, bold=True, after=2)
        self.line(MARGIN, self.y, self.w - MARGIN, self.y, 0.5, "#888888")
        self.y += 6

    def to_bytes(self) -> bytes:
        diffs = " ".join(f"{code} /{name}" for code, name in sorted(EXTRA.values()))
        # ToUnicode for the remapped codes, so copy/search give ș ț (legacy glyph lists map
        # tcommaaccent to the cedilla form).
        pairs = "\n".join(f"<{code:02X}> <{ord(ch):04X}>" for ch, (code, _) in sorted(EXTRA.items(),
                                                                                       key=lambda kv: kv[1]))
        cmap = ("/CIDInit /ProcSet findresource begin 12 dict begin begincmap /CMapName /LocComun def "
                "/CMapType 2 def 1 begincodespacerange <00> <FF> endcodespacerange "
                f"{len(EXTRA)} beginbfchar\n{pairs}\nendbfchar endcmap CMapName currentdict /CMap defineresource "
                "pop end end").encode()
        objects: list[bytes] = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"",  # page tree, filled once the pages exist
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding 5 0 R /ToUnicode 7 0 R >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding 5 0 R /ToUnicode 7 0 R >>",
            f"<< /Type /Encoding /BaseEncoding /WinAnsiEncoding /Differences [{diffs}] >>".encode(),
            b"<< /Producer (Loc Comun) /Title (Dosar de propunere) >>",
            b"<< /Length %d >>\nstream\n" % len(cmap) + cmap + b"\nendstream",
        ]
        kids, total = [], len(self.pages)
        for n, ((w, h), ops) in enumerate(self.pages, 1):
            if self.footer:
                ops = ops + [f"BT /F1 8 Tf 0.450 0.450 0.450 rg {MARGIN:.2f} {FOOTER_Y:.2f} Td "
                             f"{_pdf_string(f'{self.footer} · pagina {n} din {total}')} Tj ET"]
            content = "\n".join(ops).encode("latin-1")
            objects.append(b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream")
            objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {w:.2f} {h:.2f}] "
                           f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {len(objects)} 0 R >>"
                           .encode())
            kids.append(f"{len(objects)} 0 R")
        objects[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {total} >>".encode()

        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = []
        for i, body in enumerate(objects, 1):
            offsets.append(len(out))
            out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
        xref = len(out)
        out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
        out += b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
        out += (f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R /Info 6 0 R >>\n"
                f"startxref\n{xref}\n%%EOF\n").encode()
        return bytes(out)
