"""
components/report_form.py — Module 2: Single-point data entry form + PDF generation

Pulls all data from Module 1 DB (milestones table).
No re-keying — officer selects project, picks report type, downloads PDF.
"""

import streamlit as st
import pandas as pd
from datetime import date, timedelta

from db.database import get_projects, get_milestones
from db.reports_db import (
    init_reports_table, save_report_record,
    get_reports, update_report_status, delete_report,
)
from reports.pdf_generator import generate_mis_quarterly, generate_delay_report
from utils.constants import TODAY, STATUS_EMOJI

# Quarter options (FY India: Apr–Mar)
QUARTERS = [
    "Q1 FY 2025-26 (Apr–Jun 2025)",
    "Q2 FY 2025-26 (Jul–Sep 2025)",
    "Q3 FY 2025-26 (Oct–Dec 2025)",
    "Q4 FY 2025-26 (Jan–Mar 2026)",
    "Q1 FY 2026-27 (Apr–Jun 2026)",
]

REPORT_TYPES = {
    "MIS Quarterly Report": "MIS_Quarterly",
    "Delay / Red Flag Report": "Delay_Report",
}

STATUS_BADGE = {
    "Drafted":   ("🟡", "#d97706"),
    "Submitted": ("🟢", "#16a34a"),
    "Archived":  ("⚫", "#6b7280"),
}


