"""
utils/alerts.py — Urgency computation, mock alert dispatch, bottleneck detection
Pure logic — no Streamlit, no DB imports. Easy to swap in Twilio later.
"""

from datetime import date
from utils.constants import TODAY, BOTTLENECK_RULES, DEFAULT_BOTTLENECK


# ── Urgency ──────────────────────────────────────────────────────

def compute_urgency(target_date: date, status: str) -> dict:
    """
    Return urgency metadata for a milestone.

    Returns dict with keys:
        days    : int  (negative = overdue)
        level   : str  (complete | green | yellow | red)
        color   : str  (hex)
        label   : str  (human-readable)
        emoji   : str
    """
    if status == "complete":
        return {
            "days": 0, "level": "complete",
            "color": "#16a34a", "label": "COMPLETE", "emoji": "✅",
        }

    days = (target_date - TODAY).days

    if days > 7:
        return {
            "days": days, "level": "green", "color": "#16a34a",
            "label": f"{days}d remaining", "emoji": "🟢",
        }
    elif 3 <= days <= 7:
        return {
            "days": days, "level": "yellow", "color": "#d97706",
            "label": f"{days}d — Alert!", "emoji": "🟡",
        }
    else:
        label = f"OVERDUE {abs(days)}d" if days < 0 else f"{days}d — CRITICAL"
        return {
            "days": days, "level": "red", "color": "#dc2626",
            "label": label, "emoji": "🔴",
        }


# ── Mock alert dispatch ──────────────────────────────────────────

def fire_mock_alerts(milestone_id: int, name: str, days: int) -> list[dict]:
    """
    Print mock alerts to console and return structured list for UI.

    In production: replace print() calls with Twilio SMS/WhatsApp API.

    Returns:
        List of dicts: [{channel, message}, ...]
    """
    if days < 0:
        body = f"🚨 OVERDUE {abs(days)}d: '{name}' — Immediate action required."
    elif days <= 3:
        body = f"⚠️  CRITICAL: '{name}' due in {days} day(s). Attach docs & escalate NOW."
    else:
        body = f"📅 REMINDER: '{name}' due in {days} day(s). Verify readiness."

    channels = [
        ("WhatsApp", f"[MOCK] Send WhatsApp → Compliance Officer: {body}"),
        ("SMS",      f"[MOCK] Send SMS → +91-XXXXXXXXXX: {body}"),
        ("Email",    f"[MOCK] Send Email → compliance@angara.in | {body}"),
    ]

    dispatched = []
    for ch, msg in channels:
        print(msg)   # ← Replace with Twilio API call in production
        dispatched.append({"channel": ch, "message": msg, "milestone_id": milestone_id})

    return dispatched


# ── Bottleneck detection ─────────────────────────────────────────

def get_bottleneck(name: str, days: int, status: str) -> str | None:
    """
    Return bottleneck cause string if milestone is delayed/overdue.
    Returns None if milestone is on track or complete.
    """
    if status == "delayed" or days < 0:
        return BOTTLENECK_RULES.get(name, DEFAULT_BOTTLENECK)
    return None