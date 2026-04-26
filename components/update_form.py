"""components/update_form.py — Tab 3: Update milestone status/notes. Manager + Officer."""
import streamlit as st
import pandas as pd
from datetime import date
from db import update_milestone
from utils.alerts import compute_urgency
from utils.validators import validate_actual_date
from utils.constants import STATUS_OPTIONS

def render(milestones_df, project_start):
    st.markdown('<div class="section-title">Update Status & Notes</div>', unsafe_allow_html=True)
    role = st.session_state.role
    if milestones_df.empty: st.info("No milestones to update."); return
    for _, row in milestones_df.iterrows():
        td = date.fromisoformat(row["target_date"])
        info = compute_urgency(td, row["status"])
        with st.expander(f"{info['emoji']}  {row['name']}  — {info['label']}"):
            with st.form(f"upd_{row['id']}", clear_on_submit=False):
                ca, cb = st.columns(2)
                with ca:
                    new_status = st.selectbox("Status", STATUS_OPTIONS, index=STATUS_OPTIONS.index(row["status"]), key=f"s_{row['id']}")
                with cb:
                    actual_val = date.fromisoformat(row["actual_date"]) if row["actual_date"] else None
                    new_actual = st.date_input("Actual Completion Date (optional)", value=actual_val, key=f"a_{row['id']}")
                new_notes = st.text_area("Notes", value=row["notes"] or "", placeholder="Observations, blockers, references…", key=f"n_{row['id']}", height=75)
                if st.form_submit_button("Save Changes", use_container_width=True):
                    errors = validate_actual_date(new_actual, project_start) if new_actual else []
                    if errors:
                        for e in errors: st.error(f"❌ {e}")
                    else:
                        try:
                            update_milestone(row["id"], new_status, new_notes, new_actual.isoformat() if new_actual else None, role)
                            st.success(f" '{row['name']}' updated by {role}: {st.session_state.username}")
                            st.rerun()
                        except Exception as ex: st.error(f"Database error: {ex}")