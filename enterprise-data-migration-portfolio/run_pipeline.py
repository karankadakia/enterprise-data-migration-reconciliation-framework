#!/usr/bin/env python3
"""End-to-end orchestrator for the Enterprise Data Migration & Reconciliation
Framework.

Runs every stage in order against a single SQLite database and a single run id:

  1. init_db          create staging + target + control schemas
  2. profile_source   profile raw CSVs -> outputs/profiling_report.csv
  3. load_staging     land raw CSVs into stg_* tables
  4. transform_load   cleanse/standardize/dedupe -> dim_* / fact_* tables
  5. validate         apply business rules -> exceptions table
  6. reconcile        write exception + reconciliation reports

Usage:
    python3 run_pipeline.py
"""
import importlib.util
import os
import sys

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
sys.path.insert(0, SRC)

STEPS = [
    "01_init_db.py",
    "02_profile_source.py",
    "03_load_staging.py",
    "04_transform_load.py",
    "05_validate.py",
    "06_reconcile.py",
]


def load_module(filename):
    name = filename[:-3]
    spec = importlib.util.spec_from_file_location(name, os.path.join(SRC, filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    import common
    print("#" * 74)
    print("ENTERPRISE DATA MIGRATION & RECONCILIATION FRAMEWORK")
    print(f"Run ID: {common.run_id()}")
    print("#" * 74)
    for step in STEPS:
        module = load_module(step)
        module.main()
    common.banner("PIPELINE COMPLETE")
    print("  Outputs written to the outputs/ directory:")
    for f in ("migration.db", "profiling_report.csv",
              "exception_report.csv", "reconciliation_report.md"):
        p = os.path.join(common.OUTPUT_DIR, f)
        status = "ok" if os.path.exists(p) else "MISSING"
        print(f"    [{status}] {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
