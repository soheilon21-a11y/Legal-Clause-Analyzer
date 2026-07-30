"""Shared ReportLab PDF generation utilities.

Provides reusable helpers for building professional PDF reports:
safe HTML escaping, table styling, color mapping, and common
layout primitives. Used by both the main analysis reports and
the redlining reports.
"""

from html import escape
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import Paragraph, Table, TableStyle


RISK_SCORE_COLORS: dict[str, Any] = {
    "Critical": colors.darkred,
    "High": colors.red,
    "Medium": colors.orange,
    "Low": colors.green,
}


def risk_score_color(score: int) -> Any:
    """Return a color for an overall risk score (higher is worse)."""
    if score >= 70:
        return colors.red
    if score >= 40:
        return colors.orange
    return colors.green


def readiness_score_color(score: int) -> Any:
    """Return a color for a readiness score (higher is better)."""
    if score >= 80:
        return colors.green
    if score >= 50:
        return colors.orange
    return colors.red


def safe_paragraph(
    text: Any,
    style: Any,
    bold: bool = False,
    text_color: Any = None,
) -> Paragraph:
    """Return a ReportLab Paragraph with safe HTML escaping."""
    if text is None:
        text = "\u2014"
    safe_text = escape(str(text)).replace("\n", "<br/>")
    if bold:
        safe_text = f"<b>{safe_text}</b>"
    if text_color is not None:
        style = style.clone("_colored", textColor=text_color)
    return Paragraph(safe_text, style)


def join_items(items: list[Any], fallback: str = "\u2014") -> str:
    """Return a comma-separated string or a fallback placeholder."""
    if not items:
        return fallback
    return ", ".join(str(item) for item in items)


def base_table_style(align: str = "LEFT") -> TableStyle:
    """Return the common table style used across PDF reports."""
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
            ("GRID", (0, 0), (-1, -1), 1, colors.grey),
            ("BOX", (0, 0), (-1, -1), 1, colors.black),
            ("ALIGN", (0, 0), (-1, -1), align),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
    )


def make_table(
    rows: list[list[Any]],
    col_widths: list[Any],
    styles: Any,
    align: str = "LEFT",
    first_col_bold: bool = True,
    extra_commands: list[tuple[Any, ...]] | None = None,
    repeat_rows: int = 1,
) -> Table:
    """Build a styled ReportLab Table with Paragraph-based wrapping cells."""
    alignment_map = {
        "LEFT": TA_LEFT,
        "CENTER": 1,
        "RIGHT": 2,
    }
    body_alignment = alignment_map.get(align, TA_LEFT)
    body_style = styles["BodyText"].clone(
        "_table_body",
        alignment=body_alignment,
    )
    header_style = body_style.clone(
        "_table_header",
        textColor=colors.white,
        fontName="Helvetica-Bold",
    )

    wrapped_rows: list[list[Paragraph]] = []

    for row_idx, row in enumerate(rows):
        wrapped_row: list[Paragraph] = []
        for col_idx, value in enumerate(row):
            if isinstance(value, Paragraph):
                wrapped_row.append(value)
            elif row_idx == 0:
                wrapped_row.append(safe_paragraph(value, header_style))
            else:
                is_bold = first_col_bold and col_idx == 0
                wrapped_row.append(
                    safe_paragraph(value, body_style, bold=is_bold)
                )
        wrapped_rows.append(wrapped_row)

    style = base_table_style(align)
    for command in extra_commands or []:
        style.add(*command)
    table = Table(wrapped_rows, colWidths=col_widths, repeatRows=repeat_rows)
    table.setStyle(style)
    return table
