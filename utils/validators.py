"""
utils/validators.py — Date and input validation (no Streamlit, no DB)
Pure functions — easy to unit test.
"""

from datetime import date, timedelta
from utils.constants import TODAY


def validate_milestone_date(target_date: date, project_start: date) -> list[str]:
    """
    Validate a milestone target date.
    Returns list of error strings; empty list = valid.
    """
    errors = []
    if target_date < project_start:
        errors.append(
            f"Target date ({target_date}) cannot be before "
            f"project start ({project_start})."
        )
    if target_date < TODAY - timedelta(days=365):
        errors.append(
            f"Target date ({target_date}) is more than 1 year in the past. "
            "Please verify."
        )
    if target_date > TODAY + timedelta(days=365 * 5):
        errors.append(
            f"Target date ({target_date}) is more than 5 years ahead. "
            "Please verify."
        )
    return errors


def validate_actual_date(actual_date: date, project_start: date) -> list[str]:
    """Validate an actual completion date."""
    errors = []
    if actual_date < project_start:
        errors.append(
            f"Actual date ({actual_date}) cannot be before "
            f"project start ({project_start})."
        )
    if actual_date > TODAY + timedelta(days=1):
        errors.append(
            f"Actual completion date ({actual_date}) is in the future. "
            "Please verify."
        )
    return errors


def validate_project_start(start_date: date) -> list[str]:
    """Validate a project start date."""
    errors = []
    if start_date > TODAY + timedelta(days=365 * 2):
        errors.append("Project start date is more than 2 years in the future.")
    if start_date < date(2000, 1, 1):
        errors.append(
            "Project start date seems too far in the past (before year 2000)."
        )
    return errors


def validate_milestone_name(name: str) -> list[str]:
    """Validate a milestone name string."""
    errors = []
    if not name.strip():
        errors.append("Milestone name is required.")
    elif len(name.strip()) < 3:
        errors.append("Milestone name must be at least 3 characters.")
    elif len(name.strip()) > 120:
        errors.append("Milestone name must be under 120 characters.")
    return errors