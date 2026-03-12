#!/usr/bin/env python3
"""
init_db.py — Angara sample database initialiser
───────────────────────────────────────────────────
Run once before launching the app to seed a demo project with realistic data:

    python init_db.py

What it does:
  1. Creates the SQLite DB file at data/angara.db
  2. Initialises all tables (projects, milestones, alert_log, reports)
  3. Seeds one demo project: "Jharia Block-4" (Dhanbad, Jharkhand)
  4. Seeds 5 default milestones with varied statuses (mirrors real demo state)
  5. Seeds 2 sample report records (MIS + Delay)
  6. Generates + archives both sample PDFs to data/reports_archive/
  7. Prints a summary table of what was created

─────────────────────────────────────────────────────────────────────────────
SCALABILITY NOTE — Migrating from SQLite → PostgreSQL
─────────────────────────────────────────────────────
  This script uses SQLite (stdlib, zero config). To migrate to PostgreSQL:

  Step 1 — Install driver:
      pip install psycopg2-binary sqlalchemy

  Step 2 — Update connection factory in db/database.py and db/reports_db.py:
      # SQLite (current):
      conn = sqlite3.connect(DB_PATH, check_same_thread=False)

      # PostgreSQL replacement:
      import psycopg2
      DSN  = "postgresql://user:password@host:5432/angara"
      conn = psycopg2.connect(DSN)

  Step 3 — Remove SQLite-specific PRAGMAs:
      # Remove these lines:
      conn.execute("PRAGMA journal_mode=WAL")
      conn.execute("PRAGMA foreign_keys=ON")
      # PostgreSQL enforces foreign keys by default; uses MVCC not WAL mode

  Step 4 — Update DB_PATH in utils/constants.py to point at DSN string.

  Step 5 — Add connection pooling:
      from psycopg2 import pool
      _pool = pool.ThreadedConnectionPool(minconn=1, maxconn=10, dsn=DSN)
      conn  = _pool.getconn()   # get conn
      _pool.putconn(conn)        # release conn

  The schema itself is ANSI SQL — no SQLite-specific column types or syntax.
  AUTOINCREMENT → SERIAL/BIGSERIAL in Postgres. TEXT → VARCHAR/TEXT (same).
─────────────────────────────────────────────────────────────────────────────
"""

import sys
import os
import sqlite3
from datetime import date, timedelta

# Ensure project root is on the path
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from db.database   import init_db, create_project, get_projects, get_milestones, update_milestone
from db.reports_db import init_reports_table, save_report_record, update_file_path
from utils.constants import DB_PATH, TODAY

# ── Archive dir ──────────────────────────────────────────────────
ARCHIVE_DIR = os.path.join(ROOT, "data", "reports_archive")


def _separator(title: str = ""):
    w = 60
    if title:
        pad = (w - len(title) - 2) // 2
        print("─" * pad + f" {title} " + "─" * pad)
    else:
        print("─" * w)


