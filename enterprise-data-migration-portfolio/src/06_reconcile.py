"""Step 6 - Generate exception and reconciliation reports.

Outputs:
  outputs/exception_report.csv   - every logged exception (the defect log)
  outputs/reconciliation_report.md - row-count + financial reconciliation,
                                     exception summary by rule and severity,
                                     and an overall cutover readiness verdict.
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402


def write_exception_report(conn):
    rows = conn.execute(
        "SELECT entity, natural_key, source_row, rule_id, severity, field, "
        "bad_value, message, detected_at FROM exceptions ORDER BY "
        "severity, entity, rule_id"
    ).fetchall()
    path = os.path.join(common.OUTPUT_DIR, "exception_report.csv")
    fields = ["entity", "natural_key", "source_row", "rule_id", "severity",
              "field", "bad_value", "message", "detected_at"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r[k] for k in fields})
    return path, len(rows)


def recon_counts(conn):
    pairs = [
        ("customers", "stg_customers", "dim_customers"),
        ("products", "stg_products", "dim_products"),
        ("orders", "stg_orders", "fact_orders"),
    ]
    out = []
    for entity, stg, tgt in pairs:
        s = conn.execute(f"SELECT COUNT(*) AS c FROM {stg}").fetchone()["c"]
        t = conn.execute(f"SELECT COUNT(*) AS c FROM {tgt}").fetchone()["c"]
        out.append((entity, s, t, s - t))
    return out


def main() -> None:
    common.banner("STEP 6  Reconciliation & exception reporting")
    conn = common.connect()
    try:
        exc_path, exc_count = write_exception_report(conn)
        print(f"  exception report -> {exc_path} ({exc_count} rows)")

        counts = recon_counts(conn)
        by_sev = conn.execute(
            "SELECT severity, COUNT(*) AS c FROM exceptions GROUP BY severity"
        ).fetchall()
        sev = {r["severity"]: r["c"] for r in by_sev}
        errors = sev.get("ERROR", 0)
        warns = sev.get("WARN", 0)

        by_rule = conn.execute(
            "SELECT rule_id, severity, entity, COUNT(*) AS c FROM exceptions "
            "GROUP BY rule_id, severity, entity ORDER BY c DESC, rule_id"
        ).fetchall()

        net_rev = conn.execute(
            "SELECT ROUND(COALESCE(SUM(net_amount),0),2) AS r FROM fact_orders "
            "WHERE status='COMPLETED'"
        ).fetchone()["r"]
        orphans = conn.execute(
            "SELECT COUNT(*) AS c FROM fact_orders o LEFT JOIN dim_customers c "
            "ON c.customer_id=o.customer_id WHERE c.customer_id IS NULL"
        ).fetchone()["c"]

        verdict = "GO" if errors == 0 else "NO-GO"

        path = os.path.join(common.OUTPUT_DIR, "reconciliation_report.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("# Reconciliation Report\n\n")
            fh.write(f"- **Run ID:** {common.run_id()}\n")
            fh.write(f"- **Generated:** {common.now_iso()} UTC\n")
            fh.write(f"- **Cutover readiness:** **{verdict}** "
                     f"({errors} ERROR, {warns} WARN)\n\n")

            fh.write("## 1. Row-count reconciliation (staging vs target)\n\n")
            fh.write("| Entity | Staging rows | Target rows | Delta | Note |\n")
            fh.write("|---|---|---|---|---|\n")
            for entity, s, t, d in counts:
                note = "dedup + rejected records" if d else "balanced"
                fh.write(f"| {entity} | {s} | {t} | {d} | {note} |\n")

            fh.write("\n## 2. Financial reconciliation\n\n")
            fh.write(f"- Net revenue of COMPLETED orders (target): "
                     f"**{net_rev:,.2f}**\n")
            fh.write(f"- Orphan orders (customer missing in target): "
                     f"**{orphans}**\n")

            fh.write("\n## 3. Exception summary by rule\n\n")
            fh.write("| Rule | Severity | Entity | Count |\n")
            fh.write("|---|---|---|---|\n")
            for r in by_rule:
                fh.write(f"| {r['rule_id']} | {r['severity']} | "
                         f"{r['entity']} | {r['c']} |\n")

            fh.write("\n## 4. Verdict\n\n")
            if errors == 0:
                fh.write("All blocking (ERROR) checks passed. "
                         "Dataset is **cleared for cutover**.\n")
            else:
                fh.write(f"{errors} blocking ERROR(s) must be remediated before "
                         "cutover. See `exception_report.csv` for the defect log "
                         "and route each to the owning team.\n")

        print(f"  reconciliation report -> {path}")
        print(f"  verdict: {verdict}  (ERROR={errors}, WARN={warns})")
        print(f"  completed-order net revenue: {net_rev:,.2f}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
