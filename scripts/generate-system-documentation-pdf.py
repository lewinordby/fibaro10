from __future__ import annotations

import math
import os
from datetime import date
from pathlib import Path
from typing import Iterable, Sequence

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.colors import Color, HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    HRFlowable,
    KeepTogether,
    LongTable,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "lilletorget-systemarkitektur-og-teknisk-dokumentasjon.pdf"

NAVY = HexColor("#0B1F4B")
NAVY_2 = HexColor("#15336F")
GOLD = HexColor("#DEA62C")
BLUE = HexColor("#4B6FEA")
GREEN = HexColor("#3B9368")
RED = HexColor("#C95353")
PURPLE = HexColor("#7762B6")
TEAL = HexColor("#3F8B98")
INK = HexColor("#182238")
MUTED = HexColor("#667085")
LINE = HexColor("#D7DEE8")
PAPER = HexColor("#F5F7FB")
SOFT_BLUE = HexColor("#EEF3FF")
SOFT_GOLD = HexColor("#FFF5DC")
SOFT_GREEN = HexColor("#EAF7F0")
SOFT_RED = HexColor("#FFF0F0")
SOFT_PURPLE = HexColor("#F3F0FF")
WHITE = colors.white

BUILD = (ROOT / "BUILD").read_text(encoding="utf-8").strip()
COMMIT = os.getenv("APP_COMMIT", "se GitHub")
MONTHS_NO = (
    "januar", "februar", "mars", "april", "mai", "juni",
    "juli", "august", "september", "oktober", "november", "desember",
)
_generated_date = date.today()
GENERATED = f"{_generated_date.day}. {MONTHS_NO[_generated_date.month - 1]} {_generated_date.year}"


def register_fonts() -> None:
    font_dir = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    regular = font_dir / "segoeui.ttf"
    semibold = font_dir / "seguisb.ttf"
    bold = font_dir / "segoeuib.ttf"
    light = font_dir / "segoeuil.ttf"
    pdfmetrics.registerFont(TTFont("Segoe", str(regular)))
    pdfmetrics.registerFont(TTFont("Segoe-Semibold", str(semibold)))
    pdfmetrics.registerFont(TTFont("Segoe-Bold", str(bold)))
    pdfmetrics.registerFont(TTFont("Segoe-Light", str(light)))
    pdfmetrics.registerFontFamily(
        "Segoe",
        normal="Segoe",
        bold="Segoe-Bold",
        italic="Segoe",
        boldItalic="Segoe-Bold",
    )


register_fonts()


class NumberedDocTemplate(BaseDocTemplate):
    def __init__(self, filename: str, **kwargs):
        super().__init__(filename, **kwargs)
        self.section_name = "Systemoversikt"

    def afterFlowable(self, flowable: Flowable) -> None:
        if isinstance(flowable, Paragraph):
            style_name = flowable.style.name
            if style_name == "Heading1":
                text = flowable.getPlainText()
                self.section_name = text
                key = f"h1-{self.seq.nextf('heading1')}"
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(text, key, level=0, closed=False)
                self.notify("TOCEntry", (0, text, self.page, key))
            elif style_name == "Heading2":
                text = flowable.getPlainText()
                key = f"h2-{self.seq.nextf('heading2')}"
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(text, key, level=1, closed=False)
                self.notify("TOCEntry", (1, text, self.page, key))


def draw_brand_mark(canvas: Canvas, x: float, y: float, size: float) -> None:
    canvas.saveState()
    canvas.setStrokeColor(GOLD)
    canvas.setLineWidth(max(1.2, size * 0.035))
    center_x = x + size * 0.5
    center_y = y + size * 0.5
    radius = size * 0.31
    canvas.circle(center_x, center_y, radius, stroke=1, fill=0)
    for angle in range(0, 360, 30):
        rad = math.radians(angle)
        x1 = center_x + math.cos(rad) * size * 0.39
        y1 = center_y + math.sin(rad) * size * 0.39
        x2 = center_x + math.cos(rad) * size * 0.48
        y2 = center_y + math.sin(rad) * size * 0.48
        canvas.line(x1, y1, x2, y2)
    canvas.setStrokeColor(NAVY)
    canvas.setLineWidth(max(1.6, size * 0.05))
    canvas.circle(center_x, center_y, size * 0.18, stroke=1, fill=0)
    canvas.setFont("Segoe-Semibold", size * 0.30)
    canvas.setFillColor(NAVY)
    canvas.drawCentredString(center_x, center_y - size * 0.105, "P")
    canvas.restoreState()


def cover_page(canvas: Canvas, doc: BaseDocTemplate) -> None:
    width, height = A4
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, width, height, fill=1, stroke=0)
    canvas.setFillColor(NAVY_2)
    canvas.circle(width + 25 * mm, height - 35 * mm, 82 * mm, fill=1, stroke=0)
    canvas.setFillColor(GOLD)
    canvas.rect(0, 0, width, 5 * mm, fill=1, stroke=0)
    draw_brand_mark(canvas, 25 * mm, height - 55 * mm, 23 * mm)
    canvas.setFillColor(WHITE)
    canvas.setFont("Segoe-Semibold", 19)
    canvas.drawString(53 * mm, height - 38 * mm, "Lilletorget")
    canvas.setFillColor(HexColor("#C8D4EC"))
    canvas.setFont("Segoe", 9.5)
    canvas.drawString(53 * mm, height - 45 * mm, "Soling · parkering · energi · bygg og drift")

    canvas.setFillColor(WHITE)
    canvas.setFont("Segoe-Light", 33)
    canvas.drawString(25 * mm, height - 102 * mm, "Systemarkitektur")
    canvas.drawString(25 * mm, height - 117 * mm, "og teknisk dokumentasjon")
    canvas.setFillColor(GOLD)
    canvas.rect(25 * mm, height - 128 * mm, 30 * mm, 1.7 * mm, fill=1, stroke=0)

    canvas.setFillColor(HexColor("#DBE4F5"))
    canvas.setFont("Segoe", 12)
    text = canvas.beginText(25 * mm, height - 148 * mm)
    text.setLeading(18)
    text.textLine("Komplett oversikt over oppsett, applikasjoner, dataflyt,")
    text.textLine("teknologivalg, sikkerhet, drift, backup og gjenoppretting.")
    canvas.drawText(text)

    canvas.setStrokeColor(Color(1, 1, 1, alpha=0.18))
    canvas.line(25 * mm, 54 * mm, width - 25 * mm, 54 * mm)
    canvas.setFillColor(WHITE)
    canvas.setFont("Segoe-Semibold", 9.5)
    canvas.drawString(25 * mm, 42 * mm, f"Produksjonsbuild {BUILD}")
    canvas.drawString(76 * mm, 42 * mm, f"Commit {COMMIT}")
    canvas.drawRightString(width - 25 * mm, 42 * mm, GENERATED)
    canvas.setFillColor(HexColor("#AEBEDC"))
    canvas.setFont("Segoe", 8.5)
    canvas.drawString(25 * mm, 33 * mm, "Intern systemhåndbok · Basert på faktisk QNAP-oppsett og produksjonsstatus")
    canvas.restoreState()


def body_page(canvas: Canvas, doc: NumberedDocTemplate) -> None:
    width, height = doc.pagesize
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.55)
    canvas.line(doc.leftMargin, height - 18 * mm, width - doc.rightMargin, height - 18 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont("Segoe", 7.5)
    canvas.drawString(doc.leftMargin, height - 13.8 * mm, "LILLETORGET · SYSTEMDOKUMENTASJON")
    canvas.drawRightString(width - doc.rightMargin, height - 13.8 * mm, f"BUILD {BUILD} · {doc.section_name.upper()}")
    canvas.line(doc.leftMargin, 15 * mm, width - doc.rightMargin, 15 * mm)
    canvas.drawString(doc.leftMargin, 10.8 * mm, "Intern teknisk dokumentasjon")
    canvas.drawRightString(width - doc.rightMargin, 10.8 * mm, f"Side {doc.page}")
    canvas.restoreState()


def landscape_page(canvas: Canvas, doc: NumberedDocTemplate) -> None:
    body_page(canvas, doc)


class CoverSpacer(Flowable):
    def __init__(self):
        super().__init__()
        self.width = 1
        self.height = 1

    def draw(self) -> None:
        return


def p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text, style)


def bullet(text: str, styles: dict[str, ParagraphStyle]) -> Paragraph:
    return Paragraph(text, styles["Bullet"])


def table_paragraph(value: object, styles: dict[str, ParagraphStyle], bold: bool = False) -> Paragraph:
    text = str(value if value is not None else "")
    if bold:
        text = f"<b>{text}</b>"
    return Paragraph(text, styles["TableText"])


def make_table(
    rows: Sequence[Sequence[object]],
    widths: Sequence[float],
    styles: dict[str, ParagraphStyle],
    *,
    repeat_rows: int = 1,
    font_size: float = 7.3,
    header_color: Color = NAVY,
    zebra: bool = True,
) -> LongTable:
    converted: list[list[Paragraph]] = []
    for row_index, row in enumerate(rows):
        converted.append(
            [
                Paragraph(
                    f"<b>{value}</b>" if row_index < repeat_rows else str(value),
                    ParagraphStyle(
                        f"Cell-{row_index}",
                        parent=styles["TableText"],
                        fontName="Segoe-Semibold" if row_index < repeat_rows else "Segoe",
                        fontSize=font_size,
                        leading=font_size + 2.1,
                        textColor=WHITE if row_index < repeat_rows else INK,
                    ),
                )
                for value in row
            ]
        )
    result = LongTable(converted, colWidths=list(widths), repeatRows=repeat_rows, hAlign="LEFT")
    commands: list[tuple] = [
        ("BACKGROUND", (0, 0), (-1, repeat_rows - 1), header_color),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, repeat_rows - 1), (-1, -1), 0.35, LINE),
    ]
    if zebra:
        for row_index in range(repeat_rows, len(rows)):
            if (row_index - repeat_rows) % 2:
                commands.append(("BACKGROUND", (0, row_index), (-1, row_index), PAPER))
    result.setStyle(TableStyle(commands))
    return result


def info_cards(items: Sequence[tuple[str, str, str]], styles: dict[str, ParagraphStyle]) -> Table:
    cells = []
    for label, value, detail in items:
        cells.append(
            Table(
                [
                    [Paragraph(label.upper(), styles["CardLabel"])],
                    [Paragraph(value, styles["CardValue"])],
                    [Paragraph(detail, styles["CardDetail"])],
                ],
                colWidths=[47 * mm],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), PAPER),
                        ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, 0), 7),
                        ("TOPPADDING", (0, 1), (-1, -1), 2),
                        ("BOTTOMPADDING", (0, 2), (-1, 2), 7),
                    ]
                ),
            )
        )
    return Table([cells], colWidths=[50 * mm] * len(cells), hAlign="LEFT")


