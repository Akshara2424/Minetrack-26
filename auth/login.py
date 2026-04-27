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
    
    # Footer
    st.markdown("""
    <style>
    .footer-container {
        background-color: #1B3A6B;
        color: #ffffff;
        padding: 30px 20px;
        font-size: 13px;
        border-top: 4px solid #E8A020;
        margin-top: 40px;
    }
    </style>
    <div class="footer-container">
      <div style="max-width: 1400px; margin: 0 auto; padding: 0 20px;">
        
        <!-- Top Row -->
        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 30px; margin-bottom: 20px;">
          
          <!-- Left: Ministry Logos + Description -->
          <div style="display: flex; align-items: flex-start; gap: 15px; max-width: 350px;">
            <div style="width: 50px; min-width: 50px;">
              <div style="color: #E8A020; font-weight: bold; text-align: center;">IIT-BHU</div>
            </div>
            <div>
              <strong style="color: #E8A020;">ANGARA</strong><br>
              <small style="line-height: 1.4; color: #CBD5E0;">
                An integrated compliance tracking system for<br>
                Ministry of Coal to monitor and report on<br>
                regulatory milestones and project progress.
              </small>
            </div>
          </div>

          <!-- Center: Important Links -->
          <div>
            <strong style="color: #E8A020;">Important Links</strong><br>
            <small style="color: #CBD5E0; line-height: 1.8;">
              Dashboard &nbsp; | &nbsp; Monitor & Alerts &nbsp; | &nbsp;<br>
              Generate Reports &nbsp; | &nbsp; Update Milestones
            </small>
          </div>

          <!-- Center: Useful Links -->
          <div>
            <strong style="color: #E8A020;">Useful Links</strong><br>
            <small style="color: #CBD5E0; line-height: 1.8;">
              Documentation &nbsp; | &nbsp; Resources &nbsp; | &nbsp;<br>
              Support &nbsp; | &nbsp; Feedback
            </small>
          </div>

          <!-- Right: Partner + Powered By -->
          <div style="text-align: right;">
            <strong style="color: #E8A020;">Ministry Partners</strong><br>
            <small style="color: #CBD5E0; line-height: 1.8;">
              Ministry of Coal<br>
              IIT (BHU) Varanasi
            </small>
            <div style="margin-top: 15px; font-weight: bold; color: #E8A020;">
              JINDAL STEEL
            </div>
          </div>
        </div>

        <!-- Bottom Bar -->
        <div style="border-top: 1px solid #334155; padding-top: 15px; text-align: center; font-size: 12px; color: #CBD5E0;">
          © 2026 - ANGARA @ All rights reserved | Ministry of Coal<br>
          <small>Regulatory Milestone Tracker & Compliance Reporting System | IIT-BHU Hackathon Submission</small>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)