"""Interactive sales tracker for the DummyJSON sample warehouse."""
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

from config import DATABASE_PATH

st.set_page_config(page_title="E-Commerce Sales Tracker", layout="wide")
st.title("E-Commerce Sales Tracker")
st.caption("DummyJSON demo carts. Sample dates are generated for chart demonstration; they are not real purchase dates.")

if not Path(DATABASE_PATH).exists():
    st.warning("Warehouse not found. Run python -m src.pipeline first.")
    st.stop()

con = duckdb.connect(str(DATABASE_PATH), read_only=True)
try:
    orders = con.execute("SELECT * FROM orders").df()
    products = con.execute("SELECT * FROM product_performance").df()
    customers = con.execute("SELECT * FROM customer_performance").df()
finally:
    con.close()

if orders.empty:
    st.info("The source returned no carts.")
    st.stop()

orders["sample_order_date"] = pd.to_datetime(orders["sample_order_date"])
low, high = orders["sample_order_date"].min().date(), orders["sample_order_date"].max().date()
date_range = st.sidebar.date_input("Sample date range", value=(low, high), min_value=low, max_value=high)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start, end = date_range
else:
    start = end = date_range
filtered = orders[orders["sample_order_date"].dt.date.between(start, end)]
revenue = filtered["total_amount"].sum()
count = len(filtered)
units = filtered["total_quantity"].sum()
a, b, c, d = st.columns(4)
a.metric("Sample gross sales", f"${revenue:,.2f}")
b.metric("Orders", f"{count:,}")
c.metric("Units sold", f"{units:,}")
d.metric("Average order value", f"${revenue / count:,.2f}" if count else "$0.00")

left, right = st.columns(2)
with left:
    trend = filtered.groupby("sample_order_date", as_index=False)["total_amount"].sum()
    st.subheader("Sales by sample date")
    st.plotly_chart(px.line(trend, x="sample_order_date", y="total_amount", markers=True), use_container_width=True)
with right:
    st.subheader("Top products across the sample")
    st.plotly_chart(px.bar(products.head(10), x="gross_sales", y="title", orientation="h"), use_container_width=True)

st.subheader("Customer performance")
st.dataframe(customers.sort_values("lifetime_sample_sales", ascending=False), use_container_width=True, hide_index=True)
st.subheader("Filtered orders")
st.dataframe(filtered.sort_values("sample_order_date", ascending=False), use_container_width=True, hide_index=True)
st.download_button("Download filtered orders", filtered.to_csv(index=False).encode("utf-8"),
                   "sample_orders.csv", "text/csv")