def callout(title: str, text: str, styles: dict[str, ParagraphStyle], color: Color = BLUE) -> Table:
    return Table(
        [[Paragraph(title, styles["CalloutTitle"]), Paragraph(text, styles["CalloutText"])]],
        colWidths=[42 * mm, 112 * mm],
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PAPER),
                ("LINEBEFORE", (0, 0), (0, -1), 4, color),
                ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        ),
    )


def _box(
    drawing: Drawing,
    x: float,
    y: float,
    width: float,
    height: float,
    lines: Sequence[str],
    *,
    fill: Color,
    stroke: Color,
    title_color: Color = INK,
    font_size: float = 8.2,
    radius: float = 5,
) -> None:
    drawing.add(Rect(x, y, width, height, rx=radius, ry=radius, fillColor=fill, strokeColor=stroke, strokeWidth=0.9))
    line_height = font_size + 2.2
    total = line_height * len(lines)
    current_y = y + (height + total) / 2 - line_height + 1
    for index, line in enumerate(lines):
        drawing.add(
            String(
                x + width / 2,
                current_y - index * line_height,
                line,
                textAnchor="middle",
                fontName="Segoe-Semibold" if index == 0 else "Segoe",
                fontSize=font_size if index == 0 else font_size - 0.7,
                fillColor=title_color if index == 0 else MUTED,
            )
        )


def _arrow(
    drawing: Drawing,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    *,
    color: Color = HexColor("#77839A"),
    dashed: bool = False,
    width: float = 1.1,
) -> None:
    line = Line(x1, y1, x2, y2, strokeColor=color, strokeWidth=width)
    if dashed:
        line.strokeDashArray = [4, 3]
    drawing.add(line)
    angle = math.atan2(y2 - y1, x2 - x1)
    size = 5
    p1 = (x2, y2)
    p2 = (x2 - size * math.cos(angle - 0.55), y2 - size * math.sin(angle - 0.55))
    p3 = (x2 - size * math.cos(angle + 0.55), y2 - size * math.sin(angle + 0.55))
    drawing.add(Polygon([p1[0], p1[1], p2[0], p2[1], p3[0], p3[1]], fillColor=color, strokeColor=color))


def _label(drawing: Drawing, x: float, y: float, text: str, color: Color = MUTED, size: float = 7.2) -> None:
    drawing.add(String(x, y, text, fontName="Segoe-Semibold", fontSize=size, fillColor=color, textAnchor="middle"))


def architecture_overview() -> Drawing:
    w, h = 750, 430
    d = Drawing(w, h)
    d.add(String(0, 412, "Lagvis systemarkitektur", fontName="Segoe-Semibold", fontSize=14, fillColor=NAVY))
    d.add(String(0, 397, "Fra brukerflater via sikker inngang og fagapper til data, innsamlere og fysiske systemer.", fontName="Segoe", fontSize=8.5, fillColor=MUTED))

    lane_y = [336, 263, 184, 102, 22]
    lane_titles = ["KLIENTER", "HTTPS OG INNLOGGING", "BRUKERFLATER", "KJERNE OG TJENESTER", "DATA OG FYSISKE KILDER"]
    for y, title in zip(lane_y, lane_titles):
        d.add(Rect(0, y, 92, 54, rx=4, ry=4, fillColor=NAVY, strokeColor=NAVY))
        d.add(String(46, y + 24, title, textAnchor="middle", fontName="Segoe-Semibold", fontSize=6.8, fillColor=WHITE))

    for x, title in [(110, "PC / Mac"), (250, "Nettbrett"), (390, "Mobil / PWA"), (530, "OwnTracks Android")]:
        _box(d, x, 336, 120, 54, [title, "Nettleser eller klient"], fill=SOFT_BLUE, stroke=BLUE)

    _box(d, 130, 263, 180, 54, ["Caddy reverse proxy", "DNS · TLS · sikkerhetsheadere"], fill=SOFT_GOLD, stroke=GOLD)
    _box(d, 340, 263, 180, 54, ["Felles innlogging", "DB-sesjon · delt sikker cookie"], fill=SOFT_PURPLE, stroke=PURPLE)
    _box(d, 550, 263, 160, 54, ["Tilgangsgrenser", "LAN/VPN eller valgt mobilflate"], fill=SOFT_RED, stroke=RED)

    _box(d, 105, 184, 250, 54, ["Mantis · 13 apper", "ny.lilletorget.net · Nginx 8170"], fill=SOFT_PURPLE, stroke=PURPLE, font_size=8)
    _box(d, 375, 184, 150, 54, ["Mobil og kiosk", "Egne arbeidsflater"], fill=SOFT_PURPLE, stroke=PURPLE, font_size=7.5)
    _box(d, 545, 184, 160, 54, ["OwnTracks-web", "Egen lokasjonsflate"], fill=PAPER, stroke=LINE, font_size=7.3)

    _box(d, 110, 102, 175, 54, ["Fagadaptere", "FastAPI · port 8151-8158"], fill=SOFT_GOLD, stroke=GOLD)
    _box(d, 310, 102, 175, 54, ["Fibaro10 API", "Domenelogikk · database · admin"], fill=SOFT_GOLD, stroke=GOLD)
    _box(d, 510, 102, 175, 54, ["Worker og sidetjenester", "Import · kontroll · varsling"], fill=SOFT_GREEN, stroke=GREEN)

    data_boxes = [
        (105, "PostgreSQL", "Forretningsdata"),
        (215, "HC3", "Energi · dører"),
        (325, "EasyPark / Sun2", "Salg · parkering"),
        (435, "Kamera / AI", "Axis · Protect"),
        (545, "OwnTracks", "Sted · besøk"),
        (655, "Andre", "Yr · Elvia · SVV"),
    ]
    for x, title, sub in data_boxes:
        _box(d, x, 22, 95, 54, [title, sub], fill=SOFT_BLUE if title == "PostgreSQL" else PAPER, stroke=TEAL if title == "PostgreSQL" else LINE, font_size=7.1)

    # Parallelle forbindelser samles i busser slik at oversikten forblir lesbar.
    d.add(Line(170, 326, 590, 326, strokeColor=HexColor("#77839A"), strokeWidth=1.0))
    for x in [170, 310, 450, 590]:
        d.add(Line(x, 336, x, 326, strokeColor=HexColor("#77839A"), strokeWidth=1.0))
    _arrow(d, 220, 326, 220, 317)
    _arrow(d, 310, 290, 340, 290)
    _arrow(d, 520, 290, 550, 290)
    d.add(Line(146, 251, 704, 251, strokeColor=HexColor("#77839A"), strokeWidth=0.9))
    _arrow(d, 430, 263, 430, 251, width=0.9)
    for x in [230, 450, 625]:
        _arrow(d, x, 251, x, 238, width=0.7)
    d.add(Line(146, 171, 704, 171, strokeColor=HexColor("#77839A"), strokeWidth=0.9))
    for x in [230, 450, 625]:
        d.add(Line(x, 184, x, 171, strokeColor=HexColor("#77839A"), strokeWidth=0.7))
    _arrow(d, 230, 171, 198, 156, width=0.9)
    _arrow(d, 285, 129, 310, 129)
    _arrow(d, 485, 129, 510, 129)
    _arrow(d, 510, 118, 485, 118, color=GREEN, width=0.8)

    # PostgreSQL hører til API-et. De øvrige kildene mater worker/sidetjenester.
    _arrow(d, 397, 102, 152, 76, color=TEAL, width=0.9)
    _arrow(d, 152, 76, 397, 102, color=TEAL, dashed=True, width=0.7)
    d.add(Line(262, 88, 702, 88, strokeColor=HexColor("#77839A"), strokeWidth=0.8))
    for x in [262, 372, 482, 592, 702]:
        d.add(Line(x, 76, x, 88, strokeColor=HexColor("#77839A"), strokeWidth=0.7))
    _arrow(d, 598, 88, 598, 102, width=0.9)
    d.scale(0.96, 0.90)
    d.width = w * 0.96
    d.height = h * 0.90
    return d


def request_auth_diagram() -> Drawing:
    w, h = 750, 360
    d = Drawing(w, h)
    d.add(String(0, 342, "Forespørsel, ruting og felles innlogging", fontName="Segoe-Semibold", fontSize=14, fillColor=NAVY))
    columns = [65, 205, 355, 515, 675]
    names = ["Nettleser", "Caddy", "Mantis-app", "Fibaro10 API", "PostgreSQL"]
    colors_list = [BLUE, GOLD, PURPLE, GOLD, TEAL]
    for x, name, col in zip(columns, names, colors_list):
        _box(d, x - 48, 286, 96, 40, [name], fill=PAPER, stroke=col, font_size=8)
        d.add(Line(x, 50, x, 286, strokeColor=LINE, strokeWidth=0.8, strokeDashArray=[3, 3]))

    steps = [
        (1, 65, 205, 260, "1  HTTPS-forespørsel"),
        (2, 205, 355, 235, "2  Reverse proxy"),
        (3, 355, 515, 210, "3  Kontroller cookie"),
        (4, 515, 675, 185, "4  Slå opp sesjon"),
        (5, 675, 515, 160, "5  Bruker + gyldighet"),
        (6, 515, 355, 135, "6  Autorisert kontekst"),
        (7, 355, 515, 110, "7  Hent domenedata"),
        (8, 515, 355, 85, "8  JSON-respons"),
        (9, 355, 65, 60, "9  Side og data"),
    ]
    for _, x1, x2, y, label in steps:
        _arrow(d, x1, y, x2, y, color=HexColor("#6F7D94"))
        _label(d, (x1 + x2) / 2, y + 5, label, size=6.6)

    d.add(Rect(145, 10, 460, 26, rx=4, ry=4, fillColor=SOFT_PURPLE, strokeColor=PURPLE, strokeWidth=0.7))
    d.add(String(375, 20, "Én lilletorget_session gjelder for .lilletorget.net og tilbakekalles sentralt ved utlogging.", textAnchor="middle", fontName="Segoe", fontSize=7.5, fillColor=INK))
    return d


