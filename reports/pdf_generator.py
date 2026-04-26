"""
reports/pdf_generator.py — ReportLab PDF generation for MineGuard Module 2

Generates two MoC-style report types:
  1. MIS Quarterly Report  — full milestone status table
  2. Delay Report          — only red-flagged / delayed milestones

Both pull data directly from the Module 1 DB via passed-in DataFrames.
No Streamlit imports — pure PDF logic, testable standalone.
"""

import io
import os
from datetime import date, datetime
import streamlit as st
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether,
)

from utils.constants import TODAY

# ── Page margins ─────────────────────────────────────────────────
LEFT_MARGIN  = 18 * mm
RIGHT_MARGIN = 18 * mm
TOP_MARGIN   = 20 * mm
BOT_MARGIN   = 20 * mm

# ── MoC colour palette (aligned with Streamlit light theme) ─────
MOC_NAVY   = colors.HexColor("#1B3A6B")   # primary navy
MOC_GOLD   = colors.HexColor("#E8A020")   # accent saffron/gold
MOC_LIGHT  = colors.HexColor("#EEF2F7")   # light blue-grey
MOC_WHITE  = colors.white
MOC_RED    = colors.HexColor("#C62828")   # error red
MOC_GREEN  = colors.HexColor("#2E7D32")   # success green
MOC_YELLOW = colors.HexColor("#F57C00")   # warning orange
MOC_GREY   = colors.HexColor("#4A5568")   # muted text
MOC_BORDER = colors.HexColor("#CBD5E0")
MOC_HEADER = colors.HexColor("#2C5282")   # table header bg

# ── Status → colour map ──────────────────────────────────────────
STATUS_COLOR = {
    "complete":    MOC_GREEN,
    "in_progress": colors.HexColor("#1A5276"),
    "pending":     MOC_GREY,
    "delayed":     MOC_RED,
}


# ══════════════════════════════════════════════════════════════════
# STYLE FACTORY
# ══════════════════════════════════════════════════════════════════

def _build_styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "doc_title": ParagraphStyle(
            "doc_title", parent=base["Normal"],
            fontSize=16, fontName="Helvetica-Bold",
            textColor=MOC_WHITE, alignment=TA_CENTER,
            spaceAfter=2,
        ),
        "doc_subtitle": ParagraphStyle(
            "doc_subtitle", parent=base["Normal"],
            fontSize=10, fontName="Helvetica",
            textColor=MOC_WHITE, alignment=TA_CENTER,
        ),
        "section_head": ParagraphStyle(
            "section_head", parent=base["Normal"],
            fontSize=10, fontName="Helvetica-Bold",
            textColor=MOC_NAVY, spaceBefore=8, spaceAfter=4,
        ),
        "meta_label": ParagraphStyle(
            "meta_label", parent=base["Normal"],
            fontSize=8, fontName="Helvetica-Bold",
            textColor=MOC_NAVY,
        ),
        "meta_value": ParagraphStyle(
            "meta_value", parent=base["Normal"],
            fontSize=8, fontName="Helvetica",
            textColor=colors.black,
        ),
        "cell_normal": ParagraphStyle(
            "cell_normal", parent=base["Normal"],
            fontSize=8, fontName="Helvetica",
            textColor=colors.black, leading=11,
        ),
        "cell_bold": ParagraphStyle(
            "cell_bold", parent=base["Normal"],
            fontSize=8, fontName="Helvetica-Bold",
            textColor=colors.black,
        ),
        "footer": ParagraphStyle(
            "footer", parent=base["Normal"],
            fontSize=7, fontName="Helvetica",
            textColor=MOC_GREY, alignment=TA_CENTER,
        ),
        "note": ParagraphStyle(
            "note", parent=base["Normal"],
            fontSize=8, fontName="Helvetica-Oblique",
            textColor=MOC_GREY, spaceBefore=4,
        ),
        "alert_head": ParagraphStyle(
            "alert_head", parent=base["Normal"],
            fontSize=9, fontName="Helvetica-Bold",
            textColor=MOC_RED, spaceBefore=6, spaceAfter=2,
        ),
    }


# ══════════════════════════════════════════════════════════════════
# SHARED ELEMENTS
# ══════════════════════════════════════════════════════════════════

