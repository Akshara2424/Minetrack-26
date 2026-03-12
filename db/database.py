"""
db/database.py — SQLite schema + all CRUD for Angara Module 1.

ER DIAGRAM:
  PROJECTS ──< MILESTONES   (1:N via project_id FK)
  ALERT_LOG   (soft FK to milestones.id)
"""
import os, sqlite3
import pandas as pd
from datetime import date, timedelta
from utils.constants import DB_PATH, DEFAULT_MILESTONES

def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            start_date TEXT NOT NULL,
            location TEXT,
            created_by TEXT DEFAULT 'Manager',
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS milestones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            offset_days INTEGER NOT NULL DEFAULT 0,
            target_date TEXT NOT NULL,
            actual_date TEXT,
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK(status IN ('pending','in_progress','complete','delayed')),
            notes TEXT,
            submitted_by TEXT DEFAULT 'Officer',
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS alert_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            milestone_id INTEGER,
            channel TEXT,
            message TEXT,
            triggered_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit(); conn.close()

def create_project(name, start_date, location, role):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("INSERT INTO projects (name,start_date,location,created_by) VALUES (?,?,?,?)",
                (name, start_date.isoformat(), location, role))
    pid = cur.lastrowid
    for m_name, offset in DEFAULT_MILESTONES:
        target = start_date + timedelta(days=offset)
        cur.execute("INSERT INTO milestones (project_id,name,offset_days,target_date,status) VALUES (?,?,?,?,'pending')",
                    (pid, m_name, offset, target.isoformat()))
    conn.commit(); conn.close(); return pid

def get_projects():
    conn = get_conn()
    df = pd.read_sql_query("SELECT id,name,start_date,location,created_by,created_at FROM projects ORDER BY created_at DESC", conn)
    conn.close(); return df

def delete_project(pid):
    conn = get_conn()
    conn.execute("DELETE FROM projects WHERE id=?", (pid,))
    conn.commit(); conn.close()

def get_milestones(project_id):
    conn = get_conn()
    df = pd.read_sql_query(
        "SELECT id,name,offset_days,target_date,actual_date,status,notes,submitted_by,updated_at FROM milestones WHERE project_id=? ORDER BY offset_days",
        conn, params=(project_id,))
    conn.close(); return df

def update_milestone(mid, status, notes, actual_date, role):
    conn = get_conn()
    conn.execute("UPDATE milestones SET status=?,notes=?,actual_date=?,submitted_by=?,updated_at=datetime('now') WHERE id=?",
                 (status, notes, actual_date, role, mid))
    conn.commit(); conn.close()

def add_custom_milestone(project_id, name, target_date, notes, role):
    conn = get_conn()
    proj = conn.execute("SELECT start_date FROM projects WHERE id=?", (project_id,)).fetchone()
    if not proj: conn.close(); raise ValueError("Project not found.")
    offset = (target_date - date.fromisoformat(proj[0])).days
    conn.execute("INSERT INTO milestones (project_id,name,offset_days,target_date,notes,status,submitted_by) VALUES (?,?,?,?,?,'pending',?)",
                 (project_id, name, offset, target_date.isoformat(), notes, role))
    conn.commit(); conn.close()

def log_alert(milestone_id, channel, message):
    conn = get_conn()
    conn.execute("INSERT INTO alert_log (milestone_id,channel,message) VALUES (?,?,?)", (milestone_id, channel, message))
    conn.commit(); conn.close()