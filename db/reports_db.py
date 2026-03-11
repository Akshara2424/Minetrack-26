"""
db/reports_db.py — SQLite CRUD for Module 2 report tracking

Table: reports
  id              PK
  project_id      FK → projects
  report_type     'MIS_Quarterly' | 'Delay_Report'
  quarter         e.g. 'Q4 FY 2025-26'
  submission_date ISO date of the report period
  submitted_by    name / role string
  file_path       absolute path of archived PDF (nullable)
  status          'Drafted' | 'Submitted' | 'Archived'
  gen_date        date PDF was generated
  created_at      full datetime row was inserted
"""

import os
import sqlite3
import pandas as pd
from utils.constants import DB_PATH


def _conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_reports_table():
    """Create reports table if absent. Idempotent — safe to call on every boot."""
    conn = _conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS reports (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id      INTEGER NOT NULL,
            report_type     TEXT    NOT NULL
                CHECK(report_type IN ('MIS_Quarterly','Delay_Report')),
            quarter         TEXT    NOT NULL DEFAULT 'N/A',
            submission_date TEXT    NOT NULL,
            submitted_by    TEXT    NOT NULL,
            file_path       TEXT,
            status          TEXT    NOT NULL DEFAULT 'Drafted'
                CHECK(status IN ('Drafted','Submitted','Archived')),
            gen_date        TEXT    NOT NULL DEFAULT (date('now')),
            created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
    """)
    conn.commit()
    conn.close()


# ── WRITE ────────────────────────────────────────────────────────

def save_report_record(
    project_id: int,
    report_type: str,
    quarter: str,
    submission_date: str,
    submitted_by: str,
    file_path: str = None,
    status: str = "Drafted",
) -> int:
    """Insert a report row. Returns the new row id."""
    conn = _conn()
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


def update_report_status(report_id: int, status: str):
    conn = _conn()
    conn.execute("UPDATE reports SET status=? WHERE id=?", (status, report_id))
    conn.commit()
    conn.close()


def update_file_path(report_id: int, file_path: str):
    conn = _conn()
    conn.execute("UPDATE reports SET file_path=? WHERE id=?", (file_path, report_id))
    conn.commit()
    conn.close()


def delete_report(report_id: int):
    conn = _conn()
    conn.execute("DELETE FROM reports WHERE id=?", (report_id,))
    conn.commit()
    conn.close()


# ── READ ─────────────────────────────────────────────────────────

def get_reports(project_id: int = None) -> pd.DataFrame:
    """
    Return all reports joined with project name.
    Pass project_id to filter to one project.
    """
    conn   = _conn()
    where  = "WHERE r.project_id = ?" if project_id else ""
    params = (project_id,) if project_id else ()
    df = pd.read_sql_query(
        f"""SELECT r.id, p.name AS project_name, r.project_id,
                   r.report_type, r.quarter, r.submission_date,
                   r.submitted_by, r.status, r.file_path,
                   r.gen_date, r.created_at
            FROM   reports r
            JOIN   projects p ON r.project_id = p.id
            {where}
            ORDER  BY r.created_at DESC""",
        conn, params=params,
    )
    conn.close()
    return df


def get_report_stats() -> dict:
    """
    Aggregate KPI counts for dashboard cards.
    Returns dict: total, drafted, submitted, archived, mis_count, delay_count
    """
    conn = _conn()
    cur  = conn.cursor()

    def q(sql, p=()):
        return (cur.execute(sql, p).fetchone() or [0])[0]

    stats = {
        "total":       q("SELECT COUNT(*) FROM reports"),
        "drafted":     q("SELECT COUNT(*) FROM reports WHERE status='Drafted'"),
        "submitted":   q("SELECT COUNT(*) FROM reports WHERE status='Submitted'"),
        "archived":    q("SELECT COUNT(*) FROM reports WHERE status='Archived'"),
        "mis_count":   q("SELECT COUNT(*) FROM reports WHERE report_type='MIS_Quarterly'"),
        "delay_count": q("SELECT COUNT(*) FROM reports WHERE report_type='Delay_Report'"),
    }
    conn.close()
    return stats


def auto_archive_old(days: int = 90) -> int:
    """
    Move Submitted reports older than `days` to Archived.
    Returns count of rows updated.
    """
    conn = _conn()
    cur  = conn.cursor()
    cur.execute(
        """UPDATE reports SET status='Archived'
           WHERE status='Submitted'
             AND julianday('now') - julianday(gen_date) > ?""",
        (days,),
    )
    n = cur.rowcount
    conn.commit()
    conn.close()
    return n