def _header_block(styles: dict, title: str, subtitle: str, report_no: str) -> list:
    """MoC-style navy banner header."""
    header_table = Table(
        [[
            Paragraph(title,    styles["doc_title"]),
            Paragraph(subtitle, styles["doc_subtitle"]),
        ]],
        colWidths=["60%", "40%"],
    )
    header_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (0, -1), MOC_NAVY),
        ("BACKGROUND",  (1, 0), (1, -1), MOC_HEADER),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",  (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))

    # Gold underline strip
    gold_bar = Table([[""]],  colWidths=["100%"])
    gold_bar.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), MOC_GOLD),
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))

    return [header_table, gold_bar, Spacer(1, 6)]


def _meta_table(styles: dict, rows: list[tuple]) -> Table:
    """Two-column key/value metadata block."""
    data = [
        [
            Paragraph(k, styles["meta_label"]),
            Paragraph(str(v), styles["meta_value"]),
        ]
        for k, v in rows
    ]
    t = Table(data, colWidths=["35%", "65%"])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (0, -1), MOC_LIGHT),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("GRID",          (0, 0), (-1, -1), 0.3, MOC_BORDER),
    ]))
    return t


def _footer_block(styles: dict, report_type: str) -> list:
    return [
        Spacer(1, 10),
        HRFlowable(width="100%", thickness=0.5, color=MOC_BORDER),
        Spacer(1, 4),
        Paragraph(
            f"MineGuard Compliance System · {report_type} · "
            f"Generated: {datetime.now().strftime('%d %b %Y %H:%M')} · "
            "Ministry of Coal — Internal Use Only",
            styles["footer"],
        ),
    ]


# ══════════════════════════════════════════════════════════════════
# REPORT 1: MIS QUARTERLY
# ══════════════════════════════════════════════════════════════════