def data_flow_diagram() -> Drawing:
    w, h = 750, 455
    d = Drawing(w, h)
    d.add(String(0, 438, "Dataflyt fra kildesystem til brukerflate", fontName="Segoe-Semibold", fontSize=14, fillColor=NAVY))
    d.add(String(0, 423, "Hver faglinje har egen innsamler eller ingest, men ender i kontrollert lagring og samme analysegrunnlag.", fontName="Segoe", fontSize=8.5, fillColor=MUTED))
    headings = [(70, "KILDE"), (240, "INNSAMLING"), (420, "KONTROLL / API"), (590, "LAGRING / BRUK")]
    for x, title in headings:
        d.add(String(x, 397, title, textAnchor="middle", fontName="Segoe-Semibold", fontSize=7.2, fillColor=MUTED))

    lanes = [
        (330, "PARKERING", BLUE, ["EasyPark / Gmail", "EasyPark downloader", "Import + prognose", "Parkering · kjøretøy"]),
        (260, "SOLING", GOLD, ["Sun2", "Scraper / dagsfiler", "Ingest + avstemming", "Timer · salg · bilder"]),
        (190, "BYGG / ENERGI", GREEN, ["HC3 / Yr / Elvia", "Lua + worker + opplasting", "Validering + regler", "Energi · dører · klima"]),
        (120, "KAMERA", RED, ["Axis / UniFi Protect", "Snapshots / event ledger", "Fast utsnitt + lokal AI", "Bilder · avvik · alarm"]),
        (50, "LOKASJON", PURPLE, ["OwnTracks Android", "HTTP OwnTracks service", "Sone- og besøkslogikk", "Besøk · vedlikehold"]),
    ]
    for y, lane, color, items in lanes:
        d.add(Rect(0, y, 122, 48, rx=4, ry=4, fillColor=color, strokeColor=color))
        d.add(String(61, y + 20, lane, textAnchor="middle", fontName="Segoe-Semibold", fontSize=7, fillColor=WHITE))
        xs = [140, 300, 460, 620]
        widths = [130, 140, 140, 120]
        for x, width, text in zip(xs, widths, items):
            _box(d, x, y, width, 48, [text], fill=PAPER, stroke=color, font_size=7.5)
        _arrow(d, 270, y + 24, 300, y + 24, color=color)
        _arrow(d, 440, y + 24, 460, y + 24, color=color)
        _arrow(d, 600, y + 24, 620, y + 24, color=color)

    d.add(Rect(140, 5, 600, 25, rx=4, ry=4, fillColor=SOFT_GREEN, strokeColor=GREEN, strokeWidth=0.7))
    d.add(String(440, 14, "Importstatus, siste kjøring, antall rader, varighet og feil vises samlet som 24 datakilder.", textAnchor="middle", fontName="Segoe", fontSize=7.4, fillColor=INK))
    d.scale(0.96, 0.84)
    d.width = w * 0.96
    d.height = h * 0.84
    return d


def deployment_diagram() -> Drawing:
    w, h = 750, 370
    d = Drawing(w, h)
    d.add(String(0, 352, "Utvikling, kvalitetssikring og kontrollert utrulling", fontName="Segoe-Semibold", fontSize=14, fillColor=NAVY))
    nodes = [
        (20, "Utviklings-PC", "Codex · lokale tester", BLUE),
        (155, "GitHub", "Fibaro10 + Mantis", PURPLE),
        (290, "QNAP deploy", "backup · release · image", GOLD),
        (425, "Ny kandidat", "image eller blue/green", TEAL),
        (560, "Helsesjekk", "API · DB · datakilder", GREEN),
        (650, "Trafikkbytte", "Caddy gateway", NAVY_2),
    ]
    for x, title, sub, color in nodes:
        width = 118 if x < 650 else 95
        _box(d, x, 260, width, 56, [title, sub], fill=PAPER, stroke=color, font_size=7.8)
    for x1, x2 in [(138, 155), (273, 290), (408, 425), (543, 560), (678, 650)]:
        if x1 < x2:
            _arrow(d, x1, 288, x2, 288)
    _arrow(d, 678, 288, 650, 288)

    _box(d, 425, 168, 118, 50, ["Aktiv release", "forrige stabile beholdes"], fill=SOFT_BLUE, stroke=BLUE, font_size=7.6)
    _arrow(d, 697, 260, 484, 218, color=GREEN)
    _label(d, 598, 232, "godkjent", color=GREEN)
    _arrow(d, 560, 270, 484, 218, color=RED, dashed=True)
    _label(d, 522, 238, "feil: behold aktiv", color=RED)

    _box(d, 155, 168, 118, 50, ["Worker", "bakgrunnsjobber"], fill=SOFT_GREEN, stroke=GREEN, font_size=7.6)
    _arrow(d, 697, 260, 214, 218, color=GREEN)
    _label(d, 360, 226, "start ny worker etter trafikkbytte", color=GREEN)

    checks = [
        (20, "Lokalt", "Python · typecheck · builds"),
        (175, "Sikkerhet", "npm audit · statisk kontroll"),
        (330, "Runtime", "25 HTTP · alle containere"),
        (485, "Data", "24 datakilder"),
        (640, "UI", "127 Mantis · 228 API-ruter"),
    ]
    for x, title, sub in checks:
        _box(d, x, 65, 112, 52, [title, sub], fill=PAPER, stroke=LINE, font_size=7.3)
    for x in [132, 287, 442, 597]:
        _arrow(d, x, 91, x + 43, 91, color=LINE)

    d.add(Rect(20, 18, 732, 27, rx=4, ry=4, fillColor=SOFT_GOLD, strokeColor=GOLD, strokeWidth=0.7))
    d.add(String(386, 28, "Fibaro10 bruker selektiv/blue-green deploy. Mantis bygger komplett image og går tilbake til forrige release ved feil.", textAnchor="middle", fontName="Segoe", fontSize=7.4, fillColor=INK))
    return d


def storage_backup_diagram() -> Drawing:
    w, h = 750, 390
    d = Drawing(w, h)
    d.add(String(0, 372, "Lagring, arkiv og gjenoppretting", fontName="Segoe-Semibold", fontSize=14, fillColor=NAVY))
    sources = [
        (15, 285, "Hoveddatabase", "PostgreSQL", BLUE),
        (15, 210, "OwnTracks DB", "PostgreSQL 17", PURPLE),
        (15, 135, "Protect / AI", "bilder og modeller", RED),
        (15, 60, "Robotlogger / runtime", "Roborock · Dreame · .env", GREEN),
    ]
    for x, y, title, sub, color in sources:
        _box(d, x, y, 145, 52, [title, sub], fill=PAPER, stroke=color, font_size=8)

    _box(d, 235, 225, 190, 94, ["Nattlig backupjobb", "SQL-dumper · runtimefiler", "checksums · atomisk publisering"], fill=SOFT_GOLD, stroke=GOLD, font_size=8)
    for y in [311, 236, 161, 86]:
        _arrow(d, 160, y, 235, 270, color=HexColor("#77839A"))

    _box(d, 500, 265, 220, 64, ["Vol3 backup / arkiv", "/share/CACHEDEV3_DATA/fibaro10_archive", "20 nyeste nattbackuper"], fill=SOFT_BLUE, stroke=TEAL, font_size=7.8)
    _arrow(d, 425, 272, 500, 297, color=GOLD)

    _box(d, 500, 165, 220, 64, ["Full restore-pakke", "repo · konfig · SQL · data", "kan flyttes til ny QNAP"], fill=SOFT_GREEN, stroke=GREEN, font_size=7.8)
    _arrow(d, 610, 265, 610, 229, color=GREEN)

    _box(d, 235, 65, 190, 64, ["Verifikasjon", "midlertidige databaser", "SHA-256 · restore-test"], fill=SOFT_PURPLE, stroke=PURPLE, font_size=7.8)
    _arrow(d, 500, 197, 425, 97, color=PURPLE)

    _box(d, 500, 55, 220, 64, ["Ny eller reparert QNAP", "restore · compose up", "health · smoke · live test"], fill=PAPER, stroke=NAVY_2, font_size=7.8)
    _arrow(d, 425, 97, 500, 87, color=NAVY_2)

    d.add(Rect(190, 10, 335, 28, rx=4, ry=4, fillColor=SOFT_RED, strokeColor=RED, strokeWidth=0.7))
    d.add(String(357, 20, "Axis-bufferen er eget arkiv. Bilder som er koblet til soltimer lagres i hoveddatabasen.", textAnchor="middle", fontName="Segoe", fontSize=7.2, fillColor=INK))
    return d


def styles() -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()
    result: dict[str, ParagraphStyle] = {}
    result["Title"] = ParagraphStyle("Title", fontName="Segoe-Light", fontSize=25, leading=29, textColor=NAVY, spaceAfter=12)
    result["Subtitle"] = ParagraphStyle("Subtitle", fontName="Segoe", fontSize=11, leading=16, textColor=MUTED, spaceAfter=16)
    result["Heading1"] = ParagraphStyle("Heading1", fontName="Segoe-Semibold", fontSize=18, leading=23, textColor=NAVY, spaceBefore=8, spaceAfter=10, keepWithNext=True)
    result["Heading2"] = ParagraphStyle("Heading2", fontName="Segoe-Semibold", fontSize=12.5, leading=16, textColor=NAVY_2, spaceBefore=12, spaceAfter=6, keepWithNext=True)
    result["Heading3"] = ParagraphStyle("Heading3", fontName="Segoe-Semibold", fontSize=10, leading=13, textColor=INK, spaceBefore=8, spaceAfter=4, keepWithNext=True)
    result["Body"] = ParagraphStyle("Body", fontName="Segoe", fontSize=9, leading=13.2, textColor=INK, spaceAfter=7)
    result["Small"] = ParagraphStyle("Small", fontName="Segoe", fontSize=7.6, leading=10.4, textColor=MUTED, spaceAfter=4)
    result["Bullet"] = ParagraphStyle("Bullet", parent=result["Body"], leftIndent=12, firstLineIndent=-7, bulletIndent=0, bulletText="•", spaceAfter=4)
    result["TableText"] = ParagraphStyle("TableText", fontName="Segoe", fontSize=7.3, leading=9.5, textColor=INK)
    result["CardLabel"] = ParagraphStyle("CardLabel", fontName="Segoe-Semibold", fontSize=6.7, leading=8, textColor=MUTED)
    result["CardValue"] = ParagraphStyle("CardValue", fontName="Segoe-Semibold", fontSize=16, leading=19, textColor=NAVY)
    result["CardDetail"] = ParagraphStyle("CardDetail", fontName="Segoe", fontSize=7.2, leading=9, textColor=MUTED)
    result["CalloutTitle"] = ParagraphStyle("CalloutTitle", fontName="Segoe-Semibold", fontSize=9.2, leading=12, textColor=NAVY)
    result["CalloutText"] = ParagraphStyle("CalloutText", fontName="Segoe", fontSize=8.2, leading=11.5, textColor=INK)
    result["TOCHeading"] = ParagraphStyle("TOCHeading", fontName="Segoe-Semibold", fontSize=20, leading=24, textColor=NAVY, spaceAfter=12)
    return result


