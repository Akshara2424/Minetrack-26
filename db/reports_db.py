"""
db/reports_db.py — SQLite CRUD for Module 2 report tracking

Adds a `reports` table to track generated PDFs:
    id, project_id, report_type, quarter, submission_date,
    submitted_by, file_path, status, created_at
"""

import os
import sqlite3
import pandas as pd
from utils.constants import DB_PATH


def get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_reports_table():
    """Create reports table if it doesn't exist."""
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS reports (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id      INTEGER NOT NULL,
            report_type     TEXT    NOT NULL
                            CHECK(report_type IN ('MIS_Quarterly', 'Delay_Report')),
            quarter         TEXT,
            submission_date TEXT    NOT NULL,
            submitted_by    TEXT    NOT NULL,
            file_path       TEXT,
            status          TEXT    NOT NULL DEFAULT 'Drafted'
                            CHECK(status IN ('Drafted', 'Submitted', 'Archived')),
            created_at      TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
    """)
    conn.commit()
    conn.close()


def save_report_record(
    project_id: int,
    report_type: str,
    quarter: str,
    submission_date: str,
    submitted_by: str,
    file_path: str = None,
    status: str = "Drafted",
) -> int:
    """Insert a report record and return its id."""
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute(
        """INSERT INTO reports
           (project_id, report_type, quarter, submission_date,
            submitted_by, file_path, status)
           VALUES (?,?,?,?,?,?,?)""",
        (project_id, report_type, quarter, submission_date,
         submitted_by, file_path, status),
    )
    rid = cur.lastrowid
    conn.commit()
    conn.close()
    return rid


def get_reports(project_id: int = None) -> pd.DataFrame:
    """Fetch all reports, optionally filtered by project."""
    conn  = get_conn()
    query = """
        SELECT r.id, p.name AS project_name, r.report_type,
               r.quarter, r.submission_date, r.submitted_by,
               r.status, r.file_path, r.created_at
        FROM reports r
        JOIN projects p ON r.project_id = p.id
    """
    params = ()
    if project_id:
        query  += " WHERE r.project_id = ?"
        params  = (project_id,)
    query += " ORDER BY r.created_at DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def update_report_status(report_id: int, status: str):
    conn = get_conn()
    conn.execute(
        "UPDATE reports SET status=? WHERE id=?",
        (status, report_id),
    )
    conn.commit()
    conn.close()


def delete_report(report_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM reports WHERE id=?", (report_id,))
    conn.commit()
    conn.close()