def main():
    _separator("Angara DB Init")
    print(f"  DB path    : {DB_PATH}")
    print(f"  Archive    : {ARCHIVE_DIR}")
    print(f"  Demo date  : {TODAY}")
    _separator()

    # ── 1. Schema ────────────────────────────────────────────────
    print("\n[1/5] Creating tables…")
    init_db()
    init_reports_table()
    print("      ✅ projects, milestones, alert_log, reports")

    # ── 2. Demo project ──────────────────────────────────────────
    print("\n[2/5] Seeding demo project…")
    projects = get_projects()
    if "Jharia Block-4" in projects["name"].values:
        pid = int(projects.loc[projects["name"] == "Jharia Block-4", "id"].values[0])
        print(f"      ℹ  Project already exists (id={pid}) — skipping creation")
    else:
        start = TODAY - timedelta(days=60)          # Started 60 days ago
        pid   = create_project(
            name       = "Jharia Block-4",
            start_date = start,
            location   = "Dhanbad, Jharkhand",
            role       = "Manager",
        )
        print(f"      ✅ 'Jharia Block-4' created (id={pid}, start={start})")

    # ── 3. Set realistic milestone statuses ──────────────────────
    print("\n[3/5] Setting milestone statuses…")
    ms_df = get_milestones(pid)

    # Map: name → (status, notes, actual_date_offset_from_today)
    STATUS_MAP = {
        "EIA Submission": (
            "complete",
            "EIA report submitted to SEIAA on schedule. Ref: SEIAA/JH/2026/014.",
            -10,        # completed 10 days ago
        ),
        "Land NOC": (
            "in_progress",
            "Application filed with District Collector. Follow-up scheduled.",
            None,
        ),
        "Forest Clearance Stage 1": (
            "delayed",
            "MoEFCC online portal offline for 3 days. Escalation sent to nodal officer.",
            None,
        ),
        "Pollution Control NOC": (
            "pending",
            "",
            None,
        ),
        "Mining Lease Grant": (
            "pending",
            "Awaiting prior approvals.",
            None,
        ),
    }

    for _, row in ms_df.iterrows():
        mapping = STATUS_MAP.get(row["name"])
        if mapping:
            status, notes, actual_offset = mapping
            actual_date = (
                (TODAY + timedelta(days=actual_offset)).isoformat()
                if actual_offset is not None else None
            )
            update_milestone(row["id"], status, notes, actual_date, "Manager")
            symbol = {"complete":"✅","in_progress":"🔵","delayed":"🔴","pending":"🟡"}.get(status,"⚪")
            print(f"      {symbol} {row['name']:35s} → {status}")

    # ── 4. Report records ─────────────────────────────────────────
    print("\n[4/5] Seeding report records…")
    try:
        conn = sqlite3.connect(DB_PATH)
        existing = conn.execute("SELECT COUNT(*) FROM reports WHERE project_id=?", (pid,)).fetchone()[0]
        conn.close()
    except Exception:
        existing = 0

    if existing > 0:
        print(f"      ℹ  {existing} report record(s) already exist — skipping")
    else:
        mis_rid = save_report_record(
            project_id      = pid,
            report_type     = "MIS_Quarterly",
            quarter         = "Q4 FY 2025-26 (Jan-Mar 2026)",
            submission_date = TODAY.isoformat(),
            submitted_by    = "Rajesh Kumar (Manager)",
            status          = "Submitted",
        )
        delay_rid = save_report_record(
            project_id      = pid,
            report_type     = "Delay_Report",
            quarter         = "N/A",
            submission_date = TODAY.isoformat(),
            submitted_by    = "Rajesh Kumar (Manager)",
            status          = "Drafted",
        )
        print(f"      ✅ MIS Quarterly record  (id={mis_rid}, status=Submitted)")
        print(f"      ✅ Delay Report record   (id={delay_rid}, status=Drafted)")

        # ── 5. Generate + archive sample PDFs ──────────────────────
        print("\n[5/5] Generating sample PDFs…")
        try:
            import pandas as pd
            from reports.pdf_generator import (
                generate_mis_quarterly, generate_delay_report, save_report,
            )
            os.makedirs(ARCHIVE_DIR, exist_ok=True)

            ms_df = get_milestones(pid)   # re-fetch with updated statuses

            mis_bytes = generate_mis_quarterly(
                project_name     = "Jharia Block-4",
                project_id       = pid,
                project_location = "Dhanbad, Jharkhand",
                project_start    = (TODAY - timedelta(days=60)).isoformat(),
                submission_date  = TODAY,
                quarter          = "Q4 FY 2025-26 (Jan-Mar 2026)",
                milestones_df    = ms_df,
                submitted_by     = "Rajesh Kumar (Manager)",
            )
            mis_path = os.path.join(ARCHIVE_DIR, "MIS_Jharia_Block-4_Q4_20260310.pdf")
            save_report(mis_bytes, mis_path)
            update_file_path(mis_rid, mis_path)
            print(f"      ✅ MIS PDF  → {mis_path}")

            delay_bytes = generate_delay_report(
                project_name     = "Jharia Block-4",
                project_id       = pid,
                project_location = "Dhanbad, Jharkhand",
                submission_date  = TODAY,
                milestones_df    = ms_df,
                submitted_by     = "Rajesh Kumar (Manager)",
            )
            delay_path = os.path.join(ARCHIVE_DIR, "Delay_Jharia_Block-4_20260310.pdf")
            save_report(delay_bytes, delay_path)
            update_file_path(delay_rid, delay_path)
            print(f"      ✅ Delay PDF → {delay_path}")

        except ImportError as e:
            print(f"      ⚠  reportlab not installed — PDFs skipped ({e})")
            print("         Run: pip install reportlab")
        except Exception as e:
            print(f"      ⚠  PDF generation error: {e}")

    # ── Summary ──────────────────────────────────────────────────
    _separator("Done")
    print()
    ms_final = get_milestones(pid)
    print(f"  Project : Jharia Block-4  (id={pid})")
    print(f"  Milestones : {len(ms_final)} total")
    for _, r in ms_final.iterrows():
        sym = {"complete":"✅","in_progress":"🔵","delayed":"🔴","pending":"🟡"}.get(r["status"],"⚪")
        print(f"    {sym} {r['name']:35s}  target={r['target_date']}")
    pdfs = [f for f in os.listdir(ARCHIVE_DIR) if f.endswith(".pdf")] \
           if os.path.exists(ARCHIVE_DIR) else []
    print(f"\n  PDFs archived : {len(pdfs)}")
    for f in pdfs:
        print(f"    📄 {f}")
    print()
    _separator()
    print()
    print("  Run the app:")
    print("    streamlit run app.py")
    print()


if __name__ == "__main__":
    main()
