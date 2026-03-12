# ⛏️ Angara — Integrated Compliance System

**Modules 1 & 2 — Coal Mine Regulatory Tracker + Reporting**
IIT-BHU Angara · Jindal Steel & Power

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Seed demo database
python init_db.py

# 3. Launch
streamlit run app.py
```

## Structure

```
angara/
├── app.py                    ← Entry point (streamlit run app.py)
├── init_db.py                ← DB seed script (run once)
├── requirements.txt
│
├── auth/                     ← Login + role guards
├── components/               ← One file per page/view
│   ├── dashboard.py          ← M1: KPI + timeline
│   ├── monitoring.py         ← M1: Gantt + alerts
│   ├── update_form.py        ← M1: edit milestone
│   ├── add_milestone.py      ← M1: custom milestone
│   ├── officer_view.py       ← M1: officer entry wrapper
│   ├── report_form.py        ← M2: generate PDF report
│   └── reports_dashboard.py  ← M2: submission tracking
│
├── db/
│   ├── database.py           ← M1 CRUD (projects, milestones)
│   └── reports_db.py         ← M2 CRUD (reports table)
│
├── reports/
│   └── pdf_generator.py      ← ReportLab MIS + Delay PDFs
│
├── utils/
│   ├── constants.py          ← TODAY, DB_PATH, defaults
│   ├── validators.py         ← date/name validation
│   └── alerts.py             ← urgency, bottleneck, mock alerts
│
└── data/
    ├── angara.db          ← SQLite DB (auto-created)
    └── reports_archive/      ← Generated PDFs (auto-created)
```

## Scalability — SQLite → PostgreSQL

See `init_db.py` for full migration notes. Summary:
1. `pip install psycopg2-binary`
2. Replace `sqlite3.connect(DB_PATH)` with `psycopg2.connect(DSN)` in `db/database.py` + `db/reports_db.py`
3. Remove `PRAGMA` lines
4. Schema is ANSI SQL — no changes needed
