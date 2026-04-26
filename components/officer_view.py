"""components/officer_view.py — Officer simplified entry-only view."""
import streamlit as st
import pandas as pd
from datetime import date
from components import update_form, add_milestone

def render(project_id, project_start, milestones_df):
    st.markdown(f'''<div style="background:#E9EFF8;border:1px solid #003366;border-radius:8px;padding:10px 16px;margin-bottom:1rem;">
      <span class="role-badge role-officer">👷 Officer View</span>
      <span style="color:#CDD4D9;font-size:0.8rem;margin-left:10px;">Entry & update access only · {st.session_state.username}</span>
    </div>''', unsafe_allow_html=True)
    tab_a, tab_b = st.tabs(["Update Milestones", "Add Milestone"])
    with tab_a: update_form.render(milestones_df, project_start)
    with tab_b: add_milestone.render(project_id, project_start)
    st.markdown("---")
    st.markdown('<div class="section-title">My Submissions</div>', unsafe_allow_html=True)
    my_rows = milestones_df[milestones_df["submitted_by"] == "Officer"]
    if my_rows.empty:
        st.info("No milestones submitted by Officer role yet.")
    else:
        disp = my_rows[["name","target_date","status","notes","updated_at"]].copy()
        disp.columns = ["Milestone","Target Date","Status","Notes","Last Updated"]
        st.dataframe(disp, use_container_width=True, hide_index=True)