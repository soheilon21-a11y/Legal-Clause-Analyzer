"""Professional PDF report generation for redline suggestions.

Produces a lawyer-reviewable PDF report using ReportLab, with
color-coded risk levels, structured tables, and a mandatory
disclaimer. The report never implies automatic contract modification.
"""

from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
)

from redlining.models import RedlineResult, RedlineSuggestion
from shared.pdf_helpers import (
    RISK_SCORE_COLORS,
    base_table_style,
    safe_paragraph,
)


def _suggestion_table(
    suggestion: RedlineSuggestion,
    styles: Any,
    usable_width: float,
    index: int,
) -> Table:
    body = styles["BodyText"]
    label_width = 1.4 * inch
    value_width = usable_width - label_width

    risk_color = RISK_SCORE_COLORS.get(suggestion.risk_level, colors.black)

    rows: list[list[Any]] = [
        [
            safe_paragraph(f"Suggestion #{index}", body, bold=True),
            safe_paragraph("", body),
        ],
        [
            safe_paragraph("Clause Type", body, bold=True),
            safe_paragraph(suggestion.clause_type, body),
        ],
        [
            safe_paragraph("Risk Level", body, bold=True),
            safe_paragraph(
                suggestion.risk_level, body, text_color=risk_color
            ),
        ],
        [
            safe_paragraph("Confidence", body, bold=True),
            safe_paragraph(
                f"{suggestion.confidence_score:.0%}", body
            ),
        ],
        [
            safe_paragraph("Negotiable", body, bold=True),
            safe_paragraph(
                "Yes" if suggestion.negotiable else "No", body
            ),
        ],
        [
            safe_paragraph("Playbook", body, bold=True),
            safe_paragraph(suggestion.playbook_source, body),
        ],
        [
            safe_paragraph("Jurisdiction", body, bold=True),
            safe_paragraph(suggestion.jurisdiction, body),
        ],
        [
            safe_paragraph("Original Clause", body, bold=True),
            safe_paragraph(suggestion.original_clause, body),
        ],
        [
            safe_paragraph("Suggested Clause", body, bold=True),
            safe_paragraph(
                suggestion.suggested_clause, body,
                text_color=colors.darkblue,
            ),
        ],
        [
            safe_paragraph("Reason", body, bold=True),
            safe_paragraph(suggestion.reason, body),
        ],
    ]

    table = Table(rows, colWidths=[label_width, value_width])
    table.setStyle(base_table_style())
    return table


def generate_redline_pdf(
    result: RedlineResult,
    contract_source: str = "Uploaded Contract",
) -> BytesIO:
    """Generate a professional redline PDF report.

    Args:
        result: The redline result containing all suggestions.
        contract_source: Filename or label for the source contract.

    Returns:
        A ``BytesIO`` buffer containing the PDF bytes.
    """
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    usable_width = document.width
    story: list[Any] = []

    story.append(Paragraph("Redline Analysis Report", styles["Heading1"]))
    story.append(
        Paragraph(
            f"Source: {contract_source}",
            styles["Heading2"],
        )
    )
    story.append(
        Paragraph(
            "Generated locally by Legal Clause Analyzer.",
            styles["BodyText"],
        )
    )
    story.append(Spacer(1, 0.15 * inch))

    summary_rows = [
        ["Metric", "Value"],
        ["Total clauses scanned", str(result.total_clauses_scanned)],
        [
            "Negotiable clauses found",
            str(result.negotiable_clauses_found),
        ],
        ["Playbooks used", ", ".join(result.playbooks_used) or "None"],
        [
            "Total suggestions",
            str(len(result.suggestions)),
        ],
    ]
    summary_table = Table(
        summary_rows,
        colWidths=[2.0 * inch, usable_width - 2.0 * inch],
    )
    summary_table.setStyle(base_table_style())
    story.append(summary_table)
    story.append(Spacer(1, 0.2 * inch))

    if not result.suggestions:
        story.append(
            Paragraph(
                "No negotiable clauses were detected in this contract.",
                styles["BodyText"],
            )
        )
    else:
        story.append(
            Paragraph("Redline Suggestions", styles["Heading2"])
        )
        story.append(
            Paragraph(
                (
                    "Each suggestion below requires lawyer review "
                    "before use. No contract modification has been "
                    "made automatically."
                ),
                styles["BodyText"],
            )
        )
        story.append(Spacer(1, 0.15 * inch))

        for idx, suggestion in enumerate(result.suggestions, start=1):
            story.append(
                _suggestion_table(
                    suggestion, styles, usable_width, idx
                )
            )
            story.append(Spacer(1, 0.2 * inch))

    story.append(Spacer(1, 0.2 * inch))
    story.append(
        Paragraph(
            f"<b>Disclaimer:</b> {result.disclaimer}",
            styles["BodyText"],
        )
    )

    document.build(story)
    buffer.seek(0)
    return buffer
