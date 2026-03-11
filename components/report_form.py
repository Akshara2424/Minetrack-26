"""
components/report_form.py — Module 2: Smart Report Entry Form

Two tabs:
  📝 Generate Report  — pulls Module 1 DB, config form, PDF gen, archive + download
  🗂️ Report History   — mirrors dashboard archive with status controls
"""

import os
import streamlit as st
import pandas as pd
from datetime import date, timedelta

from db.database   import get_projects, get_milestones
from db.reports_db import (
    init_reports_table, save_report_record, update_report_status,
    update_file_path, delete_report, get_reports,
)
from reports.pdf_generator import generate_mis_quarterly, generate_delay_report
from utils.constants       import TODAY, STATUS_EMOJI

ARCHIVE_DIR = os.path.join(
    os.path.dirname(__file__), "..", "data", "reports_archive"
)

QUARTERS = [
    "Q1 FY 2025-26 (Apr–Jun 2025)",
    "Q2 FY 2025-26 (Jul–Sep 2025)",
    "Q3 FY 2025-26 (Oct–Dec 2025)",
    "Q4 FY 2025-26 (Jan–Mar 2026)",
    "Q1 FY 2026-27 (Apr–Jun 2026)",
]
REPORT_TYPES = {
    "MIS Quarterly Report":    "MIS_Quarterly",
    "Delay / Red Flag Report": "Delay_Report",
}
STATUS_META = {
    "Drafted":   ("🟡", "#d97706"),
    "Submitted": ("🟢", "#16a34a"),
    "Archived":  ("⚫", "#6b7280"),
}


def _archive_pdf(pdf_bytes: bytes, filename: str, report_id: int) -> str:
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    path = os.path.join(ARCHIVE_DIR, filename)
    with open(path, "wb") as f:
        f.write(pdf_bytes)
    update_file_path(report_id, path)
    return path


def _preview(milestones_df: pd.DataFrame):
    st.markdown(
        '<div class="section-title">📋 Data Preview — Live from Module 1 DB</div>',
        unsafe_allow_html=True,
    )
    if milestones_df.empty:
        st.warning("No milestones found. Add them in Module 1 first.")
        return

    c1, c2, c3, c4 = st.columns(4)
    total   = len(milestones_df)
    done    = int((milestones_df["status"] == "complete").sum())
    delayed = int((milestones_df["status"] == "delayed").sum())
    overdue = sum(
        1 for _, r in milestones_df.iterrows()
        if r["status"] != "complete"
        and date.fromisoformat(str(r["target_date"])) < TODAY
    )
    c1.metric("📋 Total",     total)
    c2.metric("✅ Completed", done)
    c3.metric("⚠️ Delayed",   delayed)
    c4.metric("🔥 Overdue",   overdue)

    disp = milestones_df[["name","target_date","actual_date","status","notes"]].copy()
    disp.columns = ["Milestone","Target Date","Actual Date","Status","Notes"]
    disp["Status"] = disp["Status"].apply(
        lambda s: f"{STATUS_EMOJI.get(s,'⚪')} {s.replace('_',' ').title()}"
    )
    st.dataframe(disp, use_container_width=True, hide_index=True)


