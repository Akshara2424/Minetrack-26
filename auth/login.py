"""auth/login.py — Login screen."""
import streamlit as st
from utils.constants import ROLES

def init_session():
    """Initialize session state variables."""
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "username" not in st.session_state:
        st.session_state.username = None
    if "role" not in st.session_state:
        st.session_state.role = None
    if "selected_project_id" not in st.session_state:
        st.session_state.selected_project_id = None
    if "selected_project_name" not in st.session_state:
        st.session_state.selected_project_name = None

# ...rest of your auth.py code...

def render_login():
    st.markdown('''<div class="app-header">
      <h1>⛏️ MineGuard — Compliance Module 1</h1>
      <p>Regulatory Milestone Tracker · Demo: March 10, 2026</p>
    </div>''', unsafe_allow_html=True)
    st.markdown("### 🔐 Select Role to Continue")
    st.markdown("_In production this would be JWT auth. For demo, choose your role below._")
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        username = st.text_input("Name / ID", placeholder="e.g. Rajesh Kumar", key="login_name")
    with col2:
        role = st.selectbox("Role", ["— select —"] + ROLES, key="login_role")
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("▶ Enter App", type="primary", use_container_width=True):
            if role == "— select —":
                st.error("Please select a role.")
            elif not username.strip():
                st.error("Please enter your name or ID.")
            else:
                st.session_state.logged_in = True
                st.session_state.role = role
                st.session_state.username = username.strip()
                st.rerun()
    st.markdown("---")
    st.markdown('''<div class="info-card">
      <div class="section-title">Role Permissions</div>
      <table style="width:100%;border-collapse:collapse;font-size:0.82rem;color:#e6edf3;">
        <tr style="border-bottom:1px solid #30363d;">
          <th style="text-align:left;padding:6px;color:#8b949e;">Feature</th>
          <th style="text-align:center;padding:6px;">Manager 👔</th>
          <th style="text-align:center;padding:6px;">Officer 📋</th>
        </tr>
        <tr><td style="padding:6px;">Full Dashboard</td><td style="text-align:center;">✅</td><td style="text-align:center;">❌</td></tr>
        <tr><td style="padding:6px;">Monitor &amp; Alerts</td><td style="text-align:center;">✅</td><td style="text-align:center;">❌</td></tr>
        <tr><td style="padding:6px;">Update Milestones</td><td style="text-align:center;">✅</td><td style="text-align:center;">✅</td></tr>
        <tr><td style="padding:6px;">Add Milestones</td><td style="text-align:center;">✅</td><td style="text-align:center;">✅</td></tr>
        <tr><td style="padding:6px;">Create / Delete Projects</td><td style="text-align:center;">✅</td><td style="text-align:center;">❌</td></tr>
      </table></div>''', unsafe_allow_html=True)