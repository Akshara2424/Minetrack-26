"""
app.py — MineGuard entry point (Module 1 + Module 2)
Run: streamlit run app.py
"""

import sys, os, sqlite3
import streamlit as st
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))

from auth        import init_session, render_login
from db          import init_db, get_projects, create_project, delete_project, get_milestones
from components  import (
    dashboard, monitoring, update_form, add_milestone,
    officer_view, report_form, reports_dashboard,
)
from utils.constants  import TODAY
from utils.validators import validate_project_start
from db.reports_db    import init_reports_table

# ══════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="MineGuard — Compliance",
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
html,body,[class*="css"]{font-family:'IBM Plex Sans',sans-serif}
h1,h2,h3{font-family:'IBM Plex Mono',monospace}

[data-testid="stSidebar"]{background:#0d1117;border-right:2px solid #f0a500}
[data-testid="stSidebar"] *{color:#e6edf3 !important}
[data-testid="metric-container"]{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px}

.role-badge{display:inline-block;padding:3px 14px;border-radius:20px;
  font-family:'IBM Plex Mono',monospace;font-size:.8rem;font-weight:600}
.role-manager{background:#002d4a;color:#7dd3fc;border:1px solid #0284c7}
.role-officer{background:#1a2a00;color:#86efac;border:1px solid #16a34a}

.badge{display:inline-block;padding:2px 10px;border-radius:20px;
  font-size:.75rem;font-weight:600;font-family:'IBM Plex Mono',monospace}
.badge-pending    {background:#2d2d00;color:#f0e68c;border:1px solid #a89020}
.badge-in_progress{background:#002d4a;color:#7dd3fc;border:1px solid #0284c7}
.badge-complete   {background:#003d1f;color:#86efac;border:1px solid #16a34a}
.badge-delayed    {background:#3d0000;color:#fca5a5;border:1px solid #dc2626}

.timeline-bar {height:8px;border-radius:4px;background:#30363d;margin:4px 0;overflow:hidden}
.timeline-fill{height:100%;border-radius:4px}

.overdue-chip{background:#3d0000;color:#fca5a5;border:1px solid #dc2626;
  border-radius:4px;padding:2px 8px;font-size:.7rem;font-family:'IBM Plex Mono',monospace}

.section-title{color:#f0a500;font-family:'IBM Plex Mono',monospace;font-size:.8rem;
  letter-spacing:.15em;text-transform:uppercase;border-bottom:1px solid #30363d;
  padding-bottom:4px;margin:1.5rem 0 .75rem}

.app-header{background:linear-gradient(135deg,#0d1117 0%,#1c2836 50%,#0d1117 100%);
  border-bottom:3px solid #f0a500;padding:1rem 1.5rem;margin-bottom:1.5rem;border-radius:8px}
.app-header h1{color:#f0a500;margin:0;font-size:clamp(1.1rem,4vw,1.7rem)}
.app-header p {color:#8b949e;margin:4px 0 0;font-size:.82rem}

.access-denied{background:#1a0000;border:2px solid #dc2626;border-radius:8px;
  padding:1.5rem;text-align:center;color:#fca5a5;font-family:'IBM Plex Mono',monospace;margin:1rem 0}

.info-card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px 16px}

@media(max-width:640px){
  [data-testid="column"]{min-width:100% !important;flex:1 1 100% !important}
  .stDataFrame{font-size:12px}
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# INIT
# ══════════════════════════════════════════════════════════════════
init_session()
init_db()
init_reports_table()

# ── Login gate ───────────────────────────────────────────────────
if not st.session_state.logged_in:
    render_login()
    st.stop()

# ══════════════════════════════════════════════════════════════════
# APP HEADER
# ══════════════════════════════════════════════════════════════════
role      = st.session_state.role
badge_cls = "role-manager" if role == "Manager" else "role-officer"
role_icon = "👔 Manager"   if role == "Manager" else "👷 Officer"

st.markdown(f"""
<div class="app-header">
  <h1>⛏️ MineGuard — Compliance System</h1>
  <p>
    <span class="role-badge {badge_cls}">{role_icon}</span>
    &nbsp;·&nbsp; {st.session_state.username}
    &nbsp;·&nbsp; Demo date: <strong>March 10, 2026</strong>
    &nbsp;·&nbsp; Modules: 1 (Tracking) · 2 (Reporting)
  </p>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(f"""
    <div style="margin-bottom:12px">
      <span class="role-badge {badge_cls}">{role_icon}</span>
      <div style="color:#8b949e;font-size:.8rem;margin-top:4px">
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

    if role == "Manager":
        st.markdown('<div class="section-title">New Project</div>',
                    unsafe_allow_html=True)
        with st.form("new_proj", clear_on_submit=True):
            p_name  = st.text_input("Project Name *", placeholder="e.g. Jharia Block-4")
            p_loc   = st.text_input("Location",       placeholder="e.g. Dhanbad, Jharkhand")
            p_start = st.date_input("Start Date *",   value=TODAY)
            if st.form_submit_button("➕ Create Project", use_container_width=True):
                errs = []
                if not p_name.strip(): errs.append("Name required.")
                else: errs += validate_project_start(p_start)
                if errs:
                    for e in errs: st.error(e)
                else:
                    try:
                        create_project(p_name.strip(), p_start, p_loc.strip(), role)
                        st.success(f"✅ '{p_name}' created.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("❌ Name already exists.")
                    except Exception as ex:
                        st.error(f"❌ {ex}")

        if st.session_state.selected_project_id:
            st.markdown("---")
            if st.button("🗑️ Delete Active Project", use_container_width=True,
                         type="secondary"):
                try:
                    delete_project(st.session_state.selected_project_id)
                    st.session_state.selected_project_id   = None
                    st.session_state.selected_project_name = None
                    st.warning("Deleted.")
                    st.rerun()
                except Exception as ex:
                    st.error(f"❌ {ex}")
    else:
        st.caption("⚠️ Project creation requires Manager role.")

    st.markdown("---")
    if st.button("🚪 Logout", use_container_width=True):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()

# ══════════════════════════════════════════════════════════════════
# MAIN CONTENT
# ══════════════════════════════════════════════════════════════════
pid   = st.session_state.selected_project_id
pname = st.session_state.selected_project_name

if not pid:
    st.markdown("""
    <div style="text-align:center;padding:3rem;color:#8b949e">
      <h2 style="color:#f0a500">👈 Select or create a project</h2>
      <p>Use the sidebar to get started.</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

projects_df   = get_projects()
start_str     = projects_df.loc[projects_df["id"] == pid, "start_date"].values
project_start = date.fromisoformat(start_str[0]) if len(start_str) else TODAY
milestones_df = get_milestones(pid)

# ── Officer: simplified 2-tab view ─────────────────────────────
if role == "Officer":
    officer_view.render(pid, project_start, milestones_df)

# ── Manager: full 6-tab view ────────────────────────────────────
else:
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Dashboard",
        "📡 Monitor & Alerts",
        "✏️ Update Milestones",
        "➕ Add Milestone",
        "📑 Reports",           # Module 2 — entry form
        "🗂️ Report Dashboard",  # Module 2 — submission tracking
    ])

    with tab1: dashboard.render(pid, pname, milestones_df)
    with tab2: monitoring.render(milestones_df)
    with tab3: update_form.render(milestones_df, project_start)
    with tab4: add_milestone.render(pid)
    with tab5: report_form.render(active_project_id=pid)
    with tab6: reports_dashboard.render(active_project_id=pid)
