"""components/dashboard.py — Tab 1: KPI metrics + timeline. Manager only."""
import streamlit as st
import pandas as pd
from datetime import date
from auth.guards import require_role
from db import get_projects
from utils.alerts import compute_urgency
from utils.constants import TODAY

def render(project_id, project_name, milestones_df):
    if not require_role("Manager"): return
    st.markdown(f"## {project_name}")
    _kpi(milestones_df)
    st.markdown('<div class="section-title">Milestone Timeline</div>', unsafe_allow_html=True)
    if milestones_df.empty:
        st.info("No milestones yet."); return
    proj_row = get_projects()
    start_str = proj_row.loc[proj_row["id"] == project_id, "start_date"].values[0]
    proj_start = date.fromisoformat(start_str)
    proj_end = date.fromisoformat(milestones_df["target_date"].max())
    span = max((proj_end - proj_start).days, 1)
    for _, row in milestones_df.iterrows():
        td = date.fromisoformat(row["target_date"])
        bar_pct = int((td - proj_start).days / span * 100)
        info = compute_urgency(td, row["status"])
        is_over = (td < TODAY and row["status"] != "complete")
        overdue_tag = f'<span class="overdue-chip">⚠ OVERDUE {(TODAY-td).days}d</span>' if is_over else ""
        fill = "#16a34a" if row["status"]=="complete" else "#f0a500" if row["status"]=="in_progress" else "#dc2626" if (is_over or row["status"]=="delayed") else "#4b5563"
        notes_html = f'<div style="font-size:0.73rem;color:#8b949e;margin-top:4px;">📝 {row["notes"]}</div>' if row["notes"] else ""
        by_html = f'<span style="font-size:0.7rem;color:#4b5563;margin-left:8px;">by {row["submitted_by"]}</span>' if row.get("submitted_by") else ""
        st.markdown(f"""
        <div style="background:#161b22;border:1px solid #30363d;border-left:4px solid {info['color']};border-radius:8px;padding:12px 16px;margin-bottom:8px;">
          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;">
            <div><span style="font-weight:600;color:#e6edf3;">{row['name']}</span>{by_html}&nbsp;{overdue_tag}</div>
            <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
              <span class="badge badge-{row['status']}">{row['status'].upper()}</span>
              <span style="font-size:0.78rem;color:#8b949e;font-family:'IBM Plex Mono',monospace;">{td.strftime('%d %b %Y')}</span>
            </div>
          </div>
          <div class="timeline-bar" style="margin-top:8px;"><div class="timeline-fill" style="width:{bar_pct}%;background:{fill};"></div></div>
          {notes_html}
        </div>""", unsafe_allow_html=True)
    with st.expander("🗃️ Raw Data Table"):
        disp = milestones_df[["name","target_date","actual_date","status","notes","submitted_by"]].copy()
        disp.columns = ["Milestone","Target Date","Actual Date","Status","Notes","Submitted By"]
        st.dataframe(disp, use_container_width=True, hide_index=True)

def _kpi(milestones_df):
    total = len(milestones_df)
    done = int((milestones_df["status"]=="complete").sum())
    delayed = int((milestones_df["status"]=="delayed").sum())
    overdue = sum(1 for _,r in milestones_df.iterrows() if r["status"]!="complete" and date.fromisoformat(r["target_date"])<TODAY)
    pct = int(done/max(total,1)*100)
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("📋 Total",total); c2.metric("✅ Completed",done,delta=f"{pct}%")
    c3.metric("⚠️ Delayed",delayed); c4.metric("🔥 Overdue",overdue)
    bar_color = "#16a34a" if pct==100 else ("#f0a500" if pct>=50 else "#dc2626")
    st.markdown(f'''<div style="margin:0.5rem 0 1.5rem;">
      <div style="font-size:0.75rem;color:#8b949e;margin-bottom:4px;">Overall Progress — {pct}%</div>
      <div class="timeline-bar"><div class="timeline-fill" style="width:{pct}%;background:{bar_color};"></div></div>
    </div>''', unsafe_allow_html=True)