def generate_mis_quarterly(
    project_name: str,
    project_id: int,
    project_location: str,
    project_start: str,
    submission_date: date,
    quarter: str,
    milestones_df: pd.DataFrame,
    submitted_by: str = "Compliance Officer",
) -> bytes:
    """
    Generate MIS Quarterly Report PDF.

    Args:
        project_name:     Name of the mine/project
        project_id:       DB project id
        project_location: Mine location string
        project_start:    ISO date string of project start
        submission_date:  Date of this submission
        quarter:          e.g. "Q1 FY 2025-26"
        milestones_df:    DataFrame from db.get_milestones()
        submitted_by:     Name/role of submitter

    Returns:
        PDF as bytes — write to file or serve via Streamlit download button
    """
    buf    = io.BytesIO()
    styles = _build_styles()

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=LEFT_MARGIN, rightMargin=RIGHT_MARGIN,
        topMargin=TOP_MARGIN,   bottomMargin=BOT_MARGIN,
    )

    story = []

    # ── Header ──
    story += _header_block(
        styles,
        title    = "MINISTRY OF COAL — COMPLIANCE MIS",
        subtitle = f"Quarterly Status Report · {quarter}",
        report_no= f"MIS-{project_id}-{submission_date.strftime('%Y%m')}",
    )

    # ── Metadata block ──
    story.append(Paragraph("1. PROJECT DETAILS", styles["section_head"]))
    story.append(_meta_table(styles, [
        ("Project Name",      project_name),
        ("Project ID",        f"PRJ-{project_id:04d}"),
        ("Location",          project_location or "N/A"),
        ("Project Start Date",project_start),
        ("Reporting Quarter", quarter),
        ("Submission Date",   submission_date.strftime("%d %b %Y")),
        ("Submitted By",      submitted_by),
        ("Report Reference",  f"MIS-{project_id}-{submission_date.strftime('%Y%m')}"),
    ]))
    story.append(Spacer(1, 10))

    # ── Summary counts ──
    story.append(Paragraph("2. STATUS SUMMARY", styles["section_head"]))

    total    = len(milestones_df)
    done     = int((milestones_df["status"] == "complete").sum())
    delayed  = int((milestones_df["status"] == "delayed").sum())
    pending  = int((milestones_df["status"] == "pending").sum())
    in_prog  = int((milestones_df["status"] == "in_progress").sum())
    pct      = int(done / max(total, 1) * 100)

    summary_data = [
        [
            Paragraph("Total Milestones", styles["cell_bold"]),
            Paragraph("Completed", styles["cell_bold"]),
            Paragraph("In Progress", styles["cell_bold"]),
            Paragraph("Pending", styles["cell_bold"]),
            Paragraph("Delayed", styles["cell_bold"]),
            Paragraph("Completion %", styles["cell_bold"]),
        ],
        [
            Paragraph(str(total),    styles["cell_normal"]),
            Paragraph(str(done),     styles["cell_normal"]),
            Paragraph(str(in_prog),  styles["cell_normal"]),
            Paragraph(str(pending),  styles["cell_normal"]),
            Paragraph(str(delayed),  styles["cell_normal"]),
            Paragraph(f"{pct}%",     styles["cell_normal"]),
        ],
    ]
    summary_table = Table(summary_data, colWidths=["17%"] * 6)
    summary_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), MOC_HEADER),
        ("TEXTCOLOR",     (0, 0), (-1, 0), MOC_WHITE),
        ("BACKGROUND",    (0, 1), (-1, 1), MOC_LIGHT),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("GRID",          (0, 0), (-1, -1), 0.4, MOC_BORDER),
        # Colour the delayed count red if >0
        *([("TEXTCOLOR", (4, 1), (4, 1), MOC_RED)] if delayed > 0 else []),
        *([("TEXTCOLOR", (1, 1), (1, 1), MOC_GREEN)] if done > 0 else []),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 10))

    # ── Milestone details table ──
    story.append(Paragraph("3. MILESTONE STATUS DETAILS", styles["section_head"]))

    col_headers = [
        Paragraph(h, styles["cell_bold"]) for h in
        ["#", "Milestone Name", "Target Date", "Actual Date", "Status", "Notes"]
    ]
    table_data = [col_headers]

    for i, (_, row) in enumerate(milestones_df.iterrows()):
        status_text  = row["status"].replace("_", " ").upper()

        table_data.append([
            Paragraph(str(i + 1),                            styles["cell_normal"]),
            Paragraph(str(row["name"]),                       styles["cell_normal"]),
            Paragraph(str(row["target_date"]),                styles["cell_normal"]),
            Paragraph(str(row["actual_date"] or "—"),         styles["cell_normal"]),
            Paragraph(status_text,                            styles["cell_bold"]),
            Paragraph(str(row["notes"] or "—")[:80],          styles["cell_normal"]),
        ])

    ms_table = Table(
        table_data,
        colWidths=["5%", "25%", "13%", "13%", "13%", "31%"],
        repeatRows=1,
    )

    row_styles = [
        ("BACKGROUND",    (0, 0), (-1, 0), MOC_HEADER),
        ("TEXTCOLOR",     (0, 0), (-1, 0), MOC_WHITE),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("ALIGN",         (0, 0), (0, -1), "CENTER"),
        ("ALIGN",         (2, 0), (4, -1), "CENTER"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
        ("GRID",          (0, 0), (-1, -1), 0.4, MOC_BORDER),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [MOC_WHITE, MOC_LIGHT]),
    ]

    # Highlight delayed rows
    for i, (_, row) in enumerate(milestones_df.iterrows()):
        if row["status"] == "delayed":
            row_styles.append(("BACKGROUND", (0, i + 1), (-1, i + 1), colors.HexColor("#FDEDEC")))
            row_styles.append(("TEXTCOLOR",  (4, i + 1), (4, i + 1), MOC_RED))
        elif row["status"] == "complete":
            row_styles.append(("TEXTCOLOR",  (4, i + 1), (4, i + 1), MOC_GREEN))

    ms_table.setStyle(TableStyle(row_styles))
    story.append(ms_table)
    story.append(Spacer(1, 10))

    # ── Declaration ──
    story.append(Paragraph("4. DECLARATION", styles["section_head"]))
    story.append(_meta_table(styles, [
        ("Submitted By",   submitted_by),
        ("Designation",    st.session_state.get("role", "Compliance Officer") if _has_streamlit() else "Compliance Officer"),
        ("Date",           submission_date.strftime("%d %b %Y")),
        ("Signature",      "__________________ (Authorised Signatory)"),
    ]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "I hereby certify that the information provided above is accurate and complete "
        "to the best of my knowledge, in compliance with MoC Circular No. CIL/C-5A/2024.",
        styles["note"],
    ))

    story += _footer_block(styles, "MIS Quarterly Report")

    doc.build(story)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════
