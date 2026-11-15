"""build_materiale_xlsx(lista, titlu, cost=None) -> bytes: the bill of quantities as a styled .xlsx, written as
OOXML directly with the standard library (no openpyxl, no compiled dependency).

Sheets: "Rezumat" (totals referencing the detail sheet), "Materiale" (chapters, quantities, unit prices,
values as formulas, source with link, source type coloured), "Surse" (what each source type means).
Deterministic: same list -> same bytes (fixed zip timestamps).
"""
import io
import zipfile
from typing import Any
from xml.sax.saxutils import escape

from backend.ai.proiect.materiale import SURSE_RO, ListaMateriale

# Style indexes (cellXfs order below)
S_DEFAULT, S_TITLE, S_HEAD, S_CHAPTER, S_TEXT, S_NUM, S_MONEY, S_SEAP, S_PLAFON, S_CATALOG, S_TODO, S_TOTAL, S_NOTE, S_LINK = range(14)
FILL = {"seap": S_SEAP, "plafon": S_PLAFON, "catalog": S_CATALOG}
COLS = "ABCDEFGHIJ"

STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<numFmts count="2"><numFmt numFmtId="164" formatCode="#,##0.0"/><numFmt numFmtId="165" formatCode="#,##0&quot; lei&quot;"/></numFmts>
<fonts count="5"><font><sz val="10"/><name val="Arial"/></font><font><b/><sz val="14"/><name val="Arial"/></font>
<font><b/><sz val="10"/><name val="Arial"/></font><font><i/><sz val="9"/><color rgb="FF555555"/><name val="Arial"/></font>
<font><u/><sz val="10"/><color rgb="FF1F5C99"/><name val="Arial"/></font></fonts>
<fills count="8"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFDDE3D5"/></patternFill></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFEEF1EA"/></patternFill></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFD9F0D3"/></patternFill></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFFFF2CC"/></patternFill></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFDCE9F7"/></patternFill></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFFBE0CC"/></patternFill></fill></fills>
<borders count="2"><border><left/><right/><top/><bottom/><diagonal/></border>
<border><left/><right/><top style="thin"><color rgb="FF999999"/></top><bottom/><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="14">
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>
<xf numFmtId="0" fontId="2" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>
<xf numFmtId="0" fontId="2" fillId="3" borderId="0" xfId="0" applyFont="1" applyFill="1"/>
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>
<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
<xf numFmtId="165" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
<xf numFmtId="0" fontId="0" fillId="4" borderId="0" xfId="0" applyFill="1"/>
<xf numFmtId="0" fontId="0" fillId="5" borderId="0" xfId="0" applyFill="1"/>
<xf numFmtId="0" fontId="0" fillId="6" borderId="0" xfId="0" applyFill="1"/>
<xf numFmtId="0" fontId="0" fillId="7" borderId="0" xfId="0" applyFill="1"/>
<xf numFmtId="165" fontId="2" fillId="3" borderId="1" xfId="0" applyNumberFormat="1" applyFont="1" applyFill="1" applyBorder="1"/>
<xf numFmtId="0" fontId="3" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>
<xf numFmtId="0" fontId="4" fillId="0" borderId="0" xfId="0" applyFont="1"/>
</cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>"""


class _Sheet:
    def __init__(self, widths: list[float]):
        self.rows: list[str] = []
        self.widths = widths
        self.n = 0

    def row(self, cells: list[tuple[Any, int] | None], height: float | None = None) -> int:
        """cells: (value, style) per column; value str -> inline string, number -> number, ('=...', style) -> formula."""
        self.n += 1
        parts = []
        for i, cell in enumerate(cells):
            if cell is None:
                continue
            value, style = cell
            ref = f"{COLS[i]}{self.n}"
            if isinstance(value, str) and value.startswith("="):
                parts.append(f'<c r="{ref}" s="{style}"><f>{escape(value[1:])}</f></c>')
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                parts.append(f'<c r="{ref}" s="{style}"><v>{value}</v></c>')
            else:
                parts.append(f'<c r="{ref}" s="{style}" t="inlineStr"><is><t xml:space="preserve">{escape(str(value))}</t></is></c>')
        attrs = f' ht="{height}" customHeight="1"' if height else ""
        self.rows.append(f'<row r="{self.n}"{attrs}>{"".join(parts)}</row>')
        return self.n

    def xml(self) -> str:
        cols = "".join(f'<col min="{i + 1}" max="{i + 1}" width="{w}" customWidth="1"/>' for i, w in enumerate(self.widths))
        return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                f'<cols>{cols}</cols><sheetData>{"".join(self.rows)}</sheetData></worksheet>')


def _src_text(l) -> str:
    p = l.pret_unitar
    if not p:
        return l.motiv
    if p.tip_sursa == "seap":
        return f"SEAP, {p.observatii} achiziții ({p.perioada}): {', '.join(p.surse)}"
    if p.tip_sursa == "plafon":
        return p.nota or "plafon de program"
    return p.nota or "preț de catalog"


def build_materiale_xlsx(lista: ListaMateriale, titlu: str, cost: Any = None) -> bytes:
    mat = _Sheet([44, 11, 9, 16, 14, 14, 14, 12, 46, 40])
    mat.row([(f"Listă de materiale – {titlu}", S_TITLE)], 22)
    mat.row([("Cantitățile vin din specificația tehnică și din planul schematic; prețurile din sursa de pe rând. "
              "Valoarea = cantitate × preț unitar (formulă). Listă orientativă, nu ofertă.", S_NOTE)], 30)
    mat.row([])
    head = ["Articol", "Cantitate", "Unitate", "Preț unitar median (lei)", "Min (lei)", "Max (lei)", "Valoare (lei)",
            "Tip sursă", "Sursa / observații", "Cum s-a obținut cantitatea"]
    mat.row([(h, S_HEAD) for h in head], 30)
    subtotal_rows: list[int] = []
    for capitol in lista.capitole:
        mat.row([(capitol, S_CHAPTER)] + [("", S_CHAPTER)] * 9)
        first = mat.n + 1
        for l in (x for x in lista.linii if x.capitol == capitol):
            p = l.pret_unitar
            r = mat.n + 1
            style = FILL.get(l.tip_sursa or "", S_TODO) if p else S_TODO
            link = (f'=HYPERLINK("{p.sursa_url}","{_src_text(l)[:120]}")' if p and p.sursa_url else _src_text(l))
            mat.row([
                (l.nume, S_TEXT), (l.cantitate, S_NUM), (l.unitate, S_DEFAULT),
                (p.mediana_lei, S_MONEY) if p else ("de cotat", S_TODO),
                (p.min_lei, S_MONEY) if p else None, (p.max_lei, S_MONEY) if p else None,
                (f"=B{r}*D{r}", S_MONEY) if p else ("", S_TODO),
                (SURSE_RO.get(l.tip_sursa, l.tip_sursa) if p else "de cotat", style),
                (link, S_LINK if p and p.sursa_url else S_TEXT), (l.ipoteza, S_TEXT),
            ])
        last = mat.n
        if last >= first:
            n = mat.row([(f"Subtotal {capitol.lower()} (articole cotate)", S_TOTAL)] + [("", S_TOTAL)] * 5
                        + [(f"=SUM(G{first}:G{last})", S_TOTAL)] + [("", S_TOTAL)] * 3)
            subtotal_rows.append(n)
    mat.row([])
    total_row = mat.row([(lista.eticheta_subtotal, S_TOTAL)] + [("", S_TOTAL)] * 5
                        + [("=" + "+".join(f"G{r}" for r in subtotal_rows) if subtotal_rows else 0, S_TOTAL)]
                        + [("", S_TOTAL)] * 3)
    mat.row([])
    for note in (*lista.ipoteze, lista.sursa_preturi, lista.tva, lista.disclaimer):
        mat.row([(note, S_NOTE)])

    rez = _Sheet([46, 22])
    rez.row([(titlu, S_TITLE)], 22)
    rez.row([("Rezumat al listei de materiale", S_HEAD), ("", S_HEAD)])
    rez.row([("Articole în listă", S_TEXT), (len(lista.linii), S_DEFAULT)])
    rez.row([("Articole cu preț (cotate)", S_TEXT), (len(lista.linii) - lista.linii_de_cotat, S_DEFAULT)])
    rez.row([("Articole de cotat (fără sursă de preț)", S_TEXT), (lista.linii_de_cotat, S_DEFAULT)])
    rez.row([(lista.eticheta_subtotal, S_TOTAL), (f"=Materiale!G{total_row}", S_TOTAL)])
    for tip, n in sorted(lista.pe_surse.items()):
        rez.row([(f"  din care cu sursă „{SURSE_RO.get(tip, tip)}”", S_TEXT), (n, S_DEFAULT)])
    if lista.articole_necotate:
        rez.row([("Articole de cotat: " + "; ".join(lista.articole_necotate), S_NOTE)], 45)
    if cost is not None:
        get = lambda k: cost.get(k) if isinstance(cost, dict) else getattr(cost, k, None)  # noqa: E731
        rez.row([])
        rez.row([("Estimare din proiecte de referință (independentă de listă)", S_HEAD), ("", S_HEAD)])
        if get("suficient"):
            for lab, k in (("Minim", "min_lei"), ("Mediană", "mediana_lei"), ("Maxim", "max_lei")):
                rez.row([(lab, S_TEXT), (get(k), S_MONEY)])
        else:
            rez.row([(get("motiv") or "date insuficiente", S_NOTE)], 30)
    rez.row([])
    rez.row([("Estimare orientativă, bazată pe proiecte de referință. Nu reprezintă o autorizație; acordul din "
              "aplicație este un acord de principiu simulat.", S_NOTE)], 30)

    src = _Sheet([24, 90])
    src.row([("Tipuri de surse de preț", S_TITLE)], 22)
    for tip, text in SURSE_RO.items():
        src.row([(tip, FILL.get(tip, S_DEFAULT)), (text, S_TEXT)])
    src.row([("de cotat", S_TODO), ("niciuna dintre sursele de mai sus nu are un preț verificat pentru articol", S_TEXT)])
    src.row([])
    src.row([(lista.sursa_preturi, S_NOTE)], 30)

    sheets = [("Rezumat", rez), ("Materiale", mat), ("Surse", src)]
    workbook = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
                + "".join(f'<sheet name="{escape(n)}" sheetId="{i + 1}" r:id="rId{i + 1}"/>' for i, (n, _) in enumerate(sheets))
                + "</sheets></workbook>")
    wb_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
               '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
               + "".join(f'<Relationship Id="rId{i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
                         f'relationships/worksheet" Target="worksheets/sheet{i + 1}.xml"/>' for i in range(len(sheets)))
               + f'<Relationship Id="rId{len(sheets) + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
                 'relationships/styles" Target="styles.xml"/></Relationships>')
    content_types = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                     '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                     '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                     '<Default Extension="xml" ContentType="application/xml"/>'
                     '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.'
                     'spreadsheetml.sheet.main+xml"/>'
                     '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.'
                     'spreadsheetml.styles+xml"/>'
                     + "".join(f'<Override PartName="/xl/worksheets/sheet{i + 1}.xml" ContentType="application/vnd.'
                               'openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(len(sheets)))
                     + "</Types>")
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
            'officeDocument" Target="xl/workbook.xml"/></Relationships>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        def put(name: str, data: str) -> None:
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data.encode("utf-8"))
        put("[Content_Types].xml", content_types)
        put("_rels/.rels", rels)
        put("xl/workbook.xml", workbook)
        put("xl/_rels/workbook.xml.rels", wb_rels)
        put("xl/styles.xml", STYLES)
        for i, (_, sheet) in enumerate(sheets):
            put(f"xl/worksheets/sheet{i + 1}.xml", sheet.xml())
    return buf.getvalue()