WEB_APPS = [
    ("Omsetning", "https://ny.lilletorget.net/omsetning/", "8170", "Dashboard, månedsoversikt, år og sammenligning."),
    ("Parkering", "https://ny.lilletorget.net/parkering/", "8170", "Parkeringer, kjøretøy, oppgjør, tidsanalyse og prognoser."),
    ("Soling", "https://ny.lilletorget.net/soling/", "8170", "Soltimer, bilder, senger, medlemmer, produkter og oppgjør."),
    ("Koble", "https://ny.lilletorget.net/koble/", "8170", "Kontroll av kobling mellom bil og Sun2-ID."),
    ("Bygg", "https://ny.lilletorget.net/bygg/", "8170", "Ventilasjon, klima, lys og styring."),
    ("Renhold", "https://ny.lilletorget.net/renhold/", "8170", "Roboter, planer, vann og rapporter."),
    ("Kontroll", "https://ny.lilletorget.net/kontroll/", "8170", "Dører, solrom, alarm og pullerter."),
    ("Energi", "https://ny.lilletorget.net/energi/", "8170", "Sanntid, Elvia-kontroll, kurs/last og solsengforbruk."),
    ("Vedlikehold", "https://ny.lilletorget.net/vedlikehold/", "8170", "Besøk, oppgaver og vedlikeholdshistorikk."),
    ("Operasjon", "https://ny.lilletorget.net/operasjon/", "8170", "Arbeidskø, kontroller, datakvalitet og søk."),
    ("Eiendeler", "https://ny.lilletorget.net/eiendeler/", "8170", "Teknisk register, service og garanti."),
    ("Rapporter", "https://ny.lilletorget.net/rapporter/", "8170", "Samlet rapportkatalog."),
    ("System", "https://ny.lilletorget.net/system/", "8170", "Datakilder, brukere, build, manual og verktøy."),
]

SPECIAL_APPS = [
    ("Robotkiosk", "https://kiosk.lilletorget.net/", "8163", "Fast 1920 x 1080 robotstatus."),
    ("Online dashboard", "https://online.lilletorget.net/", "8111", "Begrenset ekstern nøkkeltallflate, med direkte database-lesing."),
    ("Vedlikehold mobil", "https://vedl.lilletorget.net/", "8112", "Rask mobilregistrering mot Fibaro10 API."),
    ("Alarm mobil", "https://alarm.lilletorget.net/", "8114", "Dør-, solrom-, pullert- og trappealarmer med ntfy-dyplenker."),
    ("OwnTracks", "https://owntracks.lilletorget.net/", "8128", "HTTP-mottak, waypoints, opphold, sonebesøk og kart."),
]

COMPONENTS = [
    ("fibaro10 / blue / green", "Kjerne", "Kritisk", "FastAPI API og blue/green web-runtime."),
    ("fibaro10_worker", "Kjerne", "Kritisk", "Planlagte jobber, kontroll, vedlikehold og varsling."),
    ("fibaro10_proxy", "Infrastruktur", "Kritisk", "Caddy reverse proxy, HTTPS og tilgangsgrenser."),
    ("lilletorget_mantis", "Frontend", "Høy", "Tretten Mantis-apper og Nginx på port 8170."),
    ("revenue_app", "Omsetning", "Normal", "Avgrenset API-adapter uten frontend."),
    ("parking_app", "Parkering", "Høy", "Avgrenset API-adapter uten frontend."),
    ("sun_app", "Soling", "Høy", "Avgrenset API-adapter uten frontend."),
    ("energy_app", "Energi", "Høy", "Avgrenset API-adapter uten frontend."),
    ("operations_app", "Bygg/Renhold/Kontroll", "Høy", "Avgrenset API-adapter uten frontend."),
    ("maintenance_app", "Vedlikehold", "Normal", "Avgrenset API-adapter uten frontend."),
    ("system_app", "System", "Normal", "Avgrenset API-adapter uten frontend."),
    ("link_app", "Koble", "Normal", "Avgrenset API-adapter uten frontend."),
    ("online_dashboard", "Mobil/ekstern", "Høy", "Begrenset dashboardflate."),
    ("maintenance_mobile", "Vedlikehold", "Normal", "Mobil vedlikeholdsregistrering."),
    ("alarm_mobile", "Alarm", "Høy", "Mobil alarm- og kontrollflate."),
    ("lilletorget_kiosk", "Renhold", "Normal", "Fast robotstatus i eget repo."),
    ("owntracks_service", "Lokasjon", "Normal", "HTTP-mottak, kart, waypoints og sonebesøk."),
    ("owntracks_postgres", "Lokasjon", "Høy", "Separat PostgreSQL 17 for OwnTracks."),
    ("axis_camera_snapshots", "Bilder", "Høy", "Tar snapshots hvert 5. sekund i åpningstiden."),
    ("unifi_protect_events", "Kamera", "Høy", "Protect event ledger, kjøretøy og kontrollbilder."),
    ("visual_anomaly_service", "Kamera", "Normal", "Lokal PatchCore-analyse på CPU."),
    ("car_info_lookup", "Parkering", "Normal", "Svenske og danske kjøretøyoppslag."),
    ("sun2_session_scraper", "Soling", "Kritisk", "Enkelttimer, senger, medlemmer, salg og oppgjør."),
    ("sun2_importer", "Soling", "Lav", "Dagsfiler og romsummer."),
    ("sun2_backfill_downloader", "Soling", "Lav", "Historisk bakfylling av Sun2-filer."),
    ("easypark_downloader", "Parkering", "Kritisk", "Planlagt nedlasting og importtrigger."),
    ("parking_sun_linker", "Koble", "Høy", "Kontinuerlig koblingsmotor."),
    ("roborock_logger", "Renhold", "Normal", "Robotstatus, historikk, planer og kart."),
    ("dreame_logger", "Renhold", "Normal", "Aqua10-status, historikk, planer og kontroll via Dreamehome."),
    ("hc3_vedlikehold / scener", "HC3", "Normal", "Lua, blokk-scener og vedlikeholdsverktøy."),
]

DATA_SOURCES = [
    (1, "Lys / lux fra HC3", "Lys", "HC3", "Ca. 7 min", "Lux og lysstyringsstatus."),
    (2, "Ventilasjon / temperatur fra HC3", "Ventilasjon", "HC3", "Ca. 7 min", "Temperatur, fuktighet, modus og viftestatus."),
    (3, "Yr API", "Vær", "MET/Yr", "Ca. 70 min", "Vær, skydekke, vind, fuktighet og prognose."),
    (4, "Energi fra HC3", "Energi", "HC3", "30 sek", "Realtime effekt. Akkumulert verdi brukes som kontroll."),
    (5, "Roborock logger", "Renhold", "Roborock", "Ca. 10 min", "Roboter, status, jobber, forbruksmateriell og kart."),
    (6, "Sun2 dagsfil nedlasting", "Soling", "Sun2 backfill", "Daglig", "Laster ned forrige dags CSV."),
    (7, "Sun2 dagsimport rom", "Soling", "Sun2 importer", "Daglig", "Importerer romsummer fra dagsfil."),
    (8, "Sun2 enkelttimer", "Soling", "Sun2 scraper", "Ca. 7 min", "Enkelttimer med ID, rom, tid, beløp og varighet."),
    (9, "Sun2 senger", "Soling", "Sun2 scraper", "Ukentlig", "Senge- og romregister."),
    (10, "Sun2 medlemmer", "Soling", "Sun2 scraper", "Ukentlig", "Medlemsregister og Sun2-ID."),
    (11, "Sun2 produktsalg daglig", "Soling", "Sun2 scraper", "Daglig", "Produktlinjer per dag."),
    (12, "Sun2 produktsalg månedskontroll", "Soling", "Sun2 scraper", "Månedlig", "Kontroll av forrige måned."),
    (13, "Sun2 finansoppgjør", "Soling", "Sun2 scraper", "Månedlig", "Oppgjør og avstemming."),
    (14, "Elvia månedsfil", "Energi", "Manuell fil", "Månedlig", "Timesverdier fra Elvia, krever BankID-eksport."),
    (15, "EasyPark import", "Parkering", "EasyPark CSV", "08, 10, 12, 14, 16, 18, 20, 23", "Parkeringer, oppdatering og prognose etter import."),
    (16, "Parkering historikk", "Parkering", "QNAP appdb", "Engangsmigrering", "Migrert historikk, kjøretøy og SVV-nøkkeldata."),
    (17, "Kjøretøydata fra SVV", "Parkering", "Statens vegvesen", "Ca. 30 min", "Norske kjøretøydata."),
    (18, "Biluppgifter Sverige", "Parkering", "Biluppgifter.se", "Etter SVV uten treff", "Svenske kjøretøydata og backlog."),
    (19, "Tjekbil Danmark", "Parkering", "Tjekbil.dk", "Etter svensk kontroll", "Danske kjøretøydata."),
    (20, "Koble parkering/Sun2", "Koble", "parking_sun_linker", "Ca. 10 min", "Kandidater der samme bil og Sun2-ID gjentas."),
    (21, "OwnTracks Lilletorget-besøk", "Vedlikehold", "OwnTracks", "Ca. 2 min", "Oppretter og oppdaterer stedbesøk."),
    (22, "Dørhendelser fra HC3", "Bygg og drift", "HC3", "Hendelsesstyrt", "Åpne/lukke-hendelser med sekundoppløsning."),
    (23, "HC3 dørstatus ved avvik", "Bygg og drift", "Fibaro10 poll", "Ca. 2 min ved behov", "Spør HC3 bare når lokal status er uventet."),
    (24, "Dreame logger", "Renhold", "Dreamehome", "Ca. 5 min", "Aqua10-status, historikk, planer og driftsdata."),
]