def _preview_milestones(milestones_df: pd.DataFrame):
    """Compact milestone preview pulled from DB — no re-entry needed."""
    st.markdown('<div class="section-title">📋 Data Preview — From Module 1 DB</div>',
                unsafe_allow_html=True)

    if milestones_df.empty:
        st.warning("No milestones found. Add milestones in Module 1 first.")
        return

    total   = len(milestones_df)
    done    = int((milestones_df["status"] == "complete").sum())
    delayed = int((milestones_df["status"] == "delayed").sum())
    overdue = sum(
        1 for _, r in milestones_df.iterrows()
        if r["status"] != "complete"
        and date.fromisoformat(str(r["target_date"])) < TODAY
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📋 Total",     total)
    c2.metric("✅ Completed", done)
    c3.metric("⚠️ Delayed",   delayed)
    c4.metric("🔥 Overdue",   overdue)

    disp = milestones_df[[
        "name", "target_date", "actual_date", "status", "notes"
    ]].copy()
    disp.columns = ["Milestone", "Target Date", "Actual Date", "Status", "Notes"]
    disp["Status"] = disp["Status"].apply(
        lambda s: f"{STATUS_EMOJI.get(s, '⚪')} {s.replace('_', ' ').title()}"
    )
    st.dataframe(disp, use_container_width=True, hide_index=True)


def _report_type_info(report_type_key: str, delayed_count: int):
    """Show what will be included in the selected report."""
    if report_type_key == "MIS_Quarterly":
        st.info(
            "📄 **MIS Quarterly Report** will include: project metadata, "
            "status summary table, all milestone details, and declaration block. "
            "Template: MoC Circular No. CIL/C-5A/2024."
        )
    else:
        if delayed_count == 0:
            st.success(
                "✅ No delays detected. The Delay Report will confirm zero red flags."
            )
        else:
            st.warning(
                f"🚨 **Delay Report** will flag {delayed_count} delayed/overdue milestone(s) "
                "with bottleneck analysis and recommended remediation actions."
            )


def render(active_project_id: int = None):
    """
    Main render function for Module 2 report entry form.

    Args:
        active_project_id: Pre-selected project from sidebar (optional).
                           If None, user picks from dropdown.
    """
    init_reports_table()

    st.markdown("""
    <div style="background:#161b22;border:1px solid #f0a500;border-radius:8px;
                padding:10px 16px;margin-bottom:1rem;">
      <span style="color:#f0a500;font-family:'IBM Plex Mono',monospace;font-size:0.8rem;">
        📑 MODULE 2 — SMART REPORTING
      </span>
      <span style="color:#8b949e;font-size:0.75rem;margin-left:1rem;">
        Single-point entry · Pulls from Module 1 DB · No re-keying
      </span>
    </div>
    """, unsafe_allow_html=True)

    form_tab, history_tab = st.tabs(["📝 Generate Report", "🗂️ Report History"])

    # ════════════════════════════════════════
    # TAB 1: GENERATE REPORT
    # ════════════════════════════════════════
    with form_tab:
        projects_df = get_projects()

        if projects_df.empty:
            st.warning("No projects found. Create a project in Module 1 first.")
            return

        # ── Project selector ──
        st.markdown('<div class="section-title">1. Select Project</div>',
                    unsafe_allow_html=True)

        project_options = dict(zip(projects_df["name"], projects_df["id"]))

        # Pre-select active project if passed in
        default_idx = 0
        if active_project_id:
            names = list(project_options.keys())
            ids   = list(project_options.values())
            if active_project_id in ids:
                default_idx = ids.index(active_project_id)

        selected_name = st.selectbox(
            "Project",
            list(project_options.keys()),
            index=default_idx,
            key="rpt_project",
        )
        selected_id = project_options[selected_name]

        # Fetch project metadata
        proj_row  = projects_df[projects_df["id"] == selected_id].iloc[0]
        proj_loc  = proj_row.get("location", "N/A") or "N/A"
        proj_start= proj_row["start_date"]

        # Fetch milestones — single source of truth from Module 1
        milestones_df = get_milestones(selected_id)

        delayed_count = sum(
            1 for _, r in milestones_df.iterrows()
            if r["status"] == "delayed"
            or (r["status"] != "complete"
                and date.fromisoformat(str(r["target_date"])) < TODAY)
        )

        # ── Preview pulled data ──
        _preview_milestones(milestones_df)

        st.markdown("---")

        # ── Report config form ──
        st.markdown('<div class="section-title">2. Report Configuration</div>',
                    unsafe_allow_html=True)

        with st.form("report_gen_form", clear_on_submit=False):
            col_a, col_b = st.columns([1, 1])

            with col_a:
                report_label = st.selectbox(
                    "Report Type *",
                    list(REPORT_TYPES.keys()),
                    key="rpt_type",
                )
                report_type_key = REPORT_TYPES[report_label]

                submission_date = st.date_input(
                    "Submission Date *",
                    value=TODAY,
                    max_value=TODAY + timedelta(days=30),
                )

            with col_b:
                quarter = st.selectbox(
                    "Reporting Quarter *",
                    QUARTERS,
                    index=3,   # Default: Q4 FY 2025-26
                    key="rpt_quarter",
                    disabled=(report_type_key == "Delay_Report"),
                )
                submitted_by = st.text_input(
                    "Submitted By *",
                    value=st.session_state.get("username", "Compliance Officer"),
                    placeholder="Full name / designation",
                )

            # Validate before generate
            errors = []
            if not submitted_by.strip():
                errors.append("Submitted By is required.")

            _report_type_info(report_type_key, delayed_count)

            generate_btn = st.form_submit_button(
                "⚙️ Generate PDF Report",
                type="primary",
                use_container_width=True,
            )

            if generate_btn:
                if errors:
                    for e in errors:
                        st.error(f"❌ {e}")
                elif milestones_df.empty:
                    st.error("❌ Cannot generate report: no milestones in DB.")
                else:
                    with st.spinner("Generating PDF…"):
                        try:
                            if report_type_key == "MIS_Quarterly":
                                pdf_bytes = generate_mis_quarterly(
                                    project_name     = selected_name,
                                    project_id       = selected_id,
                                    project_location = proj_loc,
                                    project_start    = proj_start,
                                    submission_date  = submission_date,
                                    quarter          = quarter,
                                    milestones_df    = milestones_df,
                                    submitted_by     = submitted_by.strip(),
                                )
                                filename = (
                                    f"MIS_Quarterly_{selected_name.replace(' ', '_')}"
                                    f"_{quarter[:2]}_{submission_date.strftime('%Y%m%d')}.pdf"
                                )
                            else:
                                pdf_bytes = generate_delay_report(
                                    project_name     = selected_name,
                                    project_id       = selected_id,
                                    project_location = proj_loc,
                                    submission_date  = submission_date,
                                    milestones_df    = milestones_df,
                                    submitted_by     = submitted_by.strip(),
                                )
                                filename = (
                                    f"Delay_Report_{selected_name.replace(' ', '_')}"
                                    f"_{submission_date.strftime('%Y%m%d')}.pdf"
                                )

                            # Save record to DB
                            save_report_record(
                                project_id      = selected_id,
                                report_type     = report_type_key,
                                quarter         = quarter if report_type_key == "MIS_Quarterly" else "N/A",
                                submission_date = submission_date.isoformat(),
                                submitted_by    = submitted_by.strip(),
                                status          = "Drafted",
                            )

                            # Store in session for download button outside form
                            st.session_state["pdf_bytes"]   = pdf_bytes
                            st.session_state["pdf_filename"] = filename
                            st.session_state["pdf_label"]    = report_label

                            st.success(f"✅ {report_label} generated successfully!")

                        except Exception as ex:
                            st.error(f"❌ PDF generation failed: {ex}")
                            import traceback
                            st.code(traceback.format_exc(), language="text")

        # ── Download button (outside form to persist across reruns) ──
        if st.session_state.get("pdf_bytes"):
            st.markdown("---")
            st.markdown('<div class="section-title">3. Download</div>',
                        unsafe_allow_html=True)

            col_dl, col_mark = st.columns([2, 1])

            with col_dl:
                st.download_button(
                    label    = f"⬇️ Download {st.session_state['pdf_label']}",
                    data     = st.session_state["pdf_bytes"],
                    file_name= st.session_state["pdf_filename"],
                    mime     = "application/pdf",
                    use_container_width=True,
                    type     = "primary",
                )
            with col_mark:
                if st.button("✅ Mark as Submitted", use_container_width=True):
                    # Update latest report for this project to Submitted
                    rpts = get_reports(selected_id)
                    if not rpts.empty:
                        latest_id = rpts.iloc[0]["id"]
                        update_report_status(latest_id, "Submitted")
                        st.success("Marked as Submitted.")
                        st.rerun()

    # ════════════════════════════════════════
    # TAB 2: REPORT HISTORY
    # ════════════════════════════════════════
    with history_tab:
        st.markdown('<div class="section-title">Generated Reports Archive</div>',
                    unsafe_allow_html=True)

        all_reports = get_reports()

        if all_reports.empty:
            st.info("No reports generated yet.")
            return

        # KPI strip
        total_rpts  = len(all_reports)
        submitted   = int((all_reports["status"] == "Submitted").sum())
        drafted     = int((all_reports["status"] == "Drafted").sum())

        kc1, kc2, kc3 = st.columns(3)
        kc1.metric("📄 Total Reports", total_rpts)
        kc2.metric("✅ Submitted",      submitted)
        kc3.metric("🟡 Drafted",        drafted)

        st.markdown("---")

        # Render each report as a card
        for _, row in all_reports.iterrows():
            emoji, color = STATUS_BADGE.get(row["status"], ("⚪", "#6b7280"))

            st.markdown(f"""
            <div style="background:#161b22;border:1px solid #30363d;
                        border-left:4px solid {color};border-radius:8px;
                        padding:10px 16px;margin-bottom:8px;">
              <div style="display:flex;justify-content:space-between;
                          align-items:center;flex-wrap:wrap;gap:8px;">
                <div>
                  <span style="font-weight:600;color:#e6edf3;font-size:0.9rem;">
                    {emoji} {row['report_type'].replace('_', ' ')}
                  </span>
                  <span style="font-size:0.75rem;color:#8b949e;margin-left:8px;
                               font-family:'IBM Plex Mono',monospace;">
                    {row['project_name']} · {row['submission_date']}
                  </span>
                </div>
                <span style="background:{color}22;color:{color};
                             border:1px solid {color};border-radius:20px;
                             padding:2px 10px;font-size:0.72rem;
                             font-family:'IBM Plex Mono',monospace;">
                  {row['status']}
                </span>
              </div>
              <div style="font-size:0.73rem;color:#8b949e;margin-top:4px;">
                By: {row['submitted_by']} &nbsp;·&nbsp;
                Quarter: {row['quarter']} &nbsp;·&nbsp;
                Created: {row['created_at'][:16]}
              </div>
            </div>
            """, unsafe_allow_html=True)

            # Status actions inline
            col_s, col_d, _ = st.columns([1, 1, 3])
            with col_s:
                new_status = st.selectbox(
                    "Status",
                    ["Drafted", "Submitted", "Archived"],
                    index=["Drafted", "Submitted", "Archived"].index(row["status"]),
                    key=f"rs_{row['id']}",
                    label_visibility="collapsed",
                )
                if new_status != row["status"]:
                    update_report_status(row["id"], new_status)
                    st.rerun()
            with col_d:
                if st.button("🗑️ Delete", key=f"rd_{row['id']}"):
                    delete_report(row["id"])
                    st.rerun()
