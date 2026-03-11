"""
app.py — MineGuard Module 1 entry point.

Responsibilities (ONLY):
  1. st.set_page_config + global CSS
  2. Session state init + DB init
  3. Login gate
  4. App header
  5. Sidebar (project CRUD + logout)
  6. Role-based tab routing → delegates to components/

Run with:
    streamlit run app.py
"""

import sys
import os
import sqlite3
import streamlit as st
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))

from auth           import render_login, init_session
from db             import init_db, get_projects, create_project, delete_project, get_milestones
from utils          import TODAY, validate_project_start
from components     import dashboard, monitoring, update_form, add_milestone, officer_view


# ══════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="MineGuard — Module 1",
    page_icon="⛏️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ══════════════════════════════════════════════════════════════════
# GLOBAL CSS
# ══════════════════════════════════════════════════════════════════

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');

html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
h1, h2, h3                 { font-family: 'IBM Plex Mono', monospace; }

[data-testid="stSidebar"] {
    background: #0d1117;
    border-right: 2px solid #f0a500;
}
[data-testid="stSidebar"] * { color: #e6edf3 !important; }

[data-testid="metric-container"] {
    background: #161b22; border: 1px solid #30363d;
    border-radius: 8px; padding: 12px;
}

/* ── Role badges ── */
.role-badge {
    display: inline-block; padding: 3px 14px; border-radius: 20px;
    font-family: 'IBM Plex Mono', monospace; font-size: 0.8rem; font-weight: 600;
}
.role-manager { background:#002d4a; color:#7dd3fc; border:1px solid #0284c7; }
.role-officer { background:#1a2a00; color:#86efac; border:1px solid #16a34a; }

/* ── Status badges ── */
.badge {
    display: inline-block; padding: 2px 10px; border-radius: 20px;
    font-size: 0.75rem; font-weight: 600; font-family: 'IBM Plex Mono', monospace;
}
.badge-pending     { background:#2d2d00; color:#f0e68c; border:1px solid #a89020; }
.badge-in_progress { background:#002d4a; color:#7dd3fc; border:1px solid #0284c7; }
.badge-complete    { background:#003d1f; color:#86efac; border:1px solid #16a34a; }
.badge-delayed     { background:#3d0000; color:#fca5a5; border:1px solid #dc2626; }

/* ── Progress bar ── */
.timeline-bar  { height:8px; border-radius:4px; background:#30363d; margin:4px 0; overflow:hidden; }
.timeline-fill { height:100%; border-radius:4px; }

/* ── Overdue chip ── */
.overdue-chip {
    background:#3d0000; color:#fca5a5; border:1px solid #dc2626;
    border-radius:4px; padding:2px 8px; font-size:0.7rem;
    font-family:'IBM Plex Mono',monospace;
}

/* ── Section title ── */
.section-title {
    color:#f0a500; font-family:'IBM Plex Mono',monospace; font-size:0.8rem;
    letter-spacing:0.15em; text-transform:uppercase;
    border-bottom:1px solid #30363d; padding-bottom:4px; margin:1.5rem 0 0.75rem;
}

/* ── App header ── */
.app-header {
    background: linear-gradient(135deg,#0d1117 0%,#1c2836 50%,#0d1117 100%);
    border-bottom: 3px solid #f0a500;
    padding: 1rem 1.5rem; margin-bottom: 1.5rem; border-radius: 8px;
}
.app-header h1 { color:#f0a500; margin:0; font-size:clamp(1.1rem,4vw,1.7rem); }
.app-header p  { color:#8b949e; margin:4px 0 0; font-size:0.82rem; }

/* ── Access denied ── */
.access-denied {
    background:#1a0000; border:2px solid #dc2626; border-radius:8px;
    padding:1.5rem; text-align:center; color:#fca5a5;
    font-family:'IBM Plex Mono',monospace; margin:1rem 0;
}

/* ── Info card (login page) ── */
.info-card {
    background:#161b22; border:1px solid #30363d; border-radius:8px; padding:12px 16px;
}

/* ── Mobile ── */
@media (max-width: 640px) {
    [data-testid="column"] { min-width:100% !important; flex:1 1 100% !important; }
    .stDataFrame            { font-size:12px; }
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# INIT
# ══════════════════════════════════════════════════════════════════

init_session()
init_db()


# ══════════════════════════════════════════════════════════════════
# LOGIN GATE
# ══════════════════════════════════════════════════════════════════

if not st.session_state.logged_in:
    render_login()
    st.stop()


# ══════════════════════════════════════════════════════════════════
# APP HEADER
# ══════════════════════════════════════════════════════════════════

role       = st.session_state.role
badge_cls  = "role-manager" if role == "Manager" else "role-officer"
role_icon  = "👔 Manager"  if role == "Manager" else "👷 Officer"

st.markdown(f"""
<div class="app-header">
  <h1>⛏️ MineGuard — Compliance Module 1</h1>
  <p>
    <span class="role-badge {badge_cls}">{role_icon}</span>
    &nbsp;·&nbsp; {st.session_state.username}
    &nbsp;·&nbsp; Demo date: <strong>March 10, 2026</strong>
  </p>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# SIDEBAR — project selector + management + logout
# ══════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown(f"""
    <div style="margin-bottom:12px;">
      <span class="role-badge {badge_cls}">{role_icon}</span>
      <div style="color:#8b949e;font-size:0.8rem;margin-top:4px;">
        {st.session_state.username}
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 📁 Projects")
    st.markdown("---")

    projects_df = get_projects()

    if projects_df.empty:
        st.info("No projects yet.")
        st.session_state.selected_project_id   = None
        st.session_state.selected_project_name = None
    else:
        opts = dict(zip(projects_df["name"], projects_df["id"]))
        sel  = st.selectbox("Active Project", list(opts.keys()))
        st.session_state.selected_project_id   = opts[sel]
        st.session_state.selected_project_name = sel

    # ── Manager: create / delete projects ──
    if role == "Manager":
        st.markdown('<div class="section-title">New Project</div>', unsafe_allow_html=True)

        with st.form("new_proj", clear_on_submit=True):
            p_name  = st.text_input("Project Name *", placeholder="e.g. Jharia Block-4")
            p_loc   = st.text_input("Location",       placeholder="e.g. Dhanbad, Jharkhand")
            p_start = st.date_input("Start Date *",   value=TODAY)

            if st.form_submit_button("➕ Create Project", use_container_width=True):
                errors = (["Project name is required."] if not p_name.strip()
                          else validate_project_start(p_start))
                if errors:
                    for e in errors:
                        st.error(e)
                else:
                    try:
                        create_project(p_name.strip(), p_start, p_loc.strip(), role)
                        st.success(f"✅ '{p_name}' created with 5 milestones.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("❌ A project with this name already exists.")
                    except Exception as ex:
                        st.error(f"❌ Error: {ex}")

        if st.session_state.selected_project_id:
            st.markdown("---")
            if st.button("🗑️ Delete Active Project", use_container_width=True, type="secondary"):
                try:
                    delete_project(st.session_state.selected_project_id)
                    st.session_state.selected_project_id   = None
                    st.session_state.selected_project_name = None
                    st.warning("Project deleted.")
                    st.rerun()
                except Exception as ex:
                    st.error(f"❌ {ex}")
    else:
        st.caption("⚠️ Project creation requires Manager role.")

    st.markdown("---")
    if st.button("🚪 Logout", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()


# ══════════════════════════════════════════════════════════════════
# MAIN CONTENT — role-based tab routing
# ══════════════════════════════════════════════════════════════════

pid   = st.session_state.selected_project_id
pname = st.session_state.selected_project_name

if not pid:
    st.markdown("""
    <div style="text-align:center;padding:3rem;color:#8b949e;">
      <h2 style="color:#f0a500">👈 Select or create a project</h2>
      <p>Use the sidebar to get started.</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# Fetch shared data once
milestones_df = get_milestones(pid)
start_str     = projects_df.loc[projects_df["id"] == pid, "start_date"].values
project_start = date.fromisoformat(start_str[0]) if len(start_str) else TODAY

# ── Officer: 2-tab simplified view ──────────────────────────────
if role == "Officer":
    officer_view.render(pid, project_start, milestones_df)

# ── Manager: full 4-tab view ─────────────────────────────────────
else:
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Dashboard",
        "📡 Monitor & Alerts",
        "✏️ Update Milestones",
        "➕ Add Milestone",
    ])
    with tab1:
        dashboard.render(pid, pname, milestones_df)
    with tab2:
        monitoring.render(milestones_df)
    with tab3:
        update_form.render(milestones_df, project_start)
    with tab4:
        add_milestone.render(pid)