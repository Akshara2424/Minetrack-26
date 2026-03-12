"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  Angara — Integrated Compliance System                                    ║
║  Modules 1 & 2 combined into a single multi-page Streamlit app               ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Run:    streamlit run app.py                                                ║
║  Init:   python init_db.py          (seed demo data)                         ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  SIDEBAR NAVIGATION                                                          ║
║    Module 1 — Compliance Tracker                                             ║
║      📊  Dashboard          (Manager only)                                   ║
║      📡  Monitor & Alerts   (Manager only)                                   ║
║      ✏️   Update Milestones  (All roles)                                      ║
║      ➕  Add Milestone       (All roles)                                     ║
║    Module 2 — Reports                                                        ║
║      📑  Generate Report     (All roles)                                     ║
║      🗂️   Report Dashboard   (Manager only)                                   ║
║      ⬇️   Export ZIP          (Manager only — sidebar button)                 ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  DATA FLOW                                                                   ║
║    Mod 1 entry → milestones table → Mod 2 PDF (no re-keying)                ║
║    PDF generated → archived to data/reports_archive/ → ZIP export           ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  SCALABILITY NOTE                                                            ║
║    DB is SQLite by default. Migratable to PostgreSQL:                        ║
║      1. pip install psycopg2-binary sqlalchemy                               ║
║      2. Set DB_PATH in utils/constants.py to a pg DSN string                 ║
║      3. Replace sqlite3.connect() in db/database.py + db/reports_db.py       ║
║         with sqlalchemy engine or psycopg2.connect(DSN)                      ║
║      4. Drop PRAGMA lines (SQLite-only)                                      ║
║      5. Add pg connection pool (e.g. psycopg2.pool.ThreadedConnectionPool)   ║
║    Schema uses ANSI SQL only — no SQLite-specific types.                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import sys, os, io, zipfile, sqlite3
import streamlit as st
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auth             import init_session, render_login
from db               import init_db, get_projects, create_project, delete_project, get_milestones
from db.reports_db    import init_reports_table, get_report_stats
from components       import (
    dashboard, monitoring, update_form, add_milestone,
    officer_view, report_form, reports_dashboard,
)
from utils.constants  import TODAY
from utils.validators import validate_project_start

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
ARCHIVE_DIR = os.path.join(BASE_DIR, "data", "reports_archive")

