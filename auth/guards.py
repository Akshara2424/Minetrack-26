"""auth/guards.py — Role gate helpers."""
import streamlit as st

def access_denied(feature: str):
    st.markdown(f'''<div class="access-denied">
      🔒 <strong>Access Restricted</strong><br>
      <span style="font-size:0.85rem;">{feature} requires <strong>Manager</strong> role.</span>
    </div>''', unsafe_allow_html=True)

def require_role(required: str) -> bool:
    if st.session_state.get("role") != required:
        access_denied("This section")
        return False
    return True

def init_session():
    defaults = {
        "role": None, "username": "", "logged_in": False,
        "selected_project_id": None, "selected_project_name": None,
        "last_alert_run": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v