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
    # Display header image
    try:
        st.image("assests/header.png", use_container_width=True)
    except:
        st.warning("Header image not found")
    
    # Center form in 60% width
    left_space, form_col, right_space = st.columns([1, 3, 1])
    
    with form_col:
        # Form fields
        col1, col2 = st.columns(2)
        with col1:
            username = st.text_input("Name / ID", placeholder="e.g. Rajesh Kumar", key="login_name")
        with col2:
            role_col1, role_col2 = st.columns([4, 1])
            with role_col1:
                role = st.selectbox("Role", ["— select —"] + ROLES, key="login_role")
            with role_col2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("?", key="show_permissions", help="View role permissions", use_container_width=True):
                    st.session_state.show_role_perms = not st.session_state.get("show_role_perms", False)
        
        # Show permissions if toggled
        if st.session_state.get("show_role_perms"):
            st.markdown('''<div class="info-card" style="margin-top:12px;">
              <div class="section-title">Role Permissions</div>
              <table style="width:100%;border-collapse:collapse;font-size:0.82rem;color:#000000;">
                <tr style="border-bottom:1px solid #D6DADC;">
                  <th style="text-align:left;padding:6px;color:#CDD4D9;">Feature</th>
                  <th style="text-align:center;padding:6px;">Manager [M]</th>
                  <th style="text-align:center;padding:6px;">Officer [O]</th>
                </tr>
                <tr><td style="padding:6px;">Full Dashboard</td><td style="text-align:center;">[X]</td><td style="text-align:center;">[Y]</td></tr>
                <tr><td style="padding:6px;">Monitor &amp; Alerts</td><td style="text-align:center;">[X]</td><td style="text-align:center;">[Y]</td></tr>
                <tr><td style="padding:6px;">Update Milestones</td><td style="text-align:center;">[X]</td><td style="text-align:center;">[X]</td></tr>
                <tr><td style="padding:6px;">Add Milestones</td><td style="text-align:center;">[X]</td><td style="text-align:center;">[X]</td></tr>
                <tr><td style="padding:6px;">Create / Delete Projects</td><td style="text-align:center;">[X]</td><td style="text-align:center;">[Y]</td></tr>
              </table></div>''', unsafe_allow_html=True)
        
        # Enter App button below
        if st.button("Enter App", type="primary", use_container_width=True):
            if role == "— select —":
                st.error("Please select a role.")
            elif not username.strip():
                st.error("Please enter your name or ID.")
            else:
                st.session_state.logged_in = True
                st.session_state.role = role
                st.session_state.username = username.strip()
                st.rerun()