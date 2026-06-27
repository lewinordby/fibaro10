from datetime import datetime
from typing import Any, Optional
import re

from fastapi.responses import StreamingResponse


def pdf_literal(value: Any) -> bytes:
    text_value = "" if value is None else str(value)
    raw = text_value.encode("cp1252", errors="replace")
    out = bytearray()
    out.append(ord("("))
    for byte in raw:
        if byte in (40, 41, 92):
            out.append(92)
            out.append(byte)
        elif byte < 32 or byte > 126:
            out.extend(f"\\{byte:03o}".encode("ascii"))
        else:
            out.append(byte)
    out.append(ord(")"))
    return bytes(out)


def pdf_text(x: float, y: float, text_value: Any, size: float = 8, bold: bool = False) -> bytes:
    font = "F2" if bold else "F1"
    return b"BT /%b %.2f Tf 1 0 0 1 %.2f %.2f Tm %b Tj ET\n" % (
        font.encode("ascii"),
        size,
        x,
        y,
        pdf_literal(text_value),
    )


def pdf_line(x1: float, y1: float, x2: float, y2: float, gray: float = 0.82, width: float = 0.45) -> bytes:
    return f"{gray:.2f} G {width:.2f} w {x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S\n".encode("ascii")


def pdf_fill_rect(x: float, y: float, width: float, height: float, gray: float = 0.96) -> bytes:
    return f"{gray:.2f} g {x:.2f} {y:.2f} {width:.2f} {height:.2f} re f 0 g\n".encode("ascii")


def wrap_pdf_text(value: Any, max_chars: int) -> list[str]:
    text_value = re.sub(r"\s+", " ", "" if value is None else str(value)).strip()
    if not text_value:
        return ["-"]
    words = text_value.split(" ")
    lines: list[str] = []
    current = ""
    for word in words:
        if len(word) > max_chars:
            if current:
                lines.append(current)
                current = ""
            for index in range(0, len(word), max_chars):
                lines.append(word[index:index + max_chars])
            continue
        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or ["-"]


def assemble_pdf(page_streams: list[bytes], page_width: float, page_height: float) -> bytes:
    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        4: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
    }
    kids = []
    next_id = 5
    for stream in page_streams:
        page_id = next_id
        content_id = next_id + 1
        next_id += 2
        kids.append(f"{page_id} 0 R")
        objects[page_id] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_width:.2f} {page_height:.2f}] "
            f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {content_id} 0 R >>"
        ).encode("ascii")
        objects[content_id] = b"<< /Length %d >>\nstream\n%b\nendstream" % (len(stream), stream)
    objects[2] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(kids)} >>".encode("ascii")

    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets: dict[int, int] = {}
    for object_id in sorted(objects):
        offsets[object_id] = len(pdf)
        pdf.extend(f"{object_id} 0 obj\n".encode("ascii"))
        pdf.extend(objects[object_id])
        pdf.extend(b"\nendobj\n")
    xref_at = len(pdf)
    max_id = max(objects)
    pdf.extend(f"xref\n0 {max_id + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for object_id in range(1, max_id + 1):
        pdf.extend(f"{offsets.get(object_id, 0):010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {max_id + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)


def build_table_pdf(
    title: str,
    subtitle: str,
    columns: list[dict[str, Any]],
    rows: list[list[Any]],
    generated_at: Optional[datetime] = None,
) -> bytes:
    page_width = 841.89
    page_height = 595.28
    margin = 28.0
    header_height = 74.0
    footer_height = 18.0
    line_height = 9.5
    body_size = 7.4
    header_size = 7.0
    available_width = page_width - margin * 2
    scale = available_width / sum(float(column["width"]) for column in columns)
    col_widths = [float(column["width"]) * scale for column in columns]
    generated_label = f"Generert {(generated_at or datetime.now()).strftime('%d.%m.%Y %H:%M')}"

    def draw_page_header(page_num: int) -> tuple[bytearray, float]:
        content = bytearray()
        y = page_height - margin
        content.extend(pdf_text(margin, y - 5, title, 16, True))
        content.extend(pdf_text(margin, y - 23, subtitle, 8.4, False))
        content.extend(pdf_text(page_width - margin - 118, y - 5, generated_label, 7.5, False))
        content.extend(pdf_text(page_width - margin - 44, margin - 4, f"Side {page_num}", 7.0, False))
        table_top = page_height - margin - header_height
        content.extend(pdf_fill_rect(margin, table_top - 15, available_width, 18, 0.95))
        x = margin
        for column, width in zip(columns, col_widths):
            content.extend(pdf_text(x + 3, table_top - 8, column["label"], header_size, True))
            x += width
        content.extend(pdf_line(margin, table_top - 17, page_width - margin, table_top - 17, 0.78, 0.55))
        return content, table_top - 24

    page_streams: list[bytes] = []
    page_num = 1
    content, y = draw_page_header(page_num)
    bottom = margin + footer_height
    for row in rows:
        wrapped_cells = []
        max_lines = 1
        for value, width in zip(row, col_widths):
            max_chars = max(4, int(width / (body_size * 0.52)))
            lines = wrap_pdf_text(value, max_chars)[:5]
            wrapped_cells.append(lines)
            max_lines = max(max_lines, len(lines))
        row_height = max(17, 7 + max_lines * line_height)
        if y - row_height < bottom:
            page_streams.append(bytes(content))
            page_num += 1
            content, y = draw_page_header(page_num)
        content.extend(pdf_line(margin, y + 4, page_width - margin, y + 4, 0.9, 0.35))
        x = margin
        for lines, width, column in zip(wrapped_cells, col_widths, columns):
            text_x = x + 3
            if column.get("align") == "right":
                text_x = x + max(3, width - 52)
            for index, line in enumerate(lines):
                content.extend(pdf_text(text_x, y - index * line_height, line, body_size, False))
            x += width
        y -= row_height
    page_streams.append(bytes(content))
    return assemble_pdf(page_streams, page_width, page_height)


def pdf_response(pdf_bytes: bytes, filename: str) -> StreamingResponse:
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