# ══════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Angara — Compliance",
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
html,body,[class*="css"]{font-family:'IBM Plex Sans',sans-serif;background:#FFFFFF;color:#000000}
h1,h2,h3{font-family:'IBM Plex Mono',monospace;color:#003366}

[data-testid="stSidebar"]{background:#E9EFF8;border-right:3px solid #003366}
[data-testid="stSidebar"] *{color:#000000 !important}
[data-testid="metric-container"]{background:#E9EFF8;border:1px solid #D6DADC;border-radius:8px;padding:12px}

.role-badge{display:inline-block;padding:3px 14px;border-radius:20px;
  font-family:'IBM Plex Mono',monospace;font-size:.8rem;font-weight:600}
.role-manager{background:#E9EFF8;color:#003366;border:1px solid #003366}
.role-officer{background:#FDEDEB;color:#BF382A;border:1px solid #BF382A}

.badge{display:inline-block;padding:2px 10px;border-radius:20px;
  font-size:.75rem;font-weight:600;font-family:'IBM Plex Mono',monospace}
.badge-pending    {background:#FFF8E1;color:#C8950C;border:1px solid #C8950C}
.badge-in_progress{background:#E9EFF8;color:#003366;border:1px solid #003366}
.badge-complete   {background:#E9EFF8;color:#003366;border:1px solid #003366}
.badge-delayed    {background:#FDEDEB;color:#BF382A;border:1px solid #BF382A}

.timeline-bar {height:8px;border-radius:4px;background:#D6DADC;margin:4px 0;overflow:hidden}
.timeline-fill{height:100%;border-radius:4px;background:#003366}
.overdue-chip{background:#FDEDEB;color:#BF382A;border:1px solid #BF382A;
  border-radius:4px;padding:2px 8px;font-size:.7rem;font-family:'IBM Plex Mono',monospace}

.section-title{color:#003366;font-family:'IBM Plex Mono',monospace;font-size:.8rem;
  letter-spacing:.15em;text-transform:uppercase;border-bottom:2px solid #D6DADC;
  padding-bottom:4px;margin:1.5rem 0 .75rem;font-weight:600}

.app-header{background:linear-gradient(135deg,#FFFFFF 0%,#E9EFF8 50%,#FFFFFF 100%);
  border-bottom:3px solid #003366;padding:1rem 1.5rem;margin-bottom:1.5rem;border-radius:8px;box-shadow:0 2px 4px rgba(0,51,102,0.1)}
.app-header h1{color:#003366;margin:0;font-size:clamp(1.1rem,4vw,1.7rem)}
.app-header p {color:#CDD4D9;margin:4px 0 0;font-size:.82rem}

.access-denied{background:#FDEDEB;border:2px solid #BF382A;border-radius:8px;
  padding:1.5rem;text-align:center;color:#BF382A;font-family:'IBM Plex Mono',monospace;margin:1rem 0}
.info-card{background:#E9EFF8;border:1px solid #D6DADC;border-radius:8px;padding:12px 16px}
.nav-section{font-size:.68rem;letter-spacing:.12em;text-transform:uppercase;
  color:#003366 !important;padding:10px 4px 2px;font-family:'IBM Plex Mono',monospace;font-weight:600}

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
  <h1>⛏️ Angara — Compliance System</h1>
  <p>
    <span class="role-badge {badge_cls}">{role_icon}</span>
    &nbsp;·&nbsp; {st.session_state.username}
    &nbsp;·&nbsp; Demo: <strong>10 Mar 2026</strong>
    &nbsp;·&nbsp; M1: Tracker &nbsp;·&nbsp; M2: Reports
  </p>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# ZIP EXPORT
# ══════════════════════════════════════════════════════════════════
def _build_zip() -> bytes:
    buf = io.BytesIO()
    count = 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if os.path.exists(ARCHIVE_DIR):
            for fname in sorted(os.listdir(ARCHIVE_DIR)):
                if fname.endswith(".pdf"):
                    zf.write(os.path.join(ARCHIVE_DIR, fname), arcname=fname)
                    count += 1
        zf.writestr("MANIFEST.txt",
            f"Angara Report Archive\nGenerated: {TODAY}\nTotal PDFs: {count}\n")
    buf.seek(0)
    return buf.getvalue()

# ══════════════════════════════════════════════════════════════════
# NAVIGATION DEFINITIONS
# ══════════════════════════════════════════════════════════════════
MANAGER_PAGES = [
    "📊  Dashboard",
    "📡  Monitor & Alerts",
    "✏️   Update Milestones",
    "➕  Add Milestone",
    "── Module 2 ──────────",
    "📑  Generate Report",
    "🗂️   Report Dashboard",
]
OFFICER_PAGES = [
    "✏️   Update Milestones",
    "➕  Add Milestone",
    "📑  Generate Report",
]
nav_options = MANAGER_PAGES if role == "Manager" else OFFICER_PAGES

# ══════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════
with st.sidebar:
    # User badge
    st.markdown(f"""
    <div style="margin-bottom:10px">
      <span class="role-badge {badge_cls}">{role_icon}</span>
      <div style="color:#8b949e;font-size:.78rem;margin-top:4px">{st.session_state.username}</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Project selector ─────────────────────────────────────────
    st.markdown("### 📁 Projects")
    st.markdown("---")
    projects_df = get_projects()

    if projects_df.empty:
        st.info("No projects yet.")
        st.session_state.selected_project_id   = None
        st.session_state.selected_project_name = None
    else:
        opts = dict(zip(projects_df["name"], projects_df["id"]))
        sel  = st.selectbox("Active Project", list(opts.keys()), key="sb_proj")
        st.session_state.selected_project_id   = opts[sel]
        st.session_state.selected_project_name = sel

    # ── Create / delete project ───────────────────────────────────
    if role == "Manager":
        st.markdown('<div class="section-title">New Project</div>', unsafe_allow_html=True)
        with st.form("new_proj", clear_on_submit=True):
            p_name  = st.text_input("Name *",   placeholder="e.g. Jharia Block-4")
            p_loc   = st.text_input("Location", placeholder="e.g. Dhanbad, JH")
            p_start = st.date_input("Start *",  value=TODAY)
            if st.form_submit_button("➕ Create", use_container_width=True):
                errs = ([] if p_name.strip() else ["Name required."]) + validate_project_start(p_start)
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
            if st.button("🗑️ Delete Active Project", use_container_width=True, type="secondary"):
                try:
                    delete_project(st.session_state.selected_project_id)
                    st.session_state.selected_project_id   = None
                    st.session_state.selected_project_name = None
                    st.warning("Deleted.")
                    st.rerun()
                except Exception as ex:
                    st.error(f"❌ {ex}")
    else:
        st.caption("⚠️ Project management requires Manager role.")

    st.markdown("---")

    # ── Page navigation ───────────────────────────────────────────
    st.markdown('<p class="nav-section">Navigate</p>', unsafe_allow_html=True)

    if "current_page" not in st.session_state:
        st.session_state.current_page = nav_options[0]
    # Guard: if role changed and saved page no longer valid, reset
    real_pages = [p for p in nav_options if not p.startswith("──")]
    if st.session_state.current_page not in real_pages:
        st.session_state.current_page = real_pages[0]

    selected_page = st.radio(
        "nav",
        nav_options,
        index=nav_options.index(st.session_state.current_page)
              if st.session_state.current_page in nav_options else 0,
        key="nav_radio",
        label_visibility="collapsed",
    )
    if not selected_page.startswith("──"):
        st.session_state.current_page = selected_page

    # ── ZIP Export ────────────────────────────────────────────────
    if role == "Manager":
        st.markdown("---")
        st.markdown('<div class="section-title">⬇️ Export Reports</div>', unsafe_allow_html=True)
        n_pdfs = len([f for f in os.listdir(ARCHIVE_DIR) if f.endswith(".pdf")]) \
                 if os.path.exists(ARCHIVE_DIR) else 0
        stats  = get_report_stats()
        st.markdown(f"""
        <div style="font-size:.72rem;color:#8b949e;margin-bottom:6px;
                    font-family:'IBM Plex Mono',monospace">
          📁 {n_pdfs} PDF(s) archived &nbsp;·&nbsp; {stats['submitted']} submitted
        </div>
        """, unsafe_allow_html=True)

        if n_pdfs > 0:
            st.download_button(
                label     = f"⬇️ Download ZIP ({n_pdfs} PDFs)",
                data      = _build_zip(),
                file_name = f"Angara_Reports_{TODAY.strftime('%Y%m%d')}.zip",
                mime      = "application/zip",
                use_container_width=True,
                key       = "zip_dl",
            )
        else:
            st.caption("Generate at least one report to enable export.")

    st.markdown("---")
    if st.button("🚪 Logout", use_container_width=True):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()

# ══════════════════════════════════════════════════════════════════
# REQUIRE ACTIVE PROJECT
# ══════════════════════════════════════════════════════════════════
pid   = st.session_state.selected_project_id
pname = st.session_state.selected_project_name

if not pid:
    st.markdown("""
    <div style="text-align:center;padding:4rem 2rem;color:#8b949e">
      <div style="font-size:3rem">⛏️</div>
      <h2 style="color:#f0a500;margin-top:1rem">Select or create a project</h2>
      <p>Use the sidebar to get started.</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# Fetch shared data once per render
projects_df   = get_projects()
start_rows    = projects_df.loc[projects_df["id"] == pid, "start_date"].values
project_start = date.fromisoformat(start_rows[0]) if len(start_rows) else TODAY
milestones_df = get_milestones(pid)

# ══════════════════════════════════════════════════════════════════
# PAGE ROUTING
# ══════════════════════════════════════════════════════════════════
page = st.session_state.current_page

# ── Shared pages (both roles) ────────────────────────────────────
if page == "✏️   Update Milestones":
    st.markdown(f"## ✏️ Update Milestones — {pname}")
    update_form.render(milestones_df, project_start)

elif page == "➕  Add Milestone":
    st.markdown(f"## ➕ Add Milestone — {pname}")
    add_milestone.render(pid)

elif page == "📑  Generate Report":
    st.markdown(f"## 📑 Generate Report — {pname}")
    # Auto-feed banner: live Mod 1 status shown before report form
    if not milestones_df.empty:
        delayed = int((milestones_df["status"] == "delayed").sum())
        overdue = sum(
            1 for _, r in milestones_df.iterrows()
            if r["status"] != "complete"
            and date.fromisoformat(str(r["target_date"])) < TODAY
        )
        ac = "#dc2626" if (delayed + overdue) else "#16a34a"
        am = (f"🚨 {delayed} delayed · {overdue} overdue — Delay Report recommended"
              if (delayed + overdue) else
              "✅ All milestones on track — MIS Quarterly recommended")
        st.markdown(f"""
        <div style="background:#161b22;border:1px solid {ac};border-radius:8px;
                    padding:8px 14px;margin-bottom:1rem;font-size:.8rem">
          <span style="color:{ac};font-family:'IBM Plex Mono',monospace;font-weight:600">
            AUTO-FEED FROM MODULE 1
          </span>
          <span style="color:#8b949e;margin-left:10px">{am}</span>
        </div>
        """, unsafe_allow_html=True)
    report_form.render(active_project_id=pid)

# ── Manager-only pages ───────────────────────────────────────────
elif page == "📊  Dashboard":
    st.markdown(f"## 📊 Compliance Dashboard — {pname}")
    dashboard.render(pid, pname, milestones_df)

elif page == "📡  Monitor & Alerts":
    st.markdown(f"## 📡 Monitor & Alerts — {pname}")
    monitoring.render(milestones_df)

elif page == "🗂️   Report Dashboard":
    st.markdown("## 🗂️ Report Dashboard")
    reports_dashboard.render(active_project_id=pid)

# ── Officer fallback ─────────────────────────────────────────────
else:
    officer_view.render(pid, project_start, milestones_df)