# REPORT 2: DELAY REPORT
# ══════════════════════════════════════════════════════════════════

def generate_delay_report(
    project_name: str,
    project_id: int,
    project_location: str,
    submission_date: date,
    milestones_df: pd.DataFrame,
    submitted_by: str = "Compliance Officer",
) -> bytes:
    """
    Generate Delay / Red Flag Report PDF.
    Only includes milestones that are delayed or overdue.

    Returns:
        PDF as bytes. Returns None-equivalent empty PDF if no delays exist.
    """
    buf    = io.BytesIO()
    styles = _build_styles()

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=LEFT_MARGIN, rightMargin=RIGHT_MARGIN,
        topMargin=TOP_MARGIN,   bottomMargin=BOT_MARGIN,
    )

    story = []

    # Filter: delayed status OR overdue (past target, not complete)
    delayed_rows = []
    for _, row in milestones_df.iterrows():
        is_delayed = row["status"] == "delayed"
        is_overdue = (
            row["status"] != "complete"
            and date.fromisoformat(str(row["target_date"])) < TODAY
        )
        if is_delayed or is_overdue:
            delayed_rows.append(row)

    # ── Header ──
    story += _header_block(
        styles,
        title    = "MINISTRY OF COAL — DELAY REPORT",
        subtitle = f"Red Flag Compliance Alert · {submission_date.strftime('%d %b %Y')}",
        report_no= f"DLY-{project_id}-{submission_date.strftime('%Y%m%d')}",
    )

    # ── Metadata ──
    story.append(Paragraph("1. PROJECT DETAILS", styles["section_head"]))
    story.append(_meta_table(styles, [
        ("Project Name",    project_name),
        ("Project ID",      f"PRJ-{project_id:04d}"),
        ("Location",        project_location or "N/A"),
        ("Report Date",     submission_date.strftime("%d %b %Y")),
        ("Submitted By",    submitted_by),
        ("Total Milestones",str(len(milestones_df))),
        ("Delayed / Overdue", str(len(delayed_rows))),
        ("Reference",       f"DLY-{project_id}-{submission_date.strftime('%Y%m%d')}"),
    ]))
    story.append(Spacer(1, 10))

    # ── No delays case ──
    if not delayed_rows:
        story.append(Paragraph("2. DELAY STATUS", styles["section_head"]))
        no_delay = Table(
            [[Paragraph(
                "✓  No delays or red flags detected for this reporting period. "
                "All milestones are on track.",
                styles["cell_normal"],
            )]],
            colWidths=["100%"],
        )
        no_delay.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#EAFAF1")),
            ("TEXTCOLOR",     (0, 0), (-1, -1), MOC_GREEN),
            ("TOPPADDING",    (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING",   (0, 0), (-1, -1), 12),
            ("GRID",          (0, 0), (-1, -1), 0.4, MOC_BORDER),
        ]))
        story.append(no_delay)
        story += _footer_block(styles, "Delay Report")
        doc.build(story)
        return buf.getvalue()

    # ── Delay summary ──
    story.append(Paragraph("2. DELAY SUMMARY", styles["section_head"]))

    overdue_count = sum(
        1 for r in delayed_rows
        if date.fromisoformat(str(r["target_date"])) < TODAY
    )
    story.append(_meta_table(styles, [
        ("Total Red Flags",   str(len(delayed_rows))),
        ("Overdue (past date)", str(overdue_count)),
        ("Status: Delayed",   str(sum(1 for r in delayed_rows if r["status"] == "delayed"))),
        ("Simulation Date",   TODAY.strftime("%d %b %Y")),
    ]))
    story.append(Spacer(1, 10))

    # ── Per-delay detail blocks ──
    story.append(Paragraph("3. DELAYED MILESTONE DETAILS", styles["section_head"]))

    # Summary table first
    col_headers = [
        Paragraph(h, styles["cell_bold"]) for h in
        ["#", "Milestone", "Target Date", "Days Overdue", "Status", "Bottleneck (Possible Cause)"]
    ]
    table_data = [col_headers]

    from utils.alerts import get_bottleneck

    for i, row in enumerate(delayed_rows):
        td         = date.fromisoformat(str(row["target_date"]))
        days_late  = (TODAY - td).days
        days_str   = f"+{days_late}d" if days_late > 0 else f"{abs(days_late)}d to go"
        bottleneck = get_bottleneck(row["name"], -days_late if days_late > 0 else 1, row["status"])

        table_data.append([
            Paragraph(str(i + 1),                        styles["cell_normal"]),
            Paragraph(str(row["name"]),                   styles["cell_normal"]),
            Paragraph(str(row["target_date"]),            styles["cell_normal"]),
            Paragraph(days_str,                           styles["cell_bold"]),
            Paragraph(row["status"].upper(),              styles["cell_bold"]),
            Paragraph((bottleneck or "Under review")[:90], styles["cell_normal"]),
        ])

    delay_table = Table(
        table_data,
        colWidths=["5%", "20%", "13%", "11%", "11%", "40%"],
        repeatRows=1,
    )
    delay_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), MOC_RED),
        ("TEXTCOLOR",     (0, 0), (-1, 0), MOC_WHITE),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("ALIGN",         (0, 0), (0, -1), "CENTER"),
        ("ALIGN",         (2, 0), (4, -1), "CENTER"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
        ("GRID",          (0, 0), (-1, -1), 0.4, MOC_BORDER),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.HexColor("#FDEDEC"), colors.HexColor("#FDFEFE")]),
        ("TEXTCOLOR",     (3, 1), (3, -1), MOC_RED),
        ("TEXTCOLOR",     (4, 1), (4, -1), MOC_RED),
    ]))
    story.append(delay_table)
    story.append(Spacer(1, 10))

    # ── Remediation section ──
    story.append(Paragraph("4. RECOMMENDED REMEDIATION ACTIONS", styles["section_head"]))

    for i, row in enumerate(delayed_rows):
        td         = date.fromisoformat(str(row["target_date"]))
        days_late  = (TODAY - td).days
        bottleneck = get_bottleneck(row["name"], -days_late if days_late > 0 else 1, row["status"])

        block = KeepTogether([
            Paragraph(
                f"{i + 1}. {row['name']}",
                styles["alert_head"],
            ),
            _meta_table(styles, [
                ("Target Date",        str(row["target_date"])),
                ("Days Overdue",       f"+{days_late}d" if days_late > 0 else "Approaching"),
                ("Current Status",     row["status"].upper()),
                ("Possible Cause",     bottleneck or "Under investigation"),
                ("Officer Notes",      str(row["notes"] or "None recorded")),
                ("Submitted By",       str(row.get("submitted_by", "—"))),
                ("Recommended Action", "Escalate to senior officer. Request expedited processing. "
                                       "Attach supporting documents within 3 working days."),
            ]),
            Spacer(1, 6),
        ])
        story.append(block)

    # ── Sign-off ──
    story.append(Paragraph("5. AUTHORISATION", styles["section_head"]))
    story.append(_meta_table(styles, [
        ("Prepared By",   submitted_by),
        ("Reviewed By",   "Mine Manager / Nodal Officer"),
        ("Date",          submission_date.strftime("%d %b %Y")),
        ("Signature",     "__________________ (Authorised Signatory)"),
        ("Action Deadline", (TODAY + __import__("datetime").timedelta(days=3)).strftime("%d %b %Y")),
    ]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "This delay report has been prepared as required under MoC Circular No. CIL/C-5A/2024. "
        "All flagged milestones require immediate corrective action. "
        "Failure to remediate within the stipulated timeline may attract penalties under the "
        "Environment Protection Act 1986.",
        styles["note"],
    ))

    story += _footer_block(styles, "Delay Report")
    doc.build(story)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════
# UTILITY
# ══════════════════════════════════════════════════════════════════

def _has_streamlit() -> bool:
    try:
        import streamlit as st
        return True
    except ImportError:
        return False


def save_report(pdf_bytes: bytes, path: str):
    """Utility: write PDF bytes to a file path."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(pdf_bytes)