def render(active_project_id: int = None):
    init_reports_table()

    st.markdown("""
    <div style="background:#161b22;border:1px solid #f0a500;border-radius:8px;
                padding:10px 16px;margin-bottom:1rem">
      <span style="color:#f0a500;font-family:'IBM Plex Mono',monospace;font-size:.8rem">
        📑 MODULE 2 — SMART REPORTING
      </span>
      <span style="color:#8b949e;font-size:.74rem;margin-left:1rem">
        Single-point entry · Pulls Module 1 DB · Auto-archived on generate
      </span>
    </div>
    """, unsafe_allow_html=True)

    gen_tab, hist_tab = st.tabs(["📝 Generate Report", "🗂️ Report History"])

    # ════════════════════════════════════════
    # TAB 1 — GENERATE
    # ════════════════════════════════════════
    with gen_tab:
        projects_df = get_projects()
        if projects_df.empty:
            st.warning("No projects yet. Create one in Module 1.")
            return

        # Project selector (pre-seeded from sidebar selection)
        proj_map    = dict(zip(projects_df["name"], projects_df["id"]))
        default_idx = 0
        if active_project_id and active_project_id in proj_map.values():
            default_idx = list(proj_map.values()).index(active_project_id)

        sel_name = st.selectbox("Project", list(proj_map.keys()),
                                index=default_idx, key="rf_proj")
        sel_id   = proj_map[sel_name]
        proj_row = projects_df[projects_df["id"] == sel_id].iloc[0]
        proj_loc = proj_row.get("location", "N/A") or "N/A"
        proj_start = proj_row["start_date"]

        milestones_df = get_milestones(sel_id)
        delayed_count = sum(
            1 for _, r in milestones_df.iterrows()
            if r["status"] == "delayed" or (
                r["status"] != "complete"
                and date.fromisoformat(str(r["target_date"])) < TODAY
            )
        )

        _preview(milestones_df)
        st.markdown("---")

        # Config form
        st.markdown('<div class="section-title">2. Report Configuration</div>',
                    unsafe_allow_html=True)

        with st.form("rf_gen", clear_on_submit=False):
            ca, cb = st.columns(2)
            with ca:
                rpt_label   = st.selectbox("Report Type *", list(REPORT_TYPES.keys()))
                rpt_key     = REPORT_TYPES[rpt_label]
                sub_date    = st.date_input("Submission Date *", value=TODAY,
                                            max_value=TODAY + timedelta(days=30))
            with cb:
                quarter     = st.selectbox("Quarter *", QUARTERS, index=3,
                                           disabled=(rpt_key == "Delay_Report"))
                submitted_by= st.text_input(
                    "Submitted By *",
                    value=st.session_state.get("username", "Compliance Officer"),
                )

            # Contextual hint
            if rpt_key == "MIS_Quarterly":
                st.info("📄 Includes all milestones, summary table, and declaration.")
            elif delayed_count:
                st.warning(f"🚨 {delayed_count} delay(s) will be flagged with bottleneck analysis.")
            else:
                st.success("✅ No delays — report will confirm clean status.")

            go = st.form_submit_button("⚙️ Generate & Archive PDF",
                                       type="primary", use_container_width=True)

            if go:
                if not submitted_by.strip():
                    st.error("❌ Submitted By is required.")
                elif milestones_df.empty:
                    st.error("❌ No milestones in DB.")
                else:
                    with st.spinner("Building PDF…"):
                        try:
                            pname_safe = sel_name.replace(" ", "_")
                            if rpt_key == "MIS_Quarterly":
                                pdf = generate_mis_quarterly(
                                    project_name=sel_name, project_id=sel_id,
                                    project_location=proj_loc,
                                    project_start=proj_start,
                                    submission_date=sub_date, quarter=quarter,
                                    milestones_df=milestones_df,
                                    submitted_by=submitted_by.strip(),
                                )
                                fname = f"MIS_{pname_safe}_{quarter[:2]}_{sub_date.strftime('%Y%m%d')}.pdf"
                            else:
                                pdf = generate_delay_report(
                                    project_name=sel_name, project_id=sel_id,
                                    project_location=proj_loc,
                                    submission_date=sub_date,
                                    milestones_df=milestones_df,
                                    submitted_by=submitted_by.strip(),
                                )
                                fname = f"Delay_{pname_safe}_{sub_date.strftime('%Y%m%d')}.pdf"

                            # DB record + local archive
                            rid = save_report_record(
                                project_id=sel_id, report_type=rpt_key,
                                quarter=quarter if rpt_key == "MIS_Quarterly" else "N/A",
                                submission_date=sub_date.isoformat(),
                                submitted_by=submitted_by.strip(), status="Drafted",
                            )
                            _archive_pdf(pdf, fname, rid)

                            st.session_state["_rf_pdf"]   = pdf
                            st.session_state["_rf_fname"] = fname
                            st.session_state["_rf_label"] = rpt_label
                            st.session_state["_rf_rid"]   = rid
                            st.success(f"✅ {rpt_label} generated and saved to archive!")

                        except Exception as ex:
                            st.error(f"❌ {ex}")
                            import traceback; st.code(traceback.format_exc())

        # Download + mark-submitted (outside form so they persist)
        if st.session_state.get("_rf_pdf"):
            st.markdown("---")
            dl_col, mark_col = st.columns([2, 1])
            with dl_col:
                st.download_button(
                    label     = f"⬇️ Download {st.session_state['_rf_label']}",
                    data      = st.session_state["_rf_pdf"],
                    file_name = st.session_state["_rf_fname"],
                    mime      = "application/pdf",
                    key       = "rf_dl",
                    type      = "primary",
                    use_container_width=True,
                )
            with mark_col:
                if st.button("✅ Mark as Submitted", use_container_width=True,
                             key="rf_mark"):
                    update_report_status(st.session_state["_rf_rid"], "Submitted")
                    st.success("Marked Submitted.")
                    st.rerun()

    # ════════════════════════════════════════
    # TAB 2 — HISTORY
    # ════════════════════════════════════════
    with hist_tab:
        st.markdown('<div class="section-title">Generated Reports Archive</div>',
                    unsafe_allow_html=True)

        all_rpts = get_reports()
        if all_rpts.empty:
            st.info("No reports generated yet.")
            return

        t, sub, drft = st.columns(3)
        t.metric("📄 Total",    len(all_rpts))
        sub.metric("✅ Submitted", int((all_rpts["status"] == "Submitted").sum()))
        drft.metric("🟡 Drafted",  int((all_rpts["status"] == "Drafted").sum()))

        st.markdown("---")

        for _, row in all_rpts.iterrows():
            emoji, color = STATUS_META.get(row["status"], ("⚪", "#6b7280"))
            fp      = row.get("file_path")
            file_ok = bool(fp) and os.path.exists(str(fp))

            st.markdown(f"""
            <div style="background:#161b22;border:1px solid #30363d;
                        border-left:4px solid {color};border-radius:8px;
                        padding:10px 14px;margin-bottom:4px">
              <div style="display:flex;justify-content:space-between;
                          flex-wrap:wrap;gap:6px;align-items:center">
                <div>
                  <span style="font-weight:600;color:#e6edf3;font-size:.87rem">
                    {emoji} {row['report_type'].replace('_',' ')}
                  </span>
                  <span style="font-size:.73rem;color:#8b949e;margin-left:8px;
                               font-family:'IBM Plex Mono',monospace">
                    {row['project_name']} · {row['submission_date']}
                  </span>
                </div>
                <span style="background:{color}22;color:{color};
                             border:1px solid {color};border-radius:20px;
                             padding:2px 10px;font-size:.7rem;
                             font-family:'IBM Plex Mono',monospace">
                  {row['status']}
                </span>
              </div>
              <div style="font-size:.7rem;color:#4b5563;margin-top:3px">
                By {row['submitted_by']} · {str(row['created_at'])[:16]}
                {'· 📁 archived' if file_ok else ''}
              </div>
            </div>
            """, unsafe_allow_html=True)

            hc1, hc2, hc3 = st.columns([2, 2, 1])
            with hc1:
                if file_ok:
                    with open(fp, "rb") as fh:
                        st.download_button("⬇️ Download", fh.read(),
                                           file_name=os.path.basename(str(fp)),
                                           mime="application/pdf",
                                           key=f"hdl_{row['id']}",
                                           use_container_width=True)
                else:
                    st.caption("No archive file")
            with hc2:
                opts    = ["Drafted","Submitted","Archived"]
                new_s   = st.selectbox("", opts,
                                       index=opts.index(row["status"]) if row["status"] in opts else 0,
                                       key=f"hst_{row['id']}",
                                       label_visibility="collapsed")
                if new_s != row["status"]:
                    update_report_status(row["id"], new_s); st.rerun()
            with hc3:
                if st.button("🗑️", key=f"hdel_{row['id']}"):
                    delete_report(row["id"]); st.rerun()
