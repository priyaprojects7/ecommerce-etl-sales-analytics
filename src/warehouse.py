"""Load normalized tables into DuckDB and create reporting views."""
from pathlib import Path

import duckdb
import pandas as pd


def load_warehouse(tables: dict[str, pd.DataFrame], database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(database_path))
    try:
        for name, frame in tables.items():
            con.register("incoming_frame", frame)
            con.execute(f"CREATE OR REPLACE TABLE {name} AS SELECT * FROM incoming_frame")
            con.unregister("incoming_frame")
        con.execute("""
            CREATE OR REPLACE VIEW daily_sales AS
            SELECT sample_order_date, COUNT(*) AS order_count,
                   SUM(total_amount) AS gross_sales, SUM(total_quantity) AS units_sold
            FROM orders GROUP BY sample_order_date ORDER BY sample_order_date
        """)
        con.execute("""
            CREATE OR REPLACE VIEW product_performance AS
            SELECT p.product_id, p.title, p.category, p.brand,
                   SUM(i.quantity) AS units_sold, ROUND(SUM(i.line_total), 2) AS gross_sales,
                   COUNT(DISTINCT i.order_id) AS order_count
            FROM order_items i JOIN products p USING (product_id)
            GROUP BY p.product_id, p.title, p.category, p.brand
            ORDER BY gross_sales DESC
        """)
        con.execute("""
            CREATE OR REPLACE VIEW customer_performance AS
            SELECT c.customer_id, c.customer_name, c.city,
                   COUNT(DISTINCT o.order_id) AS order_count,
                   ROUND(COALESCE(SUM(o.total_amount), 0), 2) AS lifetime_sample_sales
            FROM customers c LEFT JOIN orders o USING (customer_id)
            GROUP BY c.customer_id, c.customer_name, c.city
        """)
    finally:
        con.close()
