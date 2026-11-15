"""build_plan_svg(scene, titlu) -> str: the schematic plan as a standalone SVG (UTF-8, no external assets).

Elements are numbered on the drawing and named in the legend (long names never overflow small shapes).
Dashed outlines are the free zones; the plot dimensions are drawn as dimension lines (cote).
"""
import textwrap
from xml.sax.saxutils import escape

from backend.ai.proiect.design.scene import Scene, fmt, numere

COLORS = {
    "alee": "#d9d4c7", "skate": "#9fb7d6", "joaca": "#f2c48d", "caini": "#b9d99b", "apa": "#8cc8e8",
    "pista": "#c9c2b8", "rastel": "#a7a7a7", "strat": "#8fbf6a", "magazie": "#b08a62", "compost": "#7d6a4f",
    "sport": "#e3a07a", "foisor": "#c79a6b", "masa": "#d7b48a", "banca": "#8d7b68", "cos": "#555555",
    "zona": "#c6d8c0",
}
SIDE_PX = 560  # longest side of the plot on the drawing
PAD_LEFT, PAD_TOP, PAD_RIGHT = 64, 76, 32
LINE_H = 16


def build_plan_svg(scene: Scene, titlu: str) -> str:
    s = SIDE_PX / max(scene.latime_m, scene.lungime_m)
    pw, ph = scene.latime_m * s, scene.lungime_m * s

    def X(x: float) -> float:
        return round(PAD_LEFT + x * s, 2)

    def Y(y: float) -> float:  # plan y is up, SVG y is down
        return round(PAD_TOP + (scene.lungime_m - y) * s, 2)

    legend = [f"{i}. {e.nume} ({fmt(e.latime_m)} × {fmt(e.lungime_m)} m)" for i, e in enumerate(scene.elemente, 1)]
    legend += [f"Nu încape: {o.nume}" + (f" (× {o.bucati})" if o.bucati > 1 else "") + f" – {o.motiv}"
               for o in scene.omise]
    legend = [line for item in legend for line in textwrap.wrap(item, 100, subsequent_indent="    ")]
    notes = [line for text in (*scene.ipoteze, scene.disclaimer) for line in textwrap.wrap(text, 100)]
    width = max(PAD_LEFT + pw + PAD_RIGHT, 720)
    legend_top = PAD_TOP + ph + 56
    height = legend_top + (len(legend) + len(notes) + 2) * LINE_H + 16

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" '
        f'viewBox="0 0 {width:.0f} {height:.0f}" font-family="Arial, Helvetica, sans-serif" font-size="12">',
        f"<title>{escape(titlu)}</title>",
        f'<rect width="{width:.0f}" height="{height:.0f}" fill="#ffffff"/>',
        f'<text x="{PAD_LEFT}" y="28" font-size="18" font-weight="bold">{escape(titlu)}</text>',
        f'<text x="{PAD_LEFT}" y="48" fill="#555">{escape(scene.eticheta)} · teren de '
        f'{fmt(scene.suprafata_mp)} mp ({fmt(scene.latime_m)} × {fmt(scene.lungime_m)} m) · plan schematic</text>',
        '<g id="TEREN">',
        f'<rect x="{X(0)}" y="{Y(scene.lungime_m)}" width="{pw:.2f}" height="{ph:.2f}" fill="#eef4e8" '
        'stroke="#2f4f2f" stroke-width="2"/>',
        "</g>",
        '<g id="ELEMENTE">',
    ]
    labels = []
    for i, e in enumerate(scene.elemente, 1):
        x, y, w, h = X(e.x), Y(e.y + e.lungime_m), e.latime_m * s, e.lungime_m * s
        if e.zona_libera_m:
            z = e.zona_libera_m
            out.append(f'<rect x="{X(e.x - z)}" y="{Y(e.y + e.lungime_m + z)}" width="{(e.latime_m + 2 * z) * s:.2f}" '
                       f'height="{(e.lungime_m + 2 * z) * s:.2f}" fill="none" stroke="#888" stroke-width="0.8" '
                       'stroke-dasharray="4 3"/>')
        out.append(f'<rect id="{e.id}" x="{x}" y="{y}" width="{w:.2f}" height="{h:.2f}" '
                   f'fill="{COLORS.get(e.tip, "#cccccc")}" stroke="#333" stroke-width="1">'
                   f"<title>{escape(e.nume)}</title></rect>")
    for text, mx, my, outside in numere(scene, lambda e: min(e.latime_m, e.lungime_m) * s < 14):
        if outside:
            labels.append(f'<text x="{X(mx)}" y="{Y(my) - 3:.2f}" text-anchor="middle" font-size="8">{text}</text>')
        else:
            labels.append(f'<text x="{X(mx)}" y="{Y(my) + 4:.2f}" text-anchor="middle" font-size="11">{text}</text>')
    out += ["</g>", '<g id="TEXT">', *labels, "</g>"]

    # Dimension lines: width below the plot, length left of it.
    by, lx = PAD_TOP + ph + 22, PAD_LEFT - 26
    out += [
        '<g id="COTE" stroke="#000" stroke-width="1">',
        f'<line x1="{X(0)}" y1="{by}" x2="{X(scene.latime_m)}" y2="{by}"/>',
        f'<line x1="{X(0)}" y1="{by - 5}" x2="{X(0)}" y2="{by + 5}"/>',
        f'<line x1="{X(scene.latime_m)}" y1="{by - 5}" x2="{X(scene.latime_m)}" y2="{by + 5}"/>',
        f'<line x1="{lx}" y1="{Y(0)}" x2="{lx}" y2="{Y(scene.lungime_m)}"/>',
        f'<line x1="{lx - 5}" y1="{Y(0)}" x2="{lx + 5}" y2="{Y(0)}"/>',
        f'<line x1="{lx - 5}" y1="{Y(scene.lungime_m)}" x2="{lx + 5}" y2="{Y(scene.lungime_m)}"/>',
        "</g>",
        f'<text x="{X(scene.latime_m / 2)}" y="{by + 18}" text-anchor="middle">{fmt(scene.latime_m)} m</text>',
        f'<text x="{lx - 8}" y="{Y(scene.lungime_m / 2)}" text-anchor="middle" '
        f'transform="rotate(-90 {lx - 8} {Y(scene.lungime_m / 2)})">{fmt(scene.lungime_m)} m</text>',
    ]
    y = legend_top
    out.append(f'<text x="{PAD_LEFT}" y="{y}" font-weight="bold">Legendă</text>')
    for line in legend:
        y += LINE_H
        out.append(f'<text x="{PAD_LEFT}" y="{y}">{escape(line)}</text>')
    y += LINE_H
    for line in notes:
        y += LINE_H
        out.append(f'<text x="{PAD_LEFT}" y="{y}" font-size="11" fill="#555">{escape(line)}</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"
