"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  Angara — Integrated Compliance System                                       ║
║  Ministry of Coal MIS Report Aesthetic                                       ║
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

st.set_page_config(
    page_title="Angara — Compliance",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Hide top-right buttons and elements
hide_streamlit_style = """
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        .stDeployButton {visibility: hidden;}
        [data-testid="stToolbar"] {visibility: hidden;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# MINISTRY OF COAL — GLOBAL CSS
# ══════════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* ─────────────────────────────────────────────────────────────────
   COLOUR TOKENS
   Primary navy    : #1B3A6B  — headers, active nav, buttons
   Accent saffron  : #E8A020  — highlights, badges, accent borders
   Light blue-grey : #EEF2F7  — card backgrounds, table alternates
   Table header bg : #2C5282
   Success green   : #2E7D32
   Warning orange  : #F57C00
   Error red       : #C62828
─────────────────────────────────────────────────────────────────*/
:root {
    --navy:          #1B3A6B;
    --navy-dark:     #132D55;
    --navy-header:   #2C5282;
    --saffron:       #E8A020;
    --saffron-bg:    #FEF6E4;
    --saffron-bdr:   #D4900F;
    --bg-page:       #FFFFFF;
    --bg-card:       #FFFFFF;
    --bg-alt:        #EEF2F7;
    --border:        #CBD5E0;
    --border-light:  #E2E8F0;
    --text:          #1A1A2E;
    --text-muted:    #4A5568;
    --text-light:    #718096;
    --success:       #2E7D32;
    --success-bg:    #E8F5E9;
    --warning:       #F57C00;
    --warning-bg:    #FFF3E0;
    --error:         #C62828;
    --error-bg:      #FFEBEE;
    --info:          #1B3A6B;
    --info-bg:       #EEF2F7;
}

/* BASE */
html,body,[class*="css"],.stApp{background-color:var(--bg-page)!important;color:var(--text)!important;font-family:"Segoe UI",Arial,sans-serif!important}
.stAppViewContainer {padding: 0 !important; margin: 0 !important;}
.stMainBlockContainer {padding: 0 !important; margin: 0 !important; max-width: 100% !important;}
[data-testid="stAppViewContainer"] {padding: 0 !important;}
h1,h2,h3{color:var(--navy)!important;font-weight:700!important}

/* SIDEBAR */
[data-testid="stSidebar"]{background-color:var(--navy)!important;border-right:3px solid var(--saffron)!important}
[data-testid="stSidebar"] *{color:#FFFFFF!important}
[data-testid="stSidebar"] p,[data-testid="stSidebar"] span,[data-testid="stSidebar"] label{color:#E2E8F0!important}
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3{color:var(--saffron)!important;font-weight:700!important}
[data-testid="stSidebar"] hr{border-color:rgba(232,160,32,0.4)!important}
[data-testid="stSidebar"] [data-testid="stSelectbox"]>div>div{background-color:rgba(255,255,255,0.1)!important;border-color:rgba(255,255,255,0.25)!important;color:#FFFFFF!important}

/* METRIC CARDS — white bg, 3px left border in navy */
[data-testid="metric-container"]{background-color:var(--bg-card)!important;border:1px solid var(--border-light)!important;border-left:3px solid var(--navy)!important;border-radius:6px!important;padding:14px 16px!important;box-shadow:0 1px 3px rgba(27,58,107,0.08)!important}
[data-testid="metric-container"] [data-testid="stMetricLabel"]{color:var(--text-muted)!important;font-size:0.78rem!important;font-weight:600!important;text-transform:uppercase!important;letter-spacing:0.05em!important}
[data-testid="metric-container"] [data-testid="stMetricValue"]{color:var(--navy)!important;font-size:1.7rem!important;font-weight:700!important}
[data-testid="metric-container"] [data-testid="stMetricDelta"]{color:var(--success)!important}

/* BUTTONS — primary navy */
.stButton>button{background-color:var(--navy)!important;color:#FFFFFF!important;border:1px solid var(--navy)!important;border-radius:5px!important;font-weight:600!important;transition:background 0.15s,box-shadow 0.15s!important}
.stButton>button:hover{background-color:var(--navy-dark)!important;border-color:var(--navy-dark)!important;box-shadow:0 2px 6px rgba(27,58,107,0.25)!important}
.stButton>button[kind="secondary"]{background-color:var(--bg-alt)!important;color:var(--navy)!important;border:1px solid var(--border)!important}
.stButton>button[kind="secondary"]:hover{background-color:#dce5f0!important;border-color:var(--navy)!important}
.stDownloadButton>button{background-color:var(--navy)!important;color:#FFFFFF!important;border:1px solid var(--navy)!important;border-radius:5px!important;font-weight:600!important}
.stDownloadButton>button:hover{background-color:var(--navy-dark)!important}

/* TABS */
[data-testid="stTabs"] [data-baseweb="tab-list"]{background-color:var(--bg-alt)!important;border-bottom:2px solid var(--border)!important;border-radius:6px 6px 0 0!important}
[data-testid="stTabs"] [data-baseweb="tab"]{color:var(--text-muted)!important;font-weight:600!important;padding:10px 18px!important;border-bottom:3px solid transparent!important;background:transparent!important}
[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"]{color:var(--navy)!important;border-bottom:3px solid var(--navy)!important;background-color:var(--bg-page)!important}
[data-testid="stTabs"] [data-baseweb="tab"]:hover{color:var(--navy)!important;background-color:#dce5f0!important}

/* DATA TABLES — #2C5282 header with white text */
[data-testid="stDataFrame"] thead tr th,.stDataFrame thead tr th{background-color:#2C5282!important;color:#FFFFFF!important;font-weight:700!important;font-size:0.78rem!important;text-transform:uppercase!important;letter-spacing:0.04em!important;padding:10px 12px!important;border-bottom:2px solid var(--saffron)!important}
[data-testid="stDataFrame"] tbody tr:nth-child(even) td,.stDataFrame tbody tr:nth-child(even) td{background-color:var(--bg-alt)!important}
[data-testid="stDataFrame"] tbody tr:hover td{background-color:#dce5f0!important}
[data-testid="stDataFrame"] tbody tr td{color:var(--text)!important;font-size:0.84rem!important;padding:8px 12px!important;border-bottom:1px solid var(--border-light)!important}

/* FORM INPUTS */
.stTextInput>div>div>input,.stTextArea>div>div>textarea,.stSelectbox>div>div,.stMultiSelect>div>div,.stDateInput>div>div>input{border:1px solid var(--border)!important;border-radius:5px!important;color:var(--text)!important;background-color:var(--bg-page)!important}
.stTextInput>div>div>input:focus,.stTextArea>div>div>textarea:focus{border-color:var(--navy)!important;box-shadow:0 0 0 2px rgba(27,58,107,0.15)!important}
.stTextInput label,.stTextArea label,.stSelectbox label,.stDateInput label,.stMultiSelect label,.stRadio label,.stCheckbox label{color:var(--text-muted)!important;font-weight:600!important;font-size:0.82rem!important}

/* UTILITY CLASSES */
.section-title{color:var(--navy);font-size:0.78rem;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;border-bottom:2px solid var(--border-light);padding-bottom:5px;margin:1.4rem 0 0.8rem}
.section-title::before{content:"";display:inline-block;width:4px;height:1em;background:var(--saffron);margin-right:8px;vertical-align:middle;border-radius:2px}

.app-header{background:linear-gradient(135deg,var(--navy) 0%,var(--navy-header) 100%);border-bottom:4px solid var(--saffron);padding:1.5rem 2rem;margin-bottom:1.25rem;border-radius:0;box-shadow:0 2px 8px rgba(27,58,107,0.2);display:flex;align-items:center;justify-content:space-between;gap:2rem}
.app-header-content{flex:1}
.app-header h1{color:#FFFFFF!important;margin:0;font-size:clamp(1.1rem,3vw,1.6rem);letter-spacing:0.02em}
.app-header p{color:rgba(255,255,255,0.75);margin:4px 0 0;font-size:0.8rem}
.app-header-logos{display:flex;align-items:center;gap:1.5rem}
.app-header-logo{height:50px;width:auto;object-fit:contain}

.role-badge{display:inline-block;padding:3px 12px;border-radius:20px;font-size:0.75rem;font-weight:700;letter-spacing:0.04em}
.role-manager{background:var(--saffron-bg);color:var(--navy);border:1px solid var(--saffron)}
.role-officer{background:var(--error-bg);color:var(--error);border:1px solid var(--error)}

.badge{display:inline-block;padding:2px 10px;border-radius:20px;font-size:0.72rem;font-weight:700;letter-spacing:0.03em}
.badge-pending{background:var(--warning-bg);color:var(--warning);border:1px solid var(--warning)}
.badge-in_progress{background:var(--info-bg);color:var(--navy);border:1px solid var(--navy)}
.badge-complete{background:var(--success-bg);color:var(--success);border:1px solid var(--success)}
.badge-delayed{background:var(--error-bg);color:var(--error);border:1px solid var(--error)}

.timeline-bar{height:8px;border-radius:4px;background:var(--bg-alt);margin:4px 0;overflow:hidden}
.timeline-fill{height:100%;border-radius:4px;background:var(--navy)}
.overdue-chip{background:var(--error-bg);color:var(--error);border:1px solid var(--error);border-radius:4px;padding:2px 8px;font-size:0.7rem}

.module-banner{background:var(--bg-alt);border:1px solid var(--border);border-left:4px solid var(--navy);border-radius:6px;padding:10px 16px;margin-bottom:1rem}
.module-banner .banner-tag{color:var(--navy);font-size:0.78rem;font-weight:700;letter-spacing:0.12em;text-transform:uppercase}
.module-banner .banner-sub{color:var(--text-muted);font-size:0.73rem}

.report-card{background:var(--bg-card);border:1px solid var(--border-light);border-radius:6px;padding:10px 14px;margin-bottom:6px;box-shadow:0 1px 2px rgba(27,58,107,0.06)}
.report-card-title{font-weight:700;color:var(--text);font-size:0.87rem}
.report-card-meta{font-size:0.72rem;color:var(--text-muted);margin-top:2px}

.autofeed-banner{background:var(--bg-alt);border:1px solid var(--border);border-radius:6px;padding:8px 14px;margin-bottom:1rem;font-size:0.8rem}
.autofeed-banner .af-tag{font-weight:700;font-size:0.75rem;letter-spacing:0.1em;text-transform:uppercase}
.autofeed-banner .af-msg{color:var(--text-muted);margin-left:10px}

.info-card{background:var(--bg-alt);border:1px solid var(--border-light);border-radius:6px;padding:12px 16px}
.access-denied{background:var(--error-bg);border:2px solid var(--error);border-radius:8px;padding:1.5rem;text-align:center;color:var(--error);margin:1rem 0}
.nav-section{font-size:0.68rem;letter-spacing:0.12em;text-transform:uppercase;color:var(--navy)!important;padding:10px 4px 2px;font-weight:700}

/* NAV BAR */
.nav-bar{background:linear-gradient(135deg,var(--navy) 0%,var(--navy-header) 100%);padding:16px 0;margin:0;margin-bottom:0;border-bottom:3px solid var(--saffron);box-shadow:0 2px 8px rgba(27,58,107,0.2);width:100vw;margin-left:calc(-50vw + 50%)}
.nav-bar-container{padding:0 24px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.nav-bar .stButton>button{font-size:0.85rem!important;padding:8px 16px!important;height:auto!important;border-radius:5px!important}
.nav-bar .stButton>button[kind="primary"]{background-color:var(--saffron)!important;color:var(--navy)!important;border-color:var(--saffron-bdr)!important;font-weight:700!important}
.nav-bar .stButton>button[kind="primary"]:hover{background-color:var(--saffron-bdr)!important}
.nav-bar .stButton>button[kind="secondary"]{background-color:rgba(255,255,255,0.12)!important;color:#FFFFFF!important;border-color:rgba(255,255,255,0.3)!important}
.nav-bar .stButton>button[kind="secondary"]:hover{background-color:rgba(255,255,255,0.22)!important}
.nav-spacer{flex:1;}
.nav-user-info{color:#FFFFFF;font-size:0.75rem;font-weight:600;padding:0 12px;display:flex;align-items:center;gap:8px;white-space:nowrap;border-left:1px solid rgba(255,255,255,0.2);padding-left:12px}

hr{border-color:var(--border-light)!important;margin:1rem 0!important}

@media(max-width:640px){[data-testid="column"]{min-width:100%!important;flex:1 1 100%!important}.stDataFrame{font-size:12px}}
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
# ROLE & PAGE SETUP
# ══════════════════════════════════════════════════════════════════
role      = st.session_state.role
badge_cls = "role-manager" if role == "Manager" else "role-officer"
role_icon = "Manager" if role == "Manager" else "Officer"

# ══════════════════════════════════════════════════════════════════
# NAVIGATION DEFINITIONS
# ══════════════════════════════════════════════════════════════════
MANAGER_PAGES = [
    "Dashboard",
    "Monitor & Alerts",
    "Update Milestones",
    "Add Milestone",
    "Generate Report",
    "Report Dashboard",
]
OFFICER_PAGES = [
    "Update Milestones",
    "Add Milestone",
    "Generate Report",
]
nav_options = MANAGER_PAGES if role == "Manager" else OFFICER_PAGES

if "current_page" not in st.session_state:
    st.session_state.current_page = nav_options[0]

real_pages = [p for p in nav_options if not p.startswith("──")]
if st.session_state.current_page not in real_pages:
    st.session_state.current_page = real_pages[0]

# ══════════════════════════════════════════════════════════════════
# TOP NAVIGATION BAR
# ══════════════════════════════════════════════════════════════════
st.markdown('<div class="nav-bar"><div class="nav-bar-container">', unsafe_allow_html=True)

# Navigation buttons
nav_cols = st.columns([0.1] * len(nav_options) + [1, 0.12, 0.1], gap="small")
for idx, page_option in enumerate(nav_options):
    with nav_cols[idx]:
        is_active = st.session_state.current_page == page_option
        btn_type  = "primary" if is_active else "secondary"
        if st.button(page_option, key=f"nav_{idx}", use_container_width=True, type=btn_type):
            st.session_state.current_page = page_option
            st.rerun()

# Spacer
with nav_cols[-3]:
    st.markdown("")

# User info
with nav_cols[-2]:
    st.markdown(
        f'<div class="nav-user-info">{role_icon} {st.session_state.username}</div>',
        unsafe_allow_html=True,
    )

# Exit button
with nav_cols[-1]:
    if st.button("Exit", key="logout_btn", use_container_width=True, type="secondary"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

st.markdown("</div></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# ZIP EXPORT HELPER
# ══════════════════════════════════════════════════════════════════
def _build_zip() -> bytes:
    buf   = io.BytesIO()
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
# PROJECT SELECTOR & MANAGEMENT
# ══════════════════════════════════════════════════════════════════
projects_df = get_projects()

if projects_df.empty:
    st.session_state.selected_project_id   = None
    st.session_state.selected_project_name = None
    st.info("No projects yet. Create one to get started.")
    st.stop()
else:
    proj_col1, proj_col2, proj_col3 = st.columns([3, 1, 1])
    with proj_col1:
        opts = dict(zip(projects_df["name"], projects_df["id"]))
        sel  = st.selectbox("Active Project", list(opts.keys()), key="top_proj")
        st.session_state.selected_project_id   = opts[sel]
        st.session_state.selected_project_name = sel
    with proj_col2:
        if role == "Manager" and st.button("+ New", key="new_proj_btn", use_container_width=True):
            st.session_state.show_new_project = True
    with proj_col3:
        if role == "Manager" and st.session_state.get("selected_project_id"):
            if st.button("Delete", key="del_proj_btn", use_container_width=True):
                try:
                    delete_project(st.session_state.selected_project_id)
                    st.session_state.selected_project_id   = None
                    st.session_state.selected_project_name = None
                    st.success("Project deleted.")
                    st.rerun()
                except Exception as ex:
                    st.error(f"Error: {ex}")

if st.session_state.get("show_new_project"):
    st.markdown("---")
    st.markdown('<div class="section-title">New Project</div>', unsafe_allow_html=True)
    with st.form("new_proj", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            p_name  = st.text_input("Name *",   placeholder="e.g. Jharia Block-4")
            p_start = st.date_input("Start *",  value=TODAY)
        with c2:
            p_loc   = st.text_input("Location", placeholder="e.g. Dhanbad, JH")
        if st.form_submit_button("Create Project", use_container_width=True):
            errs = ([] if p_name.strip() else ["Name required."]) + validate_project_start(p_start)
            if errs:
                for e in errs: st.error(e)
            else:
                try:
                    create_project(p_name.strip(), p_start, p_loc.strip(), role)
                    st.success(f"\'{p_name}\' created.")
                    st.session_state.show_new_project = False
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("A project with that name already exists.")
                except Exception as ex:
                    st.error(f"Error: {ex}")

# ══════════════════════════════════════════════════════════════════
# REQUIRE ACTIVE PROJECT
# ══════════════════════════════════════════════════════════════════
pid   = st.session_state.selected_project_id
pname = st.session_state.selected_project_name

if not pid:
    st.markdown("""
    <div style="text-align:center;padding:4rem 2rem;">
      <h2 style="color:#1B3A6B;">Select or create a project</h2>
      <p style="color:#4A5568;font-size:0.95rem;">Use the selector above to get started.</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

projects_df   = get_projects()
start_rows    = projects_df.loc[projects_df["id"] == pid, "start_date"].values
project_start = date.fromisoformat(start_rows[0]) if len(start_rows) else TODAY
milestones_df = get_milestones(pid)

# ══════════════════════════════════════════════════════════════════
# PAGE ROUTING
# ══════════════════════════════════════════════════════════════════
page = st.session_state.current_page

if page == "Update Milestones":
    st.markdown(f"## Update Milestones — {pname}")
    update_form.render(milestones_df, project_start)

elif page == "Add Milestone":
    st.markdown(f"## Add Milestone — {pname}")
    add_milestone.render(pid)

elif page == "Generate Report":
    st.markdown(f"## Generate Report — {pname}")
    if not milestones_df.empty:
        delayed = int((milestones_df["status"] == "delayed").sum())
        overdue = sum(
            1 for _, r in milestones_df.iterrows()
            if r["status"] != "complete"
            and date.fromisoformat(str(r["target_date"])) < TODAY
        )
        has_issue  = bool(delayed + overdue)
        border_col = "#C62828" if has_issue else "#2E7D32"
        bg_col     = "#FFEBEE" if has_issue else "#E8F5E9"
        msg = (f"{delayed} delayed · {overdue} overdue — Delay Report recommended"
               if has_issue else "All milestones on track — MIS Quarterly recommended")
        st.markdown(f"""
        <div class="autofeed-banner" style="border-left:4px solid {border_col};background:{bg_col};">
          <span class="af-tag" style="color:{border_col}">AUTO-FEED FROM MODULE 1</span>
          <span class="af-msg">{msg}</span>
        </div>
        """, unsafe_allow_html=True)
    report_form.render(active_project_id=pid)

elif page == "Dashboard":
    st.markdown(f"# Compliance Dashboard — {pname}")
    dashboard.render(pid, pname, milestones_df)

elif page == "Monitor & Alerts":
    st.markdown(f"## Monitor & Alerts — {pname}")
    monitoring.render(milestones_df)

elif page == "Report Dashboard":
    st.markdown("## Report Dashboard")
    reports_dashboard.render(active_project_id=pid)

else:
    officer_view.render(pid, project_start, milestones_df)
