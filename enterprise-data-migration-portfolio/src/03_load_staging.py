"""Step 3 - Load raw source CSVs into the staging layer as-is.

Every value is stored as TEXT with lineage columns (_source_file, _source_row,
_loaded_at). No cleansing happens here - that is the whole point of a raw
landing zone: capture exactly what arrived so it can be audited and replayed.
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

LOADS = [
    ("customers", "customers.csv", "stg_customers",
     ["customer_id", "first_name", "last_name", "email", "phone",
      "country", "signup_date", "segment", "credit_limit"]),
    ("products", "products.csv", "stg_products",
     ["product_id", "product_name", "category", "unit_price",
      "currency", "active", "launch_date"]),
    ("orders", "orders.csv", "stg_orders",
     ["order_id", "customer_id", "product_id", "order_date",
      "quantity", "unit_price", "discount_pct", "status"]),
]


def load(conn, entity, filename, table, columns):
    path = os.path.join(common.DATA_DIR, filename)
    all_cols = columns + ["_source_file", "_source_row", "_loaded_at"]
    placeholders = ", ".join(["?"] * len(all_cols))
    insert = f"INSERT INTO {table} ({', '.join(all_cols)}) VALUES ({placeholders})"

    count = 0
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for i, row in enumerate(reader, start=2):  # row 1 is the header
            values = [row.get(c) for c in columns]
            values += [filename, i, common.now_iso()]
            conn.execute(insert, values)
            count += 1
    conn.commit()
    common.log_metric(conn, "load_staging", entity, "rows_loaded", count)
    print(f"  {entity:<10} -> {table:<14} {count} rows loaded")


def main() -> None:
    common.banner("STEP 3  Load raw data into staging layer")
    conn = common.connect()
    try:
        for entity, filename, table, columns in LOADS:
            load(conn, entity, filename, table, columns)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
