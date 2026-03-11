"""
components/add_milestone.py — Tab 3: Add a custom regulatory milestone
"""

import streamlit as st
import pandas as pd
from datetime import date, timedelta
from db import add_custom_milestone

DEFAULT_MILESTONES = [
    ("EIA Submission",            30),
    ("Land NOC",                  60),
    ("Forest Clearance Stage 1",  90),
    ("Pollution Control NOC",    120),
    ("Mining Lease Grant",       180),
]


def render(project_id: int):
    st.markdown('<div class="section-title">Add Custom Regulatory Milestone</div>',
                unsafe_allow_html=True)

    with st.form("add_milestone_form", clear_on_submit=True):
        m_name = st.text_input(
            "Milestone Name *",
            placeholder="e.g. Water Usage Permit, Explosive Storage NOC…",
        )
        m_target = st.date_input(
            "Target Date *",
            value=date.today() + timedelta(days=30),
        )
        m_notes = st.text_area(
            "Notes",
            placeholder="Regulatory body, reference number, remarks…",
            height=80,
        )

        if st.form_submit_button("➕ Add Milestone", use_container_width=True):
            if not m_name.strip():
                st.error("Milestone name is required.")
            else:
                add_custom_milestone(project_id, m_name.strip(), m_target, m_notes.strip())
                st.success(f"✅ '{m_name}' added!")
                st.rerun()

    # ── Reference table ──
    st.markdown("---")
    st.markdown('<div class="section-title">Default Milestones (seeded on project creation)</div>',
                unsafe_allow_html=True)

    ref_df = pd.DataFrame(DEFAULT_MILESTONES, columns=["Milestone Name", "Days from Start"])
    st.dataframe(ref_df, use_container_width=True, hide_index=True)