"""Step 1 - Initialize the SQLite target database.

Creates the staging (raw) and target (conformed) schemas plus the operational
control tables (exceptions, run_log). Idempotent: re-running rebuilds the DB.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402


def main() -> None:
    common.ensure_dirs()
    common.banner("STEP 1  Initialize SQLite database")
    conn = common.connect()
    try:
        common.exec_sql_file(conn, "01_staging_schema.sql")
        common.exec_sql_file(conn, "02_target_schema.sql")
        print(f"  Database created at: {common.DB_PATH}")
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        print("  Tables created:")
        for t in tables:
            print(f"    - {t['name']}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
