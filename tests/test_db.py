"""Unit tests for the database layer. Run with:  pytest

These tests use a temporary database, so they never touch your real data.
"""
import os
import sys
from datetime import date, timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import db


@pytest.fixture
def temp_db(tmp_path):
    """Point the DB at a fresh temp file for each test."""
    config.DB_PATH = str(tmp_path / "test.db")
    db.init_db()
    yield


def test_add_and_get(temp_db):
    pid = db.add_prospect(company="Acme", contact_name="Jane Doe", email="jane@acme.com")
    p = db.get_prospect(pid)
    assert p["company"] == "Acme"
    assert p["contact_name"] == "Jane Doe"
    assert p["status"] == "new"


def test_update(temp_db):
    pid = db.add_prospect(company="Acme")
    db.update_prospect(pid, status="sent", sent_at="2026-06-17")
    p = db.get_prospect(pid)
    assert p["status"] == "sent"
    assert p["sent_at"] == "2026-06-17"


def test_list_and_filter(temp_db):
    db.add_prospect(company="A", status="new")
    db.add_prospect(company="B", status="sent")
    assert len(db.list_prospects()) == 2
    assert len(db.list_prospects(status="sent")) == 1


def test_import_csv(temp_db, tmp_path):
    csv = tmp_path / "leads.csv"
    csv.write_text(
        "Company,Name,Email,Website\n"
        "Foo Inc,Alice,alice@foo.com,foo.com\n"
        "Bar Ltd,Bob,,bar.com\n"
    )
    n = db.import_csv(str(csv))
    assert n == 2
    companies = {p["company"] for p in db.list_prospects()}
    assert companies == {"Foo Inc", "Bar Ltd"}


def test_due_for_followup(temp_db):
    old = (date.today() - timedelta(days=5)).isoformat()
    recent = date.today().isoformat()
    db.add_prospect(company="Due", status="sent", sent_at=old)
    db.add_prospect(company="TooRecent", status="sent", sent_at=recent)
    db.add_prospect(company="Replied", status="sent", sent_at=old, replied=1)
    due = db.due_for_followup(1)
    names = {p["company"] for p in due}
    assert names == {"Due"}  # recent not due yet, replied skipped
