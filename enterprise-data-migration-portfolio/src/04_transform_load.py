"""Step 4 - Transform staging data into the conformed target tables.

Applies the transformation rules documented in docs/templates/source_to_target_mapping.csv:
  * trim / standardize text
  * normalize country, segment, status code-sets
  * coerce dates to ISO 8601 and numbers to typed values
  * deduplicate on the natural (business) key, keeping the last occurrence
  * derive financial measures (gross_amount, net_amount) for orders

Records that cannot be made valid enough to load (e.g. missing primary key)
are skipped and recorded as ERROR exceptions. Soft issues that are loaded but
suspicious are recorded as WARN exceptions by Step 5 (validation).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402


def transform_customers(conn):
    rows = conn.execute("SELECT * FROM stg_customers").fetchall()
    seen = {}  # customer_id -> cleaned tuple (dedupe, keep last)
    skipped = 0
    for r in rows:
        cid = common.clean_str(r["customer_id"])
        if not cid:
            common.add_exception(conn, "customers", None, r["_source_row"],
                                 "C-PK-01", "ERROR", "customer_id", r["customer_id"],
                                 "Missing primary key; record skipped")
            skipped += 1
            continue
        credit = common.parse_number(r["credit_limit"])
        seen[cid] = {
            "customer_id": cid,
            "first_name": common.clean_str(r["first_name"]),
            "last_name": common.clean_str(r["last_name"]),
            "email": (common.clean_str(r["email"]) or "").lower() or None,
            "phone": common.clean_str(r["phone"]),
            "country": common.normalize_country(r["country"]),
            "signup_date": common.parse_date(r["signup_date"]),
            "segment": common.normalize_segment(r["segment"]),
            "credit_limit": credit,
        }

    for c in seen.values():
        conn.execute(
            "INSERT INTO dim_customers (customer_id, first_name, last_name, "
            "email, phone, country, signup_date, segment, credit_limit, _loaded_at) "
            "VALUES (:customer_id, :first_name, :last_name, :email, :phone, "
            ":country, :signup_date, :segment, :credit_limit, '%s')" % common.now_iso(),
            c,
        )
    conn.commit()
    common.log_metric(conn, "transform", "customers", "target_rows", len(seen))
    common.log_metric(conn, "transform", "customers", "skipped_rows", skipped)
    print(f"  customers  -> dim_customers  {len(seen)} rows ({skipped} skipped)")


def transform_products(conn):
    rows = conn.execute("SELECT * FROM stg_products").fetchall()
    seen = {}
    skipped = 0
    for r in rows:
        pid = common.clean_str(r["product_id"])
        if not pid:
            common.add_exception(conn, "products", None, r["_source_row"],
                                 "P-PK-01", "ERROR", "product_id", r["product_id"],
                                 "Missing primary key; record skipped")
            skipped += 1
            continue
        active_raw = (common.clean_str(r["active"]) or "").lower()
        active = 1 if active_raw in ("y", "yes", "1", "true") else 0
        seen[pid] = {
            "product_id": pid,
            "product_name": common.clean_str(r["product_name"]),
            "category": common.clean_str(r["category"]),
            "unit_price": common.parse_number(r["unit_price"]),
            "currency": (common.clean_str(r["currency"]) or "").upper() or None,
            "active": active,
            "launch_date": common.parse_date(r["launch_date"]),
        }

    for p in seen.values():
        conn.execute(
            "INSERT INTO dim_products (product_id, product_name, category, "
            "unit_price, currency, active, launch_date, _loaded_at) "
            "VALUES (:product_id, :product_name, :category, :unit_price, "
            ":currency, :active, :launch_date, '%s')" % common.now_iso(),
            p,
        )
    conn.commit()
    common.log_metric(conn, "transform", "products", "target_rows", len(seen))
    common.log_metric(conn, "transform", "products", "skipped_rows", skipped)
    print(f"  products   -> dim_products   {len(seen)} rows ({skipped} skipped)")


def transform_orders(conn):
    rows = conn.execute("SELECT * FROM stg_orders").fetchall()
    seen = {}  # order_id -> cleaned dict (dedupe, keep last)
    skipped = 0
    for r in rows:
        oid = common.clean_str(r["order_id"])
        cid = common.clean_str(r["customer_id"])
        pid = common.clean_str(r["product_id"])
        if not oid or not cid or not pid:
            common.add_exception(conn, "orders", oid, r["_source_row"],
                                 "O-PK-01", "ERROR",
                                 "order_id/customer_id/product_id",
                                 f"{oid}/{cid}/{pid}",
                                 "Missing key field(s); record skipped")
            skipped += 1
            continue
        qty = common.parse_int(r["quantity"])
        price = common.parse_number(r["unit_price"])
        disc = common.parse_number(r["discount_pct"]) or 0.0
        gross = (qty or 0) * (price or 0.0)
        net = gross * (1 - disc / 100.0)
        seen[oid] = {
            "order_id": oid,
            "customer_id": cid,
            "product_id": pid,
            "order_date": common.parse_date(r["order_date"]),
            "quantity": qty,
            "unit_price": price,
            "discount_pct": disc,
            "gross_amount": round(gross, 2),
            "net_amount": round(net, 2),
            "status": common.normalize_status(r["status"]),
        }

    for o in seen.values():
        conn.execute(
            "INSERT INTO fact_orders (order_id, customer_id, product_id, "
            "order_date, quantity, unit_price, discount_pct, gross_amount, "
            "net_amount, status, _loaded_at) "
            "VALUES (:order_id, :customer_id, :product_id, :order_date, "
            ":quantity, :unit_price, :discount_pct, :gross_amount, "
            ":net_amount, :status, '%s')" % common.now_iso(),
            o,
        )
    conn.commit()
    common.log_metric(conn, "transform", "orders", "target_rows", len(seen))
    common.log_metric(conn, "transform", "orders", "skipped_rows", skipped)
    print(f"  orders     -> fact_orders    {len(seen)} rows ({skipped} skipped)")


def main() -> None:
    common.banner("STEP 4  Transform & load conformed target tables")
    conn = common.connect()
    try:
        transform_customers(conn)
        transform_products(conn)
        transform_orders(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
