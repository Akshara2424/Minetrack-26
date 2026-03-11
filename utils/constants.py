"""
utils/constants.py — Shared constants for MineGuard Module 1
"""

import os
from datetime import date

# ── Demo date (fixed per spec) ───────────────────────────────────
TODAY = date(2026, 3, 10)

# ── Database path ────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "mineguard.db")

# ── Roles ────────────────────────────────────────────────────────
ROLES = ["Manager", "Officer"]

# ── Milestone statuses ───────────────────────────────────────────
STATUS_OPTIONS = ["pending", "in_progress", "complete", "delayed"]

STATUS_EMOJI = {
    "pending":     "🟡",
    "in_progress": "🔵",
    "complete":    "🟢",
    "delayed":     "🔴",
}

# ── Default regulatory milestones (name, days from project start) ─
DEFAULT_MILESTONES = [
    ("EIA Submission",            30),
    ("Land NOC",                  60),
    ("Forest Clearance Stage 1",  90),
    ("Pollution Control NOC",    120),
    ("Mining Lease Grant",       180),
]

# ── Bottleneck rules (milestone name → cause description) ────────
BOTTLENECK_RULES = {
    "Forest Clearance Stage 1": "Forest clearance backlog (Odisha avg. 90 days). Escalate to MoEFCC.",
    "Land NOC":                 "State revenue dept. backlog. Check with District Collector office.",
    "EIA Submission":           "EIA consultant delay or data gaps. Review scope with consultant.",
    "Pollution Control NOC":    "SPCB inspection queue. Request expedited review.",
    "Mining Lease Grant":       "MoC processing delay. Verify application completeness.",
}

DEFAULT_BOTTLENECK = "State dept. backlog. Consider escalation to senior officer."