TECH_STACK = [
    ("Backend", "Python 3.12 · FastAPI 0.139 · Uvicorn", "Asynkron API-plattform med god støtte for integrasjoner, validering og bakgrunnsarbeid."),
    ("Data", "PostgreSQL · SQLAlchemy 2 · asyncpg", "Transaksjoner, tidsserier, relasjoner og pålitelig historikk. OwnTracks har separat database."),
    ("Gjeldende frontend", "React 19 · TypeScript · Vite · MUI 9 · Mantis", "Tretten fagapper, felles designsystem og én origin."),
    ("Mobil", "AppKit Mobile PWA", "Kjøpt mobilgrunnlag med safe-area, toppfelt, bunnnavigasjon og lyst/mørkt tema."),
    ("Proxy", "Caddy 2", "Reverse proxy, komprimering, sikkerhetsheadere og offentlig betrodde sertifikater."),
    ("Kjøring", "Docker Compose på QNAP", "Isolerte tjenester, enkel restart, deklarativ konfigurasjon og reproduksjon."),
    ("Varsling", "ntfy", "Enkel abonnementsløsning med dyplenker til relevante alarmflater."),
    ("Lokal AI", "PatchCore · CPU", "Visuell avviksdeteksjon lokalt uten å sende kamerabilder ut av installasjonen."),
    ("Kvalitet", "Pytest · TypeScript · Playwright · smoke-skript", "Tester API, builds, sikkerhet, routing, visuell funksjon og produksjonsdata."),
]

PORTS = [
    ("8094", "dreame_logger", "Lokal Dreame/Aqua10-status og API"),
    ("8095", "roborock_logger", "Lokal Roborock-status og API"),
    ("8096", "sun2_importer", "Sun2 dagsimport"),
    ("8097", "sun2_backfill_downloader", "Historisk Sun2-nedlasting"),
    ("8099", "sun2_session_scraper", "Ekstern port til intern 8098"),
    ("8109", "easypark_downloader", "EasyPark status og trigger"),
    ("8110", "fibaro10", "Fast gateway til aktiv blue/green web"),
    ("8111", "online_dashboard", "Begrenset dashboard"),
    ("8112", "maintenance_mobile", "Vedlikehold mobil"),
    ("8114", "alarm_mobile", "Alarm mobil og lokal reserve"),
    ("8125", "axis_camera_snapshots", "Axis status og API"),
    ("8126", "car_info_lookup", "Nordiske kjøretøyoppslag"),
    ("8127", "parking_sun_linker", "Koblingsmotor"),
    ("8128", "owntracks_service", "OwnTracks HTTP og web"),
    ("8130", "unifi_protect_events", "Protect Ledger og administrasjon"),
    ("8140", "visual_anomaly_service", "Kun internt Docker-nett"),
    ("8151-8158", "API-adaptere", "Omsetning til Koble, uten frontend"),
    ("8163", "lilletorget_kiosk", "Fast robotkiosk"),
    ("8170", "lilletorget_mantis", "Gjeldende Mantis-stack med tretten appbygg"),
    ("8081 / 8443", "fibaro10_proxy", "Tekniske reserveporter for HTTP/HTTPS"),
]

DATA_DOMAINS = [
    ("Parkering", "parkering · kjoretoy · kjoretoy_nokkeldata", "Parkeringstid, beløp, kjøretøy, eier-/registerdata, område og oppgjør."),
    ("Soling", "sun2_tanning_sessions · sun2_beds · sun2_members · sun2_product_sales · sun2_finance_settlements", "Timer, bilder, senger, medlemmer, produkter og finans."),
    ("Energi", "energy_fibaro_samples · energy_hourly_consumption · energy_circuits · energy_loads · hc3_meter_readings", "30-sekunders effekt, timesforbruk, kurser, målere og laster."),
    ("Bygg og drift", "utelys_* · ventilasjon_* · yr_forecast_samples · door_events · alarm_events", "Lys, klima, vifter, dører, avvik og alarmer."),
    ("Renhold", "roborock_robots · roborock_status_samples · roborock_clean_jobs · roborock_maps", "Robotregister, status, historikk, planer, forbruksmateriell og kart."),
    ("Plattform", "users · auth_sessions · import_job_status · import_job_runs · notification_outbox · operational_incident_reviews", "Brukere, SSO, datakildestatus, varsling og operatørkvitteringer."),
    ("OwnTracks", "separat PostgreSQL", "Enheter, lokasjoner, waypoints, hendelser og beregnede sonebesøk."),
]

FAILURE_MODES = [
    ("QNAP eller Docker stopper", "Alle lokale tjenester blir utilgjengelige.", "restart-policy, health-watch, nattbackup og dokumentert full restore."),
    ("Fibaro10 web-build feiler", "Brukerflatene kan ikke hente data.", "Blue/green lar gammel web fortsette; trafikk flyttes bare etter grønn health."),
    ("Worker stopper", "Importstatus eldes og kontroller/varsler uteblir.", "Egen worker-container, datakildegrenser og health-watch."),
    ("PostgreSQL utilgjengelig", "API og innlogging feiler.", "SELECT 1 health, pool pre-ping, SQL-dump og restore-test."),
    ("HC3 restart eller nettverksbrudd", "Realtime energi og hendelser får hull.", "Watchdog starter logger-scene igjen. Historisk realtime kan ikke rekonstrueres."),
    ("EasyPark pålogging utløper", "Nye parkeringer uteblir.", "Egen downloader-status, faste kjøringer, manuell trigger og varsling via datakilder."),
    ("Sun2 endrer side/API", "Timer, medlemmer eller salg stopper.", "Separat scraper, importstatus, råfiler og historisk backfill."),
    ("Kamera eller AI feiler", "Bilder eller visuell avviksanalyse mangler.", "Separat status, fast utsnitt, klassisk visuell sammenligning og AI som tillegg."),
    ("Ekstern API rate-limit", "Kjøretøyoppslag forsinkes.", "Kø, negativ cache, sekvens Norge-Sverige-Danmark og kontrollert retry."),
    ("Diskplass blir lav", "Imports, bilder og database kan stoppe.", "Volumkontroll hvert femte minutt, retention og ukentlig Docker-rydding."),
]

SOURCE_REFERENCES = [
    ("docker-compose.qnap.yml", "Autoritativ tjenestedefinisjon, porter, avhengigheter, volumes og healthchecks."),
    ("Caddyfile", "Domener, TLS, proxyregler, sikkerhetsheadere og intern tilgangsbegrensning."),
    ("main.py", "Fibaro10 datamodell, API, jobber, domenelogikk og varsling."),
    ("system_inventory.py", "Felles komponentregister for systemgrensesnitt og dokumentasjon."),
    ("import_jobs.py", "Datakilderegister, rytmer og operativ statuslogikk."),
    ("microapp_backend/", "Felles innlogging og runtime for fagappene."),
    ("../lilletorget-mantis/packages/platform/", "Gjeldende ruting, API-klient, kontrakter og fagvisninger."),
    ("../lilletorget-mantis/packages/mantis/", "Mantis-skall, MUI-tema og leverandørkomponenter."),
    ("packages/microapp-ui/", "Felles rammeverk for reservegenerasjonen."),
    ("packages/mobile-appkit/", "Felles AppKit-design for mobilflatene."),
    ("docs/systemoversikt.md", "Løpende systeminventar, webflater, data og backup."),
    ("docs/utviklingsoppsett.md", "Oppsett, deploy, Gmail-import, backup og restore."),
    ("docs/hc3-energi-oppsamlinger.md", "HC3 energiarkitektur, målere og watchdog."),
    ("docs/hc3-dorer.md", "Dørscener, poll ved avvik, romkobling og alarmhistorikk."),
]


