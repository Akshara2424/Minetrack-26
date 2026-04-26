"""
components/reports_dashboard.py — Module 2: Submission Tracking Dashboard

Layout
  ┌─────────────────────────────────────────────────────┐
  │  KPI cards: Generated · Pending · Submitted · Arch  │
  │  Type-split bar (MIS vs Delay)                       │
  ├─────────────────────────────────────────────────────┤
  │  Live Milestone Strip (Module 1 read-through)        │
  ├──────────────────────────┬──────────────────────────┤
  │    Quick Generate       │  Report Archive List      │
  | (from current state)    │  filters + cards + DL     │
  └──────────────────────────┴──────────────────────────┘

Module 1 Integration
  • "Generate Report from Current Milestone" reads live DB state
  • Auto-selects report type based on delay/overdue detection
  • One click → PDF built → saved to archive → DB record created
"""

import os
import streamlit as st
import pandas as pd
from datetime import date, timedelta

from db.database    import get_projects, get_milestones
from db.reports_db  import (
    init_reports_table, get_reports, get_report_stats,
    update_report_status, update_file_path, delete_report,
    save_report_record, auto_archive_old,
)
from reports.pdf_generator import generate_mis_quarterly, generate_delay_report
from utils.constants       import TODAY
from utils.alerts          import compute_urgency

# ── Local archive directory ───────────────────────────────────────
ARCHIVE_DIR = os.path.join(
    os.path.dirname(__file__), "..", "data", "reports_archive"
)

# ── Shared display constants ──────────────────────────────────────
STATUS_META = {
    "Drafted":   {"emoji": "🟡", "color": "#C8950C", "bg": "#FFF8E1"},
    "Submitted": {"emoji": "🟢", "color": "#003366", "bg": "#E9EFF8"},
    "Archived":  {"emoji": "⚫", "color": "#CDD4D9", "bg": "#F5F6F7"},
}
TYPE_LABEL = {
    "MIS_Quarterly": "MIS Quarterly",
    "Delay_Report":  "Delay Report",
}
DEFAULT_QUARTER = "Q4 FY 2025-26 (Jan–Mar 2026)"


# ══════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════

def _archive_pdf(pdf_bytes: bytes, filename: str, report_id: int) -> str:
    """Write PDF to local archive folder, update DB file_path. Returns path."""
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    path = os.path.join(ARCHIVE_DIR, filename)
    with open(path, "wb") as f:
        f.write(pdf_bytes)
    update_file_path(report_id, path)
    return path


def _generate_pdf(
    report_type_key: str,
    project_name: str,
    project_id: int,
    proj_loc: str,
    proj_start: str,
    milestones_df: pd.DataFrame,
    submission_date: date,
    quarter: str,
    submitted_by: str,
) -> tuple[bytes, str]:
    """Build PDF bytes + filename for either report type."""
    pname_safe = project_name.replace(" ", "_")
    if report_type_key == "MIS_Quarterly":
        pdf = generate_mis_quarterly(
            project_name=project_name, project_id=project_id,
            project_location=proj_loc, project_start=proj_start,
            submission_date=submission_date, quarter=quarter,
            milestones_df=milestones_df, submitted_by=submitted_by,
        )
        fname = f"MIS_{pname_safe}_{quarter[:2]}_{submission_date.strftime('%Y%m%d')}.pdf"
    else:
        pdf = generate_delay_report(
            project_name=project_name, project_id=project_id,
            project_location=proj_loc, submission_date=submission_date,
            milestones_df=milestones_df, submitted_by=submitted_by,
        )
        fname = f"Delay_{pname_safe}_{submission_date.strftime('%Y%m%d')}.pdf"
    return pdf, fname


# ══════════════════════════════════════════════════════════════════
# KPI CARDS
# ══════════════════════════════════════════════════════════════════

