"""components/dashboard.py — Tab 1: KPI metrics + timeline. Manager only."""
import streamlit as st
import pandas as pd
import os
import base64
from datetime import date
from auth.guards import require_role
from db import get_projects, create_project
from utils.alerts import compute_urgency
from utils.constants import TODAY
from utils.validators import validate_project_start
import sqlite3

def get_image_base64(image_path):
    """Convert image file to base64 data URI."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    full_path = os.path.join(base_dir, image_path)
    if not os.path.exists(full_path):
        return None
    with open(full_path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    ext = image_path.split('.')[-1].lower()
    mime = f"image/{ext}" if ext != "jpg" else "image/jpeg"
    return f"data:{mime};base64,{b64}"

def render(project_id, project_name, milestones_df):
    if not require_role("Manager"): return
    
    # ══════════════════════════════════════════════════════════════════
    # DASHBOARD CONTENT
    # ══════════════════════════════════════════════════════════════════
    col1, col2 = st.columns([0.85, 0.15])
    with col1:
        st.markdown(f"## {project_name}")
    with col2:
        if st.button("New Project", key="dashboard_new_proj", use_container_width=True):
            st.session_state.show_create_modal_main = True
    
    # Modal form for new project
    if st.session_state.get("show_create_modal_main"):
        st.markdown('<div style="background:#EEF2F7;border:1px solid #CBD5E0;border-radius:8px;padding:20px;margin-bottom:20px;">', unsafe_allow_html=True)
        st.markdown('<h3 style="color:#1B3A6B;margin-top:0;">Create New Project</h3>', unsafe_allow_html=True)
        
        with st.form("new_project_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                p_name = st.text_input("Project Name", placeholder="e.g. Jharia Block-4")
                p_start = st.date_input("Start Date", value=TODAY)
            with c2:
                p_loc = st.text_input("Location", placeholder="e.g. Dhanbad, Jharkhand")
            
            form_col1, form_col2 = st.columns(2)
            with form_col1:
                if st.form_submit_button("Create", use_container_width=True):
                    errs = ([] if p_name.strip() else ["Project name is required."]) + validate_project_start(p_start)
                    if errs:
                        for e in errs:
                            st.error(e)
                    else:
                        try:
                            create_project(p_name.strip(), p_start, p_loc.strip(), "Manager")
                            st.success(f"Project '{p_name}' created successfully.")
                            st.session_state.show_create_modal_main = False
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("A project with that name already exists.")
                        except Exception as ex:
                            st.error(f"Error: {ex}")
            with form_col2:
                if st.form_submit_button("Cancel", use_container_width=True):
                    st.session_state.show_create_modal_main = False
                    st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
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
        overdue_tag = f'<span class="overdue-chip"> OVERDUE {(TODAY-td).days}d</span>' if is_over else ""
        fill = "#003366" if row["status"]=="complete" else "#C8950C" if row["status"]=="in_progress" else "#BF382A" if (is_over or row["status"]=="delayed") else "#CDD4D9"
        notes_html = f'<div style="font-size:0.73rem;color:#CDD4D9;margin-top:4px;">[Notes] {row["notes"]}</div>' if row["notes"] else ""
        by_html = f'<span style="font-size:0.7rem;color:#CDD4D9;margin-left:8px;">by {row["submitted_by"]}</span>' if row.get("submitted_by") else ""
        st.markdown(f"""
        <div style="background:#E9EFF8;border:1px solid #D6DADC;border-left:4px solid {info['color']};border-radius:8px;padding:12px 16px;margin-bottom:8px;">
          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;">
            <div><span style="font-weight:600;color:#000000;">{row['name']}</span>{by_html}&nbsp;{overdue_tag}</div>
            <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
              <span class="badge badge-{row['status']}">{row['status'].upper()}</span>
              <span style="font-size:0.78rem;color:#CDD4D9;font-family:'IBM Plex Mono',monospace;">{td.strftime('%d %b %Y')}</span>
            </div>
          </div>
          <div class="timeline-bar" style="margin-top:8px;"><div class="timeline-fill" style="width:{bar_pct}%;background:{fill};"></div></div>
          {notes_html}
        </div>""", unsafe_allow_html=True)
    with st.expander("Raw Data Table"):
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
    c1.metric("Total",total); c2.metric("Completed",done,delta=f"{pct}%")
    c3.metric("Delayed",delayed); c4.metric("Overdue",overdue)
    bar_color = "#003366" if pct==100 else ("#C8950C" if pct>=50 else "#BF382A")
    st.markdown(f'''<div style="margin:0.5rem 0 1.5rem;">
      <div style="font-size:0.75rem;color:#CDD4D9;margin-bottom:4px;">Overall Progress — {pct}%</div>
      <div class="timeline-bar"><div class="timeline-fill" style="width:{pct}%;background:{bar_color};"></div></div>
    </div>''', unsafe_allow_html=True)