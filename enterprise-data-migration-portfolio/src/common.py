"""Shared configuration and helper utilities for the migration framework.

Pure standard-library: sqlite3, csv, os, datetime, re. No third-party deps.
"""
from __future__ import annotations

import os
import re
import sqlite3
from datetime import datetime, timezone

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "source")
SQL_DIR = os.path.join(PROJECT_ROOT, "sql")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "outputs")
DB_PATH = os.path.join(OUTPUT_DIR, "migration.db")


def ensure_dirs() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def run_id() -> str:
    """A stable run id for the current process invocation."""
    global _RUN_ID
    return _RUN_ID


_RUN_ID = datetime.now(timezone.utc).strftime("RUN-%Y%m%d-%H%M%S")


def exec_sql_file(conn: sqlite3.Connection, filename: str) -> None:
    path = os.path.join(SQL_DIR, filename)
    with open(path, "r", encoding="utf-8") as fh:
        conn.executescript(fh.read())
    conn.commit()


def log_metric(conn, step, entity, metric, value) -> None:
    conn.execute(
        "INSERT INTO run_log (run_id, step, entity, metric, value, logged_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (run_id(), step, entity, metric, float(value), now_iso()),
    )
    conn.commit()


def add_exception(conn, entity, natural_key, source_row, rule_id,
                  severity, field, bad_value, message) -> None:
    conn.execute(
        "INSERT INTO exceptions (run_id, entity, natural_key, source_row, "
        "rule_id, severity, field, bad_value, message, detected_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (run_id(), entity, natural_key, source_row, rule_id, severity,
         field, str(bad_value), message, now_iso()),
    )


# --------------------------------------------------------------------------
# Reusable cleansing / validation primitives
# --------------------------------------------------------------------------
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

COUNTRY_MAP = {
    "usa": "USA", "us": "USA", "united states": "USA",
    "uk": "UK", "united kingdom": "UK",
    "spain": "Spain", "china": "China", "india": "India",
    "brazil": "Brazil", "mexico": "Mexico", "canada": "Canada",
}

SEGMENT_MAP = {
    "enterprise": "Enterprise", "smb": "SMB", "consumer": "Consumer",
}

STATUS_MAP = {
    "completed": "COMPLETED", "shipped": "SHIPPED", "cancelled": "CANCELLED",
    "pending": "PENDING", "returned": "RETURNED",
}

CURRENCY_WHITELIST = {"USD", "EUR", "GBP"}


def clean_str(value):
    if value is None:
        return None
    v = value.strip()
    return v if v else None


def parse_date(value):
    """Return ISO date string or None. Accepts YYYY-MM-DD and YYYY/MM/DD."""
    v = clean_str(value)
    if not v:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(v, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def parse_number(value):
    v = clean_str(value)
    if v is None:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def parse_int(value):
    n = parse_number(value)
    if n is None:
        return None
    return int(n)


def normalize_country(value):
    v = clean_str(value)
    if not v:
        return None
    return COUNTRY_MAP.get(v.lower(), v)


def normalize_segment(value):
    v = clean_str(value)
    if not v:
        return None
    return SEGMENT_MAP.get(v.lower(), v)


def normalize_status(value):
    v = clean_str(value)
    if not v:
        return None
    return STATUS_MAP.get(v.lower())  # None if unknown -> flagged by validation


def is_future_date(iso_date):
    if not iso_date:
        return False
    try:
        return datetime.strptime(iso_date, "%Y-%m-%d").date() > datetime.now(timezone.utc).date()
    except ValueError:
        return False


def banner(title: str) -> None:
    line = "=" * 74
    print(f"\n{line}\n{title}\n{line}")
