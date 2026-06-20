"""Step 2 - Profile the raw source CSV files.

Produces a data profiling report (outputs/profiling_report.csv) describing,
per column: populated %, null/blank count, distinct count, min/max length,
and a small sample of distinct values. This is the discovery step that drives
the source-to-target mapping and validation-rule design in a real migration.
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

SOURCES = {
    "customers": "customers.csv",
    "products": "products.csv",
    "orders": "orders.csv",
}


def profile_file(entity, filename):
    path = os.path.join(common.DATA_DIR, filename)
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        cols = reader.fieldnames or []

    total = len(rows)
    profile = []
    for col in cols:
        values = [(r.get(col) or "").strip() for r in rows]
        nonblank = [v for v in values if v != ""]
        distinct = sorted(set(nonblank))
        lengths = [len(v) for v in nonblank] or [0]
        sample = ", ".join(distinct[:5])
        profile.append({
            "entity": entity,
            "column": col,
            "total_rows": total,
            "populated": len(nonblank),
            "null_blank": total - len(nonblank),
            "populated_pct": round(100.0 * len(nonblank) / total, 1) if total else 0.0,
            "distinct": len(distinct),
            "min_len": min(lengths),
            "max_len": max(lengths),
            "sample_values": sample,
        })
    return total, profile


def main() -> None:
    common.ensure_dirs()
    common.banner("STEP 2  Profile source data")
    conn = common.connect()
    out_path = os.path.join(common.OUTPUT_DIR, "profiling_report.csv")
    fields = ["entity", "column", "total_rows", "populated", "null_blank",
              "populated_pct", "distinct", "min_len", "max_len", "sample_values"]

    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for entity, filename in SOURCES.items():
            total, profile = profile_file(entity, filename)
            common.log_metric(conn, "profile", entity, "source_rows", total)
            print(f"  {entity:<10} {total:>3} rows, {len(profile)} columns profiled")
            for row in profile:
                writer.writerow(row)
                if row["populated_pct"] < 100.0:
                    print(f"      ! {row['column']:<14} "
                          f"{row['null_blank']} missing "
                          f"({row['populated_pct']}% populated)")
    conn.close()
    print(f"  Profiling report written to: {out_path}")


if __name__ == "__main__":
    main()