def build_document() -> Path:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    s = styles()
    portrait_w, portrait_h = A4
    landscape_size = landscape(A4)

    doc = NumberedDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=22 * mm,
        rightMargin=22 * mm,
        topMargin=25 * mm,
        bottomMargin=21 * mm,
        title="Lilletorget systemarkitektur og teknisk dokumentasjon",
        author="Lilletorget / Codex",
        subject="Komplett teknisk dokumentasjon for Fibaro10-plattformen",
        creator="ReportLab",
    )

    cover_frame = Frame(0, 0, portrait_w, portrait_h, id="cover", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    body_frame = Frame(doc.leftMargin, doc.bottomMargin, portrait_w - doc.leftMargin - doc.rightMargin, portrait_h - doc.topMargin - doc.bottomMargin, id="body")
    landscape_frame = Frame(18 * mm, 20 * mm, landscape_size[0] - 36 * mm, landscape_size[1] - 43 * mm, id="landscape")
    doc.addPageTemplates(
        [
            PageTemplate(id="cover", pagesize=A4, frames=[cover_frame], onPage=cover_page),
            PageTemplate(id="body", pagesize=A4, frames=[body_frame], onPage=body_page),
            PageTemplate(id="landscape", pagesize=landscape_size, frames=[landscape_frame], onPage=landscape_page),
        ]
    )

    story: list[Flowable] = [CoverSpacer(), NextPageTemplate("body"), PageBreak()]

    story += [Paragraph("Dokumentkontroll", s["Heading1"])]
    story += [
        make_table(
            [
                ["Felt", "Verdi"],
                ["Dokument", "Lilletorget systemarkitektur og teknisk dokumentasjon"],
                ["Status", "Gjeldende oppsett i produksjon"],
                ["Produksjonsbuild", BUILD],
                ["Git-commit", COMMIT],
                ["Dokumentdato", GENERATED],
                ["Målgruppe", "Eier, utvikler, driftsansvarlig og person som skal gjenopprette løsningen"],
                ["Kilder", "Compose, Caddy, applikasjonskode, systeminventar, driftsdokumentasjon og live health"],
                ["Sensitivitet", "Intern. Dokumentet beskriver struktur og konfigurasjonskategorier, men inneholder ikke hemmelige verdier."],
            ],
            [42 * mm, 112 * mm],
            s,
            font_size=8,
        )
    ]
    story += [Spacer(1, 8), callout("Fasit og avgrensning", "Dokumentet beskriver den faktiske installasjonen ved dokumentdatoen. Operativ status i System -> Datakilder og /health?details=true er fasit dersom en tidsangivelse senere endres.", s, GOLD)]

    story += [PageBreak(), Paragraph("Innhold", s["TOCHeading"])]
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle("TOC1", fontName="Segoe-Semibold", fontSize=9.5, leading=14, leftIndent=0, firstLineIndent=0, textColor=NAVY, spaceBefore=3),
        ParagraphStyle("TOC2", fontName="Segoe", fontSize=8.2, leading=12, leftIndent=14, firstLineIndent=0, textColor=INK),
    ]
    story += [toc]

    story += [PageBreak(), Paragraph("1. Sammendrag", s["Heading1"])]
    story += [p("Lilletorget/Fibaro10 er en lokal-først drifts- og analyseplattform for soling, parkering, energi, bygg, vedlikehold, kamera og lokasjon. Plattformen kjører primært som Docker-containere på én QNAP, men er delt i domeneapper og innsamlere slik at hver del kan bygges, testes og restartes uavhengig.", s["Body"])]
    story += [
        info_cards(
            [
                ("Produksjon", f"Build {BUILD}", f"Commit {COMMIT}"),
                ("Brukerapper", "11", "Mantis-appidentiteter"),
                ("Datakilder", "24", "Separate kilder med friskhetsstatus"),
            ],
            s,
        ),
        Spacer(1, 10),
    ]
    story += [p("Den gjeldende appstakken består av tretten Mantis-apper under ny.lilletorget.net. Alle statiske appbygg leveres fra Nginx på port 8170 og deler MUI/Mantis-design, API-klient og én databasesesjon for innlogging. Fibaro10-kjernen er fortsatt det sentrale API- og datalaget, mens fagadapterne på 8151-8158 oversetter forespørsler til kjernen.", s["Body"])]
    story += [p("Innsamling er flyttet ut i separate tjenester der det gir verdi: EasyPark, Sun2, Axis, UniFi Protect, kjøretøyoppslag, Roborock, Dreame, OwnTracks og koblingsmotoren kjører ved siden av kjernen. Denne oppdelingen reduserer påvirkning mellom integrasjoner og gjør feil enklere å lokalisere.", s["Body"])]
    story += [Paragraph("Viktigste arkitekturvalg", s["Heading2"])]
    for text in [
        "Én sentral PostgreSQL-database for forretningsdata og en separat PostgreSQL-database for OwnTracks.",
        "Felles FastAPI-kjerne og dedikert worker, med blue/green web-utrulling.",
        "Elleve domeneorienterte Mantis-apper med egne statiske bygg, men felles image, UI-pakke, tema, navigasjon og innlogging.",
        "Caddy med offentlig betrodde sertifikater. Interne domener finnes i offentlig DNS, men peker til privat IP og avvises utenfor privat nett.",
        "Separate innsamlere for ustabile eller tunge integrasjoner, med datakildestatus lagret i kjernen.",
        "Nattlig full backup med separate SQL-dumper, checksums og gjenopprettingstest.",
    ]:
        story.append(bullet(text, s))

    story += [NextPageTemplate("landscape"), PageBreak(), Paragraph("2. Samlet arkitekturbilde", s["Heading1"]), architecture_overview(), NextPageTemplate("body"), PageBreak()]
    story += [Paragraph("2.1 Hvordan bildet skal leses", s["Heading2"])]
    story += [p("Brukerflatene er separate applikasjoner, men de fleste henter data og tilgangskontekst fra Fibaro10. Innsamlerne skriver enten gjennom Fibaro10 API eller til en kontrollert databasekobling. Fysiske enheter og eksterne systemer ligger nederst i kjeden; de skal aldri være nødvendige for å rendre en vanlig side i sanntid.", s["Body"])]
    story += [callout("Kjernen i én setning", "Mikroappene presenterer data, Fibaro10 eier domenelogikken og hoveddatabasen, mens separate tjenester sørger for at data kommer inn pålitelig.", s, BLUE)]
    story += [Paragraph("2.2 Arkitekturprinsipper", s["Heading2"])]
    principles = [
        ("Lokal-først", "Kritiske data, integrasjoner og AI kjøres på QNAP eller lokalt nett. Eksterne tjenester brukes som datakilder, ikke som eneste lagringssted."),
        ("Kildebasert historikk", "Rå hendelser og importresultater lagres før presentasjon og analyse. Beregnede verdier kan dermed kontrolleres mot kilden."),
        ("Tynn brukerflate", "Fagappene inneholder visning og lokal interaksjon, men forretningsregler og skriving ligger primært i Fibaro10 API."),
        ("Isolerte integrasjoner", "Tjenester som EasyPark, Sun2, kamera, Roborock og Dreame har egne prosesser, healthchecks og restart-policy."),
        ("Reversibel deploy", "Ny web-build verifiseres i inaktivt spor. Trafikken flyttes først når helsesjekken er grønn."),
        ("Synlig datakvalitet", "Alle viktige datakilder har nummer, status, siste suksess, neste forventning og feildetaljer."),
    ]
    story.append(make_table([["Prinsipp", "Praktisk betydning"], *principles], [38 * mm, 116 * mm], s, font_size=8))

    story += [PageBreak(), Paragraph("3. Brukerflater og applikasjoner", s["Heading1"])]
    story += [p("Den daglige arbeidsflaten er delt etter fagområde. Brukeren opplever ett samlet system gjennom samme origin, appbytte, felles designsystem og delt innlogging, mens hver app beholder egen base path og statisk inngang.", s["Body"])]
    story += [Paragraph("3.1 Interne hovedflater", s["Heading2"])]
    story.append(make_table([["Flate", "Adresse", "Port", "Formål"], *WEB_APPS], [28 * mm, 52 * mm, 15 * mm, 59 * mm], s, font_size=7.2))
    story += [Paragraph("3.2 Mobil- og spesialflater", s["Heading2"])]
    story.append(make_table([["Flate", "Adresse", "Port", "Formål"], *SPECIAL_APPS], [30 * mm, 52 * mm, 15 * mm, 57 * mm], s, font_size=7.2, header_color=NAVY_2))
    story += [Paragraph("3.3 Ansvarsdeling i frontend", s["Heading2"])]
    story += [
        bullet("<b>Mantis:</b> gjeldende brukerflate med React, TypeScript, MUI og tretten apper under ny.lilletorget.net.", s),
        bullet("<b>Fibaro10 og adapterne:</b> produksjonskritisk API-lag uten egne desktopflater.", s),
        bullet("<b>Mobilappene:</b> AppKit Mobile PWA med mobilspesifikke arbeidsflyter, safe-area og bunnnavigasjon.", s),
        bullet("<b>Serverrendret innlogging:</b> lett felles side som lastes før React-bundlene og gir samme sesjon i alle appene.", s),
    ]

    story += [PageBreak(), Paragraph("4. Tjenestelandskap", s["Heading1"])]
    story += [p("Compose-oppsettet består av kjernen, brukerrettede apper, datainnsamlere, kamera/AI og infrastrukturtjenester. Enkelte tjenester som EasyPark, Roborock og Dreame har egen compose for å unngå unødvendig restart når hovedstacken bygges.", s["Body"])]
    story.append(make_table([["Komponent", "Område", "Kritikalitet", "Ansvar"], *COMPONENTS], [45 * mm, 30 * mm, 22 * mm, 57 * mm], s, font_size=6.8))

    story += [NextPageTemplate("landscape"), PageBreak(), Paragraph("5. Innlogging, nettverk og forespørselsflyt", s["Heading1"]), request_auth_diagram(), NextPageTemplate("body"), PageBreak()]
    story += [Paragraph("5.1 Felles innlogging", s["Heading2"])]
    story += [p("Mantis, Fibaro10 og fagadapterne bruker én opak sesjonscookie med navnet lilletorget_session. Cookien gjelder for .lilletorget.net og har Secure, HttpOnly og SameSite=Lax. Nettleseren får ikke passordet eller komplette brukerdata i cookien; den inneholder bare en tilfeldig sesjonsreferanse som slås opp i hoveddatabasen.", s["Body"])]
    story += [p("Utlogging fra én av appene tilbakekaller databasesesjonen og fjerner den delte cookien. Direkte utvikling via localhost eller IP bruker vertsspesifikk cookie fordi domenecookie ikke passer utenfor lilletorget.net.", s["Body"])]
    story += [Paragraph("5.2 DNS, TLS og intern tilgang", s["Heading2"])]
    for text in [
        "De interne appnavnene finnes i offentlig DNS, men peker til privat QNAP-adresse. Dette gjør at samme navn kan brukes over LAN og VPN.",
        "TLS-sertifikatene er offentlig betrodde og hentes via DNS-01. Appene trenger derfor verken lokal CA eller sertifikatinstallasjon på klientene.",
        "Caddy sin internal_app-regel avviser klienter utenfor private_ranges med 404, selv om domenenavnet er offentlig.",
        "Online, OwnTracks og de valgte mobilflatene har egne proxyregler. De må sikres med sine respektive bruker-, token- eller applikasjonskontroller.",
        "Caddy legger på HSTS, nosniff og streng referrer-policy og skjuler Server-headeren.",
    ]:
        story.append(bullet(text, s))
    story += [Paragraph("5.3 Tillitsgrenser", s["Heading2"])]
    story.append(make_table(
        [
            ["Grense", "Tillatt trafikk", "Kontroll"],
            ["Intern nettleser -> Caddy", "HTTPS til lilletorget.net-domener", "Privat IP/VPN, TLS og sikkerhetsheadere"],
            ["Caddy -> app", "Kun definert reverse proxy", "Docker-nett og eksplisitt port"],
            ["App -> Fibaro10", "HTTP internt i Docker-nettet", "Sesjon eller tjenestenøkkel"],
            ["Innsamler -> ingest", "Avgrensede API-endepunkter", "Token/IP/validering etter tjeneste"],
            ["Fibaro10 -> eksternt API", "HTTPS eller lokalt API", "Nøkler i .env, timeout og retry"],
        ], [40 * mm, 58 * mm, 56 * mm], s, font_size=7.5))

    story += [NextPageTemplate("landscape"), PageBreak(), Paragraph("6. Dataflyt og integrasjoner", s["Heading1"]), data_flow_diagram(), NextPageTemplate("body"), PageBreak()]
    story += [Paragraph("6.1 Datakilder", s["Heading2"])]
    story += [p("Health-endepunktet oppsummerer 24 separate datakilder. Tabellen under beskriver normal rytme og ansvar. Dreame-kilden kan stå som klargjort og vente på konto uten at Aqua10-verdier fabrikkeres.", s["Body"])]
    story.append(make_table([["Nr", "Datakilde", "Kategori", "Kilde", "Rytme", "Innhold"], *DATA_SOURCES], [9 * mm, 38 * mm, 24 * mm, 28 * mm, 25 * mm, 40 * mm], s, font_size=6.3))
    story += [Paragraph("6.2 Parkering", s["Heading2"])]
    story += [p("EasyPark-downloaderen henter i går og i dag på faste tidspunkt 08:00, 10:00, 12:00, 14:00, 16:00, 18:00, 20:00 og 23:00. Etter vellykket import lagres ny parkeringsprognose. Norske kjøretøy kontrolleres først hos SVV; manglende treff sendes videre til svensk og deretter dansk tjeneste. Historiske Flowbird/Park Nordic-perioder før 2026 krever eget oppgjørsgrunnlag.", s["Body"])]
    story += [Paragraph("6.3 Soling og bilder", s["Heading2"])]
    story += [p("Sun2-scraperen henter enkelttimer løpende og senger/medlemmer sjeldnere. Dags- og månedsjobber brukes til avstemming av romsummer, produkter og finansoppgjør. Axis tar bilder hvert femte sekund i åpningstidsvinduet. Fem kandidater rundt valgt tidspunkt kobles til soltimen, og brukeren kan velge nytt hovedbilde uten å forlate timen.", s["Body"])]
    story += [Paragraph("6.4 Energi, dører og automasjon", s["Heading2"])]
    story += [p("HC3 sender realtime effekt hvert 30. sekund. Forbruk beregnes fra disse målingene; akkumulert kWh beholdes som kontrollverdi fordi enkelte undermålere kan nullstilles. Dørhendelser sendes hendelsesstyrt fra HC3. Fibaro10 spør bare HC3 direkte når siste lokale status er uventet, slik at løsningen unngår unødvendig polling.", s["Body"])]

    story += [PageBreak(), Paragraph("7. Datamodell og lagring", s["Heading1"])]
    story += [p("Hoveddatabasen lagrer både forretningshistorikk, konfigurasjon, importstatus og sesjoner. Data er organisert per domene, men kan analyseres samlet fordi tidspunkter, kilde og identiteter bevares. OwnTracks er fysisk skilt ut i egen PostgreSQL for å holde lokasjonstrafikk og livssyklus uavhengig.", s["Body"])]
    story.append(make_table([["Domene", "Viktige tabeller / lagring", "Hva de representerer"], *DATA_DOMAINS], [28 * mm, 68 * mm, 58 * mm], s, font_size=7.2))
    story += [Paragraph("7.1 Tids- og kildeprinsipper", s["Heading2"])]
    for text in [
        "Applikasjonen bruker Europe/Oslo for visning og normalisering, men bevarer kildens semantikk ved import.",
        "Sun2- og Elvia-filer tolkes som lokal kildetid. Yr og HC3 vises i Europe/Oslo.",
        "Sammenligninger bruker siste felles oppdateringstid, særlig fordi parkering importeres sjeldnere enn soling.",
        "Originalfiler, oppgjørsbilag, rå hendelser og bildereferanser beholdes slik at beregninger kan etterprøves.",
        "Tekniske suksesslogger har retention, mens virksomhetsdata som parkering, soling, energi, dører og alarmer ikke slettes automatisk.",
    ]:
        story.append(bullet(text, s))

    story += [PageBreak(), Paragraph("8. Teknologistack og begrunnelse", s["Heading1"])]
    story += [p("Teknologiene er valgt for å balansere rask videreutvikling, lokal drift og enkel gjenoppretting. Plattformen er ikke en full distribuert mikrotjenestearkitektur: den har separate prosesser og apper, men deler fortsatt hoveddatabase og domenekjerne. Dette er bevisst og reduserer kompleksitet på én QNAP.", s["Body"])]
    story.append(make_table([["Lag", "Teknologi", "Hvorfor dette er valgt"], *TECH_STACK], [32 * mm, 56 * mm, 66 * mm], s, font_size=7.4))
    story += [Paragraph("8.1 Bevisste avgrensninger", s["Heading2"])]
    story += [
        bullet("Det brukes ikke Kubernetes. Docker Compose er tilstrekkelig på én vert og er enklere å forstå og gjenopprette.", s),
        bullet("Det brukes ikke Redis/Celery som sentral kø. Jobber ligger i dedikert worker eller separate tjenester. Det reduserer komponentantallet, men krever idempotente jobber og databasebasert status.", s),
        bullet("Mantis-appene eier ikke hver sin forretningsdatabase. De er domenefronter over felles API, noe som unngår distribuert datakonsistens på én QNAP.", s),
        bullet("Mantis/MUI er gjeldende designsystem. Mobilflatene har et separat, mobiltilpasset AppKit-grunnlag.", s),
    ]
    story += [callout("Nåværende vurdering", "Teknologistacken passer installasjonens størrelse. Den viktigste videre arkitekturjobben er å fortsette å trekke avgrenset domenelogikk ut av main.py, uten å splitte data og drift raskere enn det gir reell gevinst.", s, GREEN)]

    story += [NextPageTemplate("landscape"), PageBreak(), Paragraph("9. Utrulling og kvalitetskontroll", s["Heading1"]), deployment_diagram(), NextPageTemplate("body"), PageBreak()]
    story += [Paragraph("9.1 Standard flyt", s["Heading2"])]
    deploy_steps = [
        ("1", "Lokal kontroll", "Python-kompilering, pytest, TypeScript, alle frontend-builds, CSS-, bundle- og sikkerhetsrevisjon."),
        ("2", "Git", "Endringene committes og pushes til main. Commit-ID brukes i buildmetadata."),
        ("3", "Pre-deploy backup", "Runtimefiler og berørte data kopieres før containerendringer."),
        ("4", "Byggeplan", "Git-diff avgjør hvilke tjenester som bygges. Ukjent påvirkning gir full rebuild."),
        ("5", "Blue/green", "Ny Fibaro10 web bygges i inaktivt spor og testes før Caddy-gatewayen peker om."),
        ("6", "Worker", "Ny worker startes etter godkjent trafikkbytte slik at jobber ikke dobbelkjøres."),
        ("7", "Verifikasjon", "Containere, datakilder, 127 Mantis-ruter, 228 reserveruter og produksjonssmoke."),
    ]
    story.append(make_table([["Trinn", "Kontroll", "Innhold"], *deploy_steps], [13 * mm, 38 * mm, 103 * mm], s, font_size=7.6))
    story += [Paragraph("9.2 Build- og endringsspor", s["Heading2"])]
    story += [p("Fibaro10 har et globalt buildnummer. Mantis ligger i eget Git-repo og deployes som tidsstemplet, uforanderlig release. Buildloggen registrerer bestilling, overskrift, berørte applikasjoner og teknisk beskrivelse. Commit-ID og image i health gjør det mulig å kontrollere at GitHub, QNAP og brukerflaten viser samme kode.", s["Body"])]

    story += [NextPageTemplate("landscape"), PageBreak(), Paragraph("10. Lagring, backup og gjenoppretting", s["Heading1"]), storage_backup_diagram(), NextPageTemplate("body"), PageBreak()]
    story += [Paragraph("10.1 Lagringsmodell", s["Heading2"])]
    storage_rows = [
        ("QNAP appområde", "/share/CACHEDEV1_DATA/Public/containerdata/fibaro10", "Repo, compose og vanlig runtime."),
        ("Hoveddatabase", "DATABASE_URL", "Ekstern/egen PostgreSQL for Fibaro10-data."),
        ("OwnTracks database", "owntracks_postgres volume", "PostgreSQL 17 i stacken."),
        ("Axis buffer", "AXIS_HOST_SNAPSHOT_DIR", "Eget arkivvolum, normalt 35 dagers buffer."),
        ("Protect snapshots", "UNIFI_PROTECT_HOST_SNAPSHOT_DIR", "SSD-arkiv for kontrollbilder."),
        ("Visuell AI", "VISUAL_AI_HOST_DATA_DIR", "Modeller og kalibreringsmetadata på SSD."),
        ("Backup", "/share/CACHEDEV3_DATA/fibaro10_archive", "Nattbackup, full restore og deploy-backuper."),
    ]
    story.append(make_table([["Område", "Plassering / variabel", "Innhold"], *storage_rows], [35 * mm, 64 * mm, 55 * mm], s, font_size=7.5))
    story += [Paragraph("10.2 Hva nattbackupen inneholder", s["Heading2"])]
    for text in [
        "Separate validerte SQL-dumper av Fibaro10- og OwnTracks-databasene.",
        "Alle runtime-.env-filer og konfigurasjon som trengs for å starte stackene.",
        "EasyPark-, Sun2-, Roborock-, Dreame-, Protect- og AI-data som ikke ligger i databasen.",
        "Repo-/oppsettreferanser, BACKUP_MANIFEST.txt og CHECKSUMS.sha256.",
        "Axis-arkivet tas ikke med i sin helhet. Bilder som er knyttet til soltimer ligger i PostgreSQL og følger databasedumpen.",
    ]:
        story.append(bullet(text, s))
    story += [Paragraph("10.3 Gjenoppretting på ny QNAP", s["Heading2"])]
    restore_steps = [
        ("1", "Klargjør volumer, nettverk og Container Station/Docker."),
        ("2", "Hent repo fra GitHub eller restore-pakken og legg det i forventet appområde."),
        ("3", "Gjenopprett .env, sertifikatdata, runtimekataloger og eventuelle tjenestespesifikke nøkler."),
        ("4", "Opprett PostgreSQL og importer Fibaro10-dumpen. Start OwnTracks PostgreSQL og importer egen dump."),
        ("5", "Gjenopprett AI-, Protect-, Roborock-, Dreame- og importerdata til dokumenterte mount-punkter."),
        ("6", "Start compose-stackene og verifiser database, proxy, core, worker og datainnsamlere i den rekkefølgen."),
        ("7", "Kontroller DNS/privat IP, TLS, 24 datakilder, Mantis-smoke og innlogging på tvers av appene."),
    ]
    story.append(make_table([["Trinn", "Handling"], *restore_steps], [14 * mm, 140 * mm], s, font_size=7.8))

    story += [PageBreak(), Paragraph("11. Drift, overvåking og varsling", s["Heading1"])]
    story += [Paragraph("11.1 Health og readiness", s["Heading2"])]
    story += [p("Hver brukerrettede tjeneste har /health, og fagappene har også /ready som kontrollerer forbindelsen til Fibaro10. Hovedhealth kjører SELECT 1 mot databasen og oppsummerer alle 24 datakilder. Docker-health brukes i tillegg for containernivå og oppstartsrekkefølge.", s["Body"])]
    story += [Paragraph("11.2 Operativt hendelsessenter", s["Heading2"])]
    for text in [
        "Feilede eller for gamle datakilder blir operative hendelser.",
        "Aktive døralarmer, pullert-/trappeavvik og fastlåste ntfy-meldinger samles i samme kontrollflate.",
        "Operatør kan kvittere og skrive notat uten å overskrive kildens opprinnelige status.",
        "Nattbackup og full restore-backup overvåkes separat gjennom skrivebeskyttede statusmounts.",
        "QNAP health-watch kontrollerer webtjenester, backuper og ledig plass på Vol1-Vol3 hvert femte minutt.",
    ]:
        story.append(bullet(text, s))
    story += [Paragraph("11.3 Varsling", s["Heading2"])]
    story += [p("ntfy brukes til dør-, pullert-, trappe-, lys-, ventilasjons- og tilgangsvarsler. Utsending skjer via databasebasert outbox med status for pending, sending, retrying og sent. Alarmappen åpnes via dyplenke slik at varselet leder direkte til riktig kontrollflate.", s["Body"])]
    story += [Paragraph("11.4 Retention", s["Heading2"])]
    retention = [
        ("Vellykkede tilgangslogger", "90 dager"),
        ("Feilede tilgangslogger", "365 dager"),
        ("Vellykkede importkjøringer", "90 dager"),
        ("Feilede importkjøringer", "365 dager"),
        ("Sendte varslinger", "30 dager"),
        ("Utløpte autentiseringssesjoner", "30 dager"),
        ("Forretningsdata", "Ingen automatisk sletting"),
    ]
    story.append(make_table([["Datatype", "Retention"], *retention], [100 * mm, 54 * mm], s, font_size=8))

    story += [PageBreak(), Paragraph("12. Feilscenarier og robusthet", s["Heading1"])]
    story += [p("Løsningen har flere beskyttelseslag, men QNAP og hoveddatabasen er fortsatt sentrale avhengigheter. Tabellen viser de viktigste kjente feilscenariene og hvordan de begrenses.", s["Body"])]
    story.append(make_table([["Scenario", "Konsekvens", "Beskyttelse / respons"], *FAILURE_MODES], [38 * mm, 49 * mm, 67 * mm], s, font_size=7.3))
    story += [Paragraph("12.1 Gjenstående enkeltpunkter", s["Heading2"])]
    for text in [
        "Én fysisk QNAP er single point of failure inntil restore er utført på ny maskin.",
        "Hoveddatabasen er felles for mange domener. Feil eller låser kan påvirke flere flater samtidig.",
        "Eksterne kilder kan endre innlogging eller HTML uten forvarsel, særlig EasyPark og Sun2.",
        "Realtime energi kan ikke backfylles etter HC3-nedetid. Watchdog reduserer varighet, men kan ikke rekonstruere samples.",
        "Offentlig tilgjengelige mobilruter krever fortsatt jevnlig kontroll av autentisering og eksponerte API-stier.",
    ]:
        story.append(bullet(text, s))

    story += [PageBreak(), Paragraph("13. Konfigurasjon og hemmeligheter", s["Heading1"])]
    story += [p("Konfigurasjon ligger i versjonerte example-filer og runtime-.env på QNAP. Faktiske passord, API-nøkler, tokens og database-URL-er skal ikke ligge i Git. Backupen inkluderer runtimefilene fordi målet er full gjenoppretting, og må derfor behandles som sensitiv.", s["Body"])]
    config_groups = [
        ("Kjerne og database", "DATABASE_URL, APP_BUILD, APP_COMMIT, prosessrolle og background tasks."),
        ("Felles innlogging", "Cookie-navn/domene, sesjonslevetid og brukerdata i hoveddatabasen."),
        ("HC3", "Base-URL, bruker/passord, watchdog og device-/sceneoppsett."),
        ("EasyPark/Gmail", "Gmail IMAP/app-passord, kjøreplan, recent-days og importtoken."),
        ("Sun2", "Pålogging, scraper-rytme, dataområder og dagsfilkatalog."),
        ("Kamera", "Axis URL/credentials, Protect API-key, kamera-ID-er, snapshotkatalog og AI-token."),
        ("Kjøretøy", "SVV API-key, Biluppgifter/Tjekbil-parametre, retry og backlog."),
        ("Varsling", "ntfy base-URL, topics og dyplenker."),
        ("OwnTracks", "HTTP-token, PostgreSQL URL, offentlig base-URL og nøyaktighetsgrense."),
        ("Backup", "Volumstier, replica target, retention og statuskataloger."),
    ]
    story.append(make_table([["Konfigurasjonsgruppe", "Eksempler og ansvar"], *config_groups], [43 * mm, 111 * mm], s, font_size=7.6))
    story += [callout("Sikkerhetsregel", "Runtimebackupen inneholder nok informasjon til å starte løsningen på nytt og må derfor sikres minst like godt som den operative QNAP-en.", s, RED)]

    story += [PageBreak(), Paragraph("14. Videreutvikling og endringsregler", s["Heading1"])]
    story += [Paragraph("14.1 Hvor ny funksjonalitet skal ligge", s["Heading2"])]
    placement = [
        ("Ny visning i ett fagområde", "Riktig Mantis-app", "Bruk packages/platform og eksisterende API før ny backend."),
        ("Ny forretningsregel", "Fibaro10 API eller avgrenset domenemodul", "Regelen skal kunne testes uten frontend."),
        ("Ny ustabil integrasjon", "Egen innsamlertjeneste", "Egen health, timeout, retry og importstatus."),
        ("Ny bakgrunnsjobb", "Worker hvis tett på kjernen, ellers egen tjeneste", "Jobben skal være idempotent og rapportere kjøring."),
        ("Ny mobil arbeidsflyt", "Eksisterende relevant mobilapp", "Ikke kopier desktop-siden; optimaliser for én hånd og få felter."),
        ("Ny datakilde", "Registrer i import_jobs", "Gi nummer, forklaring, rytme, forventet ferskhet og feilmelding."),
    ]
    story.append(make_table([["Endring", "Plassering", "Krav"], *placement], [42 * mm, 49 * mm, 63 * mm], s, font_size=7.5))
    story += [Paragraph("14.2 Kriterier før en tjeneste skilles helt ut", s["Heading2"])]
    for text in [
        "Den har tydelig eierskap til egne data og API-kontrakt.",
        "Den har egen feil- og skaleringsprofil som faktisk gir gevinst ved separat drift.",
        "Den kan deployes uten synkron databaseendring i flere tjenester.",
        "Backup, observability, autentisering og restore er definert før produksjonsdeling.",
        "Det er akseptert hvem som eier data ved avvik og hvordan historikk migreres.",
    ]:
        story.append(bullet(text, s))

    story += [PageBreak(), Paragraph("15. Port- og ruteoversikt", s["Heading1"])]
    story += [p("Domener er foretrukket for brukertrafikk. Portene brukes til lokal reserve, helsesjekk, deploy og feilsøking. Direkte porter skal ikke publiseres uten at proxy- og autentiseringsmodellen er vurdert.", s["Body"])]
    story.append(make_table([["Port", "Tjeneste", "Bruk"], *PORTS], [28 * mm, 56 * mm, 70 * mm], s, font_size=7.6))

    story += [PageBreak(), Paragraph("16. Driftsrutiner", s["Heading1"])]
    routines = [
        ("Daglig", "Kontroller System -> Datakilder ved varsel; se aktive alarmer; bekreft neste EasyPark-import."),
        ("Ukentlig", "Se statusrapport, backupalder, diskplass, tregeste ruter og utestående hendelser."),
        ("Månedlig", "Importer Elvia, kontroller parkering- og soloppgjør og vurder avvik mot intern omsetning."),
        ("Ved deploy", "Kjør lokal kontroll, oppdater buildlogg, push, selektiv deploy og full live smoke."),
        ("Ved HC3-restart", "Bekreft at energi-, lys-, ventilasjons- og dørlogger kommer tilbake; watchdog hjelper energiscenen."),
        ("Ved ny datakilde", "Dokumenter avhengigheter, rytme, retry, eier, statusgrense, datamodell og restore."),
        ("Ved diskvarsel", "Kontroller bildearkiv, deploybackuper og Docker build-cache før sletting av virksomhetsdata vurderes."),
        ("Kvartalsvis", "Kjør full restore-verifikasjon, kontroller sertifikatkjede og gjennomgå offentlig eksponerte ruter."),
    ]
    story.append(make_table([["Frekvens / hendelse", "Rutine"], *routines], [42 * mm, 112 * mm], s, font_size=7.8))

    story += [PageBreak(), Paragraph("17. Kildedokumenter", s["Heading1"])]
    story += [p("Denne håndboken sammenfatter informasjon fra følgende versjonerte kilder. De er også naturlige inngangspunkter ved feilsøking eller endring.", s["Body"])]
    story.append(make_table([["Kilde", "Ansvar"], *SOURCE_REFERENCES], [57 * mm, 97 * mm], s, font_size=7.4))
    story += [Paragraph("17.1 Verifikasjonskrav ved dokumentuttak", s["Heading2"])]
    verification = [
        ("Fibaro10", f"Build {BUILD}, commit {COMMIT}"),
        ("Database", "SELECT 1 og migreringskontroll skal være OK"),
        ("Datakilder", "Aktuell status leses i System -> Datakilder"),
        ("Varslingskø", "Aktuell status leses i Operasjonssentral/System"),
        ("Backend", "Full pytest og berørte tjenestetester skal være grønne"),
        ("Mantis", "Build, verify og produksjonssmoke skal være grønne"),
        ("Ruter", "127 Mantis-ruter og 228 adapterruter inngår i kontrollgrunnlaget"),
    ]
    story.append(make_table([["Kontroll", "Resultat"], *verification], [55 * mm, 99 * mm], s, font_size=8))

    story += [PageBreak(), Paragraph("18. Ordliste", s["Heading1"])]
    glossary = [
        ("Blue/green", "To web-spor der ett er aktivt og ett kan bygges/testes før trafikkbytte."),
        ("Datakilde", "Navngitt og nummerert import- eller ingestjobb med status og forventet rytme."),
        ("Fagapp / mikroapp", "Separat appidentitet for ett domene som normalt bruker Fibaro10 API."),
        ("Ingest", "Kontrollert mottak og validering av data fra en annen tjeneste eller fysisk enhet."),
        ("Mantis", "Kjøpt React/MUI-designgrunnlag for den gjeldende brukerflaten."),
        ("Outbox", "Databasetabell som holder varslinger til de er sendt eller retryet."),
        ("PatchCore", "Lokal modell for å oppdage visuelle avvik i faste kamerautsnitt."),
        ("PWA", "Webapp med manifest og mobiltilpasset installasjon/opplevelse."),
        ("Readiness", "Kontroll av at en app både kjører og kan nå nødvendige underliggende tjenester."),
        ("SSO", "Én innlogging og felles sesjon på tvers av lilletorget.net-appene."),
        ("Worker", "Prosess som kjører bakgrunnsjobber uten å servere vanlig webtrafikk."),
    ]
    story.append(make_table([["Begrep", "Forklaring"], *glossary], [40 * mm, 114 * mm], s, font_size=7.8))
    story += [Spacer(1, 14), HRFlowable(width="100%", thickness=0.7, color=GOLD), Spacer(1, 8)]
    story += [p("Dokumentet er laget for å gjøre løsningen forståelig og gjenopprettbar uten å være avhengig av muntlig historikk. Når arkitekturen endres, bør systemoversikt, compose, datakilderegister og denne PDF-en oppdateres i samme build.", s["Body"])]

    doc.multiBuild(story)
    return OUTPUT


if __name__ == "__main__":
    path = build_document()
    print(path)