def _kpi_cards(stats: dict):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Reports Generated",  stats["total"])
    c2.metric(
        "Pending Submissions", stats["drafted"],
        delta=f"{stats['drafted']} to submit" if stats["drafted"] else None,
        delta_color="inverse",
    )
    c3.metric("Submitted",  stats["submitted"])
    c4.metric("Archived",   stats["archived"])

    # Type breakdown bar
    total = max(stats["total"], 1)
    mis_w   = int(stats["mis_count"]   / total * 100)
    delay_w = int(stats["delay_count"] / total * 100)

    st.markdown(f"""
    <div style="margin:.4rem 0 1rem">
      <div style="font-size:.7rem;color:#CDD4D9;margin-bottom:4px;
                  font-family:'IBM Plex Mono',monospace;letter-spacing:.05em">
        BREAKDOWN &nbsp;·&nbsp; MIS: {stats['mis_count']}
        &nbsp;|&nbsp; Delay: {stats['delay_count']}
      </div>
      <div style="display:flex;height:6px;border-radius:3px;overflow:hidden;background:#D6DADC">
        <div style="width:{mis_w}%;background:#0284c7"></div>
        <div style="width:{delay_w}%;background:#BF382A"></div>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# MILESTONE CONTEXT STRIP  (Module 1 live read)
# ══════════════════════════════════════════════════════════════════

def _milestone_strip(project_id: int):
    """
    Compact per-milestone status pills drawn live from Module 1 DB.
    Gives reporting context at a glance without switching tabs.
    """
    df = get_milestones(project_id)
    if df.empty:
        return

    st.markdown(
        '<div class="section-title">📌 Live Milestone State (Module 1)</div>',
        unsafe_allow_html=True,
    )

    cols = st.columns(len(df))
    for i, (_, row) in enumerate(df.iterrows()):
        td   = date.fromisoformat(str(row["target_date"]))
        info = compute_urgency(td, row["status"])
        with cols[i]:
            st.markdown(f"""
            <div style="background:#E9EFF8;border:1px solid {info['color']};
                        border-radius:6px;padding:8px 6px;text-align:center;">
              <div style="font-size:1.1rem">{info['emoji']}</div>
              <div style="font-size:.63rem;color:#000000;font-weight:600;
                          margin-top:2px;line-height:1.3">
                {row['name'][:20]}
              </div>
              <div style="font-size:.6rem;color:#CDD4D9;margin-top:2px;
                          font-family:'IBM Plex Mono',monospace">
                {td.strftime('%d %b')}
              </div>
            </div>
            """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# QUICK GENERATE BUTTON  (Module 1 integration)
# ══════════════════════════════════════════════════════════════════

def _quick_generate_section(project_id: int):
    """
    One-click 'Generate Report from Current Milestone' feature.
    Reads live Module 1 state, auto-detects best report type,
    generates PDF, saves to archive folder, creates DB record.
    """
    if not project_id:
        st.info("Select a project in the sidebar to enable quick generate.")
        return

    projects_df = get_projects()
    proj_row    = projects_df[projects_df["id"] == project_id]
    if proj_row.empty:
        return

    pname      = proj_row.iloc[0]["name"]
    ploc       = proj_row.iloc[0].get("location", "N/A") or "N/A"
    pstart     = proj_row.iloc[0]["start_date"]
    ms_df      = get_milestones(project_id)
    by         = st.session_state.get("username", "System")

    # Detect delays / overdue
    has_delays = any(
        r["status"] == "delayed" or (
            r["status"] != "complete"
            and date.fromisoformat(str(r["target_date"])) < TODAY
        )
        for _, r in ms_df.iterrows()
    ) if not ms_df.empty else False

    border_col  = "#BF382A" if has_delays else "#003366"
    suggestion  = "Delays detected — Delay Report recommended" if has_delays \
                  else "On track — MIS Quarterly recommended"

    st.markdown(f"""
    <div style="background:#E9EFF8;border:1px solid {border_col};
                border-radius:8px;padding:12px 16px;margin-bottom:.75rem">
      <div style="font-size:.82rem;font-weight:600;color:#000000">
        Generate Report from Current Milestone
      </div>
      <div style="font-size:.74rem;color:#CDD4D9;margin-top:4px">
        Project: <strong style="color:#000000">{pname}</strong>
        &nbsp;·&nbsp; {suggestion}
      </div>
    </div>
    """, unsafe_allow_html=True)

    col_mis, col_delay = st.columns(2)

    with col_mis:
        if st.button("MIS Quarterly", use_container_width=True, key="qg_mis"):
            _do_quick_gen("MIS_Quarterly", pname, project_id, ploc, pstart, ms_df, by)

    with col_delay:
        if st.button(
            "Delay Report", use_container_width=True, key="qg_delay",
            type="primary" if has_delays else "secondary",
        ):
            _do_quick_gen("Delay_Report", pname, project_id, ploc, pstart, ms_df, by)

    # Show download if a quick PDF is ready
    if st.session_state.get("_qpdf_bytes"):
        st.download_button(
            label     = f"⬇Download {st.session_state['_qpdf_label']}",
            data      = st.session_state["_qpdf_bytes"],
            file_name = st.session_state["_qpdf_fname"],
            mime      = "application/pdf",
            key       = "qg_dl",
            type      = "primary",
            use_container_width=True,
        )


def _do_quick_gen(rtype, pname, pid, ploc, pstart, ms_df, by):
    with st.spinner("Generating PDF…"):
        try:
            pdf, fname = _generate_pdf(
                report_type_key=rtype, project_name=pname,
                project_id=pid, proj_loc=ploc, proj_start=pstart,
                milestones_df=ms_df, submission_date=TODAY,
                quarter=DEFAULT_QUARTER, submitted_by=by,
            )
            rid  = save_report_record(
                project_id=pid, report_type=rtype,
                quarter=DEFAULT_QUARTER if rtype == "MIS_Quarterly" else "N/A",
                submission_date=TODAY.isoformat(),
                submitted_by=by, status="Drafted",
            )
            _archive_pdf(pdf, fname, rid)

            st.session_state["_qpdf_bytes"] = pdf
            st.session_state["_qpdf_fname"] = fname
            st.session_state["_qpdf_label"] = rtype.replace("_", " ")
            st.success(f"{rtype.replace('_',' ')} generated & archived.")
            st.rerun()
        except Exception as ex:
            st.error(f" {ex}")


# ══════════════════════════════════════════════════════════════════
# REPORT ARCHIVE LIST
# ══════════════════════════════════════════════════════════════════

def _filters(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    f1, f2, f3 = st.columns(3)
    with f1:
        projs = ["All"] + sorted(df["project_name"].unique().tolist())
        sp = st.selectbox("Project", projs, key="f_proj")
    with f2:
        stats = ["All", "Drafted", "Submitted", "Archived"]
        ss = st.selectbox("Status", stats, key="f_stat")
    with f3:
        types = ["All", "MIS_Quarterly", "Delay_Report"]
        st_ = st.selectbox("Type", types, key="f_type")

    if sp  != "All": df = df[df["project_name"] == sp]
    if ss  != "All": df = df[df["status"]        == ss]
    if st_ != "All": df = df[df["report_type"]   == st_]

    st.caption(f"Showing {len(df)} report(s)")
    return df


def _report_list(df: pd.DataFrame):
    if df.empty:
        st.info("No reports match the current filters.")
        return

    for _, row in df.iterrows():
        meta     = STATUS_META.get(row["status"], STATUS_META["Drafted"])
        rtype    = TYPE_LABEL.get(row["report_type"], row["report_type"])
        fp       = row.get("file_path")
        file_ok  = bool(fp) and os.path.exists(str(fp))

        # Card
        st.markdown(f"""
        <div style="background:#E9EFF8;border:1px solid #D6DADC;
                    border-left:4px solid {meta['color']};border-radius:8px;
                    padding:12px 16px;margin-bottom:4px">
          <div style="display:flex;justify-content:space-between;
                      align-items:flex-start;flex-wrap:wrap;gap:8px">
            <div style="flex:1;min-width:180px">
              <div style="font-weight:600;color:#000000;font-size:.88rem">
                {rtype}
              </div>
              <div style="font-size:.72rem;color:#CDD4D9;margin-top:3px;
                          font-family:'IBM Plex Mono',monospace">
                {row['project_name']}
                &nbsp;·&nbsp; {row['quarter']}
                &nbsp;·&nbsp; {row['submission_date']}
              </div>
              <div style="font-size:.68rem;color:#CDD4D9;margin-top:2px">
                By {row['submitted_by']}
                &nbsp;·&nbsp; Generated {str(row['created_at'])[:16]}
                {'&nbsp;·&nbsp; local archive' if file_ok else ''}
              </div>
            </div>
            <span style="background:{meta['bg']};color:{meta['color']};
                         border:1px solid {meta['color']};border-radius:20px;
                         padding:2px 10px;font-size:.7rem;white-space:nowrap;
                         font-family:'IBM Plex Mono',monospace;font-weight:600">
              {meta['emoji']} {row['status']}
            </span>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Action row: download | status change | mark submitted | delete
        ca, cb, cc, cd = st.columns([3, 2, 2, 1])

        with ca:
            if file_ok:
                with open(fp, "rb") as fh:
                    pdf_data = fh.read()
                st.download_button(
                    label     = "⬇️ Download PDF",
                    data      = pdf_data,
                    file_name = os.path.basename(str(fp)),
                    mime      = "application/pdf",
                    key       = f"dl_{row['id']}",
                    use_container_width=True,
                )
            else:
                st.caption("Not in local archive")

        with cb:
            opts    = ["Drafted", "Submitted", "Archived"]
            cur_idx = opts.index(row["status"]) if row["status"] in opts else 0
            new_s   = st.selectbox(
                "Status", opts, index=cur_idx,
                key=f"rs_{row['id']}", label_visibility="collapsed",
            )
            if new_s != row["status"]:
                update_report_status(row["id"], new_s)
                st.rerun()

        with cc:
            if row["status"] == "Drafted":
                if st.button("Mark Submitted", key=f"ms_{row['id']}",
                             use_container_width=True):
                    update_report_status(row["id"], "Submitted")
                    st.rerun()
            elif row["status"] == "Submitted":
                if st.button("Archive", key=f"arc_{row['id']}",
                             use_container_width=True):
                    update_report_status(row["id"], "Archived")
                    st.rerun()

        with cd:
            if st.button("🗑️", key=f"del_{row['id']}", help="Delete record"):
                delete_report(row["id"])
                st.rerun()

        st.markdown(
            '<hr style="border:0;border-top:1px solid #21262d;margin:2px 0 6px">',
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════
# MAIN RENDER
# ══════════════════════════════════════════════════════════════════

def render(active_project_id: int = None):
    """
    Top-level render for the Reports Dashboard tab.
    Wire into app.py manager tab block.
    """
    init_reports_table()

    # Silent auto-archive on first load per session
    if not st.session_state.get("_archive_ran"):
        n = auto_archive_old(90)
        st.session_state["_archive_ran"] = True
        if n:
            st.toast(f"🗄️ {n} report(s) auto-archived (>90 days)", icon="📦")

    # ── Page header ──────────────────────────────────────────────
    st.markdown("""
    <div style="background:#E9EFF8;border:1px solid #003366;border-radius:8px;
                padding:10px 16px;margin-bottom:1rem">
      <span style="color:#003366;font-family:'IBM Plex Mono',monospace;font-size:.8rem">
        REPORTS DASHBOARD — MODULE 2
      </span>
      <span style="color:#CDD4D9;font-size:.74rem;margin-left:1rem">
        Submission tracking · Auto-archive · Module 1 integration
      </span>
    </div>
    """, unsafe_allow_html=True)

    # ── KPI cards ────────────────────────────────────────────────
    stats = get_report_stats()
    _kpi_cards(stats)

    st.markdown("---")

    # ── Live milestone context strip ─────────────────────────────
    if active_project_id:
        _milestone_strip(active_project_id)
        st.markdown("---")

    # ── Two-column layout: quick gen | archive list ───────────────
    left, right = st.columns([1, 2], gap="large")

    with left:
        st.markdown(
            '<div class="section-title">⚡ Quick Generate</div>',
            unsafe_allow_html=True,
        )
        _quick_generate_section(active_project_id)

    with right:
        st.markdown(
            '<div class="section-title">Report Archive</div>',
            unsafe_allow_html=True,
        )
        all_reports = get_reports()
        filtered    = _filters(all_reports)
        _report_list(filtered)

    # ── Archive folder footer ─────────────────────────────────────
    n_files = len([
        f for f in os.listdir(ARCHIVE_DIR)
        if f.endswith(".pdf")
    ]) if os.path.exists(ARCHIVE_DIR) else 0

    st.markdown("---")
    st.markdown(f"""
    <div style="background:#E9EFF8;border:1px solid #D6DADC;border-radius:8px;
                padding:8px 14px">
      <span style="font-size:.72rem;color:#CDD4D9;font-family:'IBM Plex Mono',monospace">
        Archive folder: <code style="color:#C8950C">{ARCHIVE_DIR}</code>
        &nbsp;·&nbsp; {n_files} PDF(s) stored locally
      </span>
    </div>
    """, unsafe_allow_html=True)
