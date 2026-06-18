"""SQLite storage for prospects and outreach state."""
import sqlite3
import csv
from datetime import datetime, date, timedelta
from contextlib import contextmanager

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS prospects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company TEXT NOT NULL,
    contact_name TEXT,
    title TEXT,
    email TEXT,
    linkedin TEXT,
    website TEXT,
    company_blurb TEXT,         -- one-line description of what they do
    status TEXT DEFAULT 'new',  -- new|drafted|sent|followup1|followup2|replied|closed
    draft_subject TEXT,
    draft_body TEXT,
    sent_at TEXT,
    followup1_at TEXT,
    followup2_at TEXT,
    replied INTEGER DEFAULT 0,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def add_prospect(**fields):
    cols = ", ".join(fields.keys())
    placeholders = ", ".join("?" for _ in fields)
    with get_conn() as conn:
        cur = conn.execute(
            f"INSERT INTO prospects ({cols}) VALUES ({placeholders})",
            tuple(fields.values()),
        )
        return cur.lastrowid


# Apollo exports use inconsistent headers; map several possibilities to our schema.
CSV_MAPPING = {
    "company": ["Company", "Company Name", "company"],
    "contact_name": ["Name", "Full Name", "First Name", "contact_name"],
    "title": ["Title", "Job Title", "title"],
    "email": ["Email", "email"],
    "linkedin": ["Person Linkedin Url", "LinkedIn", "linkedin"],
    "website": ["Website", "Company Website", "website"],
    "company_blurb": ["Short Description", "Keywords", "company_blurb"],
}


def import_csv(path):
    """Import an Apollo-style CSV export. Returns number of rows added."""
    added = 0
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            fields = {}
            for our_key, candidates in CSV_MAPPING.items():
                for col in candidates:
                    if col in row and (row[col] or "").strip():
                        fields[our_key] = row[col].strip()
                        break
            if not fields.get("company"):
                continue
            add_prospect(**fields)
            added += 1
    return added


def list_prospects(status=None):
    q, args = "SELECT * FROM prospects", ()
    if status:
        q += " WHERE status = ?"
        args = (status,)
    q += " ORDER BY id"
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(q, args).fetchall()]


def get_prospect(pid):
    with get_conn() as conn:
        r = conn.execute("SELECT * FROM prospects WHERE id = ?", (pid,)).fetchone()
        return dict(r) if r else None


def update_prospect(pid, **fields):
    sets = ", ".join(f"{k} = ?" for k in fields)
    with get_conn() as conn:
        conn.execute(
            f"UPDATE prospects SET {sets} WHERE id = ?",
            tuple(fields.values()) + (pid,),
        )


def due_for_followup(stage):
    """Prospects due for follow-up 1 or 2 and not yet marked as replied."""
    today = date.today()
    out = []
    for p in list_prospects():
        if p["replied"]:
            continue
        if stage == 1 and p["status"] == "sent" and p["sent_at"]:
            due = datetime.fromisoformat(p["sent_at"]).date() + timedelta(
                days=config.FOLLOWUP_1_DAYS
            )
            if today >= due:
                out.append(p)
        elif stage == 2 and p["status"] == "followup1" and p["followup1_at"]:
            gap = config.FOLLOWUP_2_DAYS - config.FOLLOWUP_1_DAYS
            due = datetime.fromisoformat(p["followup1_at"]).date() + timedelta(days=gap)
            if today >= due:
                out.append(p)
    return out
