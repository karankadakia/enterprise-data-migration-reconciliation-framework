"""Step 5 - Validate business rules against the conformed target tables.

Each rule maps to an id in docs/templates/validation_rules.csv. Violations are
written to the exceptions table with a severity. ERROR-level issues represent
data that should block a production cutover; WARN-level issues are tracked but
non-blocking. Step 6 turns these into the exception and reconciliation reports.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402


def validate_customers(conn):
    n = 0
    rows = conn.execute("SELECT * FROM dim_customers").fetchall()
    valid_segments = {"Enterprise", "SMB", "Consumer"}
    for r in rows:
        cid = r["customer_id"]
        if not r["email"] or not common.EMAIL_RE.match(r["email"] or ""):
            common.add_exception(conn, "customers", cid, None, "C-EMAIL-01",
                                 "ERROR", "email", r["email"], "Missing or malformed email")
            n += 1
        if r["segment"] not in valid_segments:
            common.add_exception(conn, "customers", cid, None, "C-SEG-01",
                                 "WARN", "segment", r["segment"], "Segment not in code-set")
            n += 1
        if r["credit_limit"] is None:
            common.add_exception(conn, "customers", cid, None, "C-CREDIT-01",
                                 "WARN", "credit_limit", r["credit_limit"],
                                 "Credit limit not numeric / missing")
            n += 1
        elif r["credit_limit"] < 0:
            common.add_exception(conn, "customers", cid, None, "C-CREDIT-02",
                                 "ERROR", "credit_limit", r["credit_limit"],
                                 "Negative credit limit")
            n += 1
        if r["signup_date"] is None:
            common.add_exception(conn, "customers", cid, None, "C-DATE-01",
                                 "WARN", "signup_date", r["signup_date"],
                                 "Missing or unparseable signup date")
            n += 1
        elif common.is_future_date(r["signup_date"]):
            common.add_exception(conn, "customers", cid, None, "C-DATE-02",
                                 "ERROR", "signup_date", r["signup_date"],
                                 "Signup date is in the future")
            n += 1
    return n


def validate_products(conn):
    n = 0
    rows = conn.execute("SELECT * FROM dim_products").fetchall()
    for r in rows:
        pid = r["product_id"]
        if r["unit_price"] is None:
            common.add_exception(conn, "products", pid, None, "P-PRICE-01",
                                 "WARN", "unit_price", r["unit_price"],
                                 "Missing unit price")
            n += 1
        elif r["unit_price"] < 0:
            common.add_exception(conn, "products", pid, None, "P-PRICE-02",
                                 "ERROR", "unit_price", r["unit_price"],
                                 "Negative unit price")
            n += 1
        if r["currency"] not in common.CURRENCY_WHITELIST:
            common.add_exception(conn, "products", pid, None, "P-CCY-01",
                                 "ERROR", "currency", r["currency"],
                                 "Currency not in allowed ISO 4217 set")
            n += 1
    return n


def validate_orders(conn):
    n = 0
    rows = conn.execute("SELECT * FROM fact_orders").fetchall()
    cust_ids = {r["customer_id"] for r in conn.execute(
        "SELECT customer_id FROM dim_customers").fetchall()}
    prod_ids = {r["product_id"] for r in conn.execute(
        "SELECT product_id FROM dim_products").fetchall()}
    valid_status = {"COMPLETED", "SHIPPED", "CANCELLED", "PENDING", "RETURNED"}

    for r in rows:
        oid = r["order_id"]
        if r["customer_id"] not in cust_ids:
            common.add_exception(conn, "orders", oid, None, "O-FK-01",
                                 "ERROR", "customer_id", r["customer_id"],
                                 "Customer not found in dim_customers (orphan)")
            n += 1
        if r["product_id"] not in prod_ids:
            common.add_exception(conn, "orders", oid, None, "O-FK-02",
                                 "ERROR", "product_id", r["product_id"],
                                 "Product not found in dim_products (orphan)")
            n += 1
        if r["quantity"] is None or r["quantity"] <= 0:
            common.add_exception(conn, "orders", oid, None, "O-QTY-01",
                                 "ERROR", "quantity", r["quantity"],
                                 "Quantity must be a positive integer")
            n += 1
        elif r["quantity"] > 10000:
            common.add_exception(conn, "orders", oid, None, "O-QTY-02",
                                 "WARN", "quantity", r["quantity"],
                                 "Quantity exceeds sane threshold (possible fat-finger)")
            n += 1
        if r["unit_price"] is None or r["unit_price"] <= 0:
            common.add_exception(conn, "orders", oid, None, "O-PRICE-01",
                                 "ERROR", "unit_price", r["unit_price"],
                                 "Unit price must be positive")
            n += 1
        if r["discount_pct"] is not None and not (0 <= r["discount_pct"] <= 100):
            common.add_exception(conn, "orders", oid, None, "O-DISC-01",
                                 "ERROR", "discount_pct", r["discount_pct"],
                                 "Discount percent out of 0-100 range")
            n += 1
        if r["status"] not in valid_status:
            common.add_exception(conn, "orders", oid, None, "O-STATUS-01",
                                 "ERROR", "status", r["status"],
                                 "Status not in allowed code-set")
            n += 1
        if r["order_date"] is None:
            common.add_exception(conn, "orders", oid, None, "O-DATE-01",
                                 "WARN", "order_date", r["order_date"],
                                 "Missing or unparseable order date")
            n += 1
    return n


def main() -> None:
    common.banner("STEP 5  Validate business rules")
    conn = common.connect()
    try:
        nc = validate_customers(conn)
        np = validate_products(conn)
        no = validate_orders(conn)
        conn.commit()
        common.log_metric(conn, "validate", "customers", "exceptions", nc)
        common.log_metric(conn, "validate", "products", "exceptions", np)
        common.log_metric(conn, "validate", "orders", "exceptions", no)
        print(f"  customers  {nc} exceptions")
        print(f"  products   {np} exceptions")
        print(f"  orders     {no} exceptions")
        total = conn.execute("SELECT COUNT(*) AS c FROM exceptions").fetchone()["c"]
        print(f"  total exceptions logged this run: {total}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
