"""Interactive sales tracker for the DummyJSON sample warehouse."""
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

from config import DATABASE_PATH

st.set_page_config(page_title="E-Commerce Sales Tracker", page_icon="🛒", layout="wide")
st.title("E-Commerce Sales Tracker")
st.caption(
    "Demo data from DummyJSON. Sample dates are generated for charting and are "
    "not real purchase dates or evidence of actual merchant performance."
)

if not Path(DATABASE_PATH).exists():
    st.warning("Warehouse not found. Run `python -m src.pipeline` first.")
    st.stop()

con = duckdb.connect(str(DATABASE_PATH), read_only=True)
try:
    orders = con.execute("SELECT * FROM orders").df()
    order_items = con.execute("SELECT * FROM order_items").df()
    products = con.execute("SELECT * FROM products").df()
    customers = con.execute("SELECT * FROM customers").df()
finally:
    con.close()

if orders.empty:
    st.info("The source returned no carts.")
    st.stop()

orders["sample_order_date"] = pd.to_datetime(orders["sample_order_date"])
low = orders["sample_order_date"].min().date()
high = orders["sample_order_date"].max().date()
date_range = st.sidebar.date_input(
    "Sample date range", value=(low, high), min_value=low, max_value=high
)
if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start, end = date_range
else:
    start = end = date_range

filtered = orders[
    orders["sample_order_date"].dt.date.between(start, end)
].copy()
filtered_items = order_items[
    order_items["order_id"].isin(filtered["order_id"])
].copy()

revenue = float(filtered["total_amount"].sum())
order_count = len(filtered)
units = int(filtered["total_quantity"].sum())
aov = revenue / order_count if order_count else 0.0

def compact_currency(value: float) -> str:
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:,.2f}M"
    if abs(value) >= 1_000:
        return f"${value / 1_000:,.1f}K"
    return f"${value:,.2f}"

k1, k2, k3, k4 = st.columns(4)
k1.metric("Sample gross sales", compact_currency(revenue))
k2.metric("Orders", f"{order_count:,}")
k3.metric("Units sold", f"{units:,}")
k4.metric("Average order value", compact_currency(aov))

if filtered.empty:
    st.info("No orders fall within the selected sample date range.")
    st.stop()

left, right = st.columns(2)
with left:
    trend = (
        filtered.set_index("sample_order_date")["total_amount"]
        .resample("W").sum().rename("sample_sales").reset_index()
    )
    st.subheader("Weekly sales (sample dates)")
    fig = px.line(
        trend, x="sample_order_date", y="sample_sales", markers=True,
        labels={"sample_order_date": "Sample week", "sample_sales": "Sample sales"},
    )
    st.plotly_chart(fig, use_container_width=True)

with right:
    product_sales = (
        filtered_items.groupby("product_id", as_index=False)
        .agg(units_sold=("quantity", "sum"), gross_sales=("line_total", "sum"))
        .merge(products[["product_id", "title", "category"]], on="product_id", how="left")
        .sort_values("gross_sales", ascending=False)
        .head(10)
    )
    st.subheader("Top products in selected period")
    product_fig = px.bar(
        product_sales.sort_values("gross_sales"),
        x="gross_sales", y="title", orientation="h",
        labels={"gross_sales": "Sample sales", "title": "Product"},
        hover_data=["category", "units_sold"],
    )
    st.plotly_chart(product_fig, use_container_width=True)

st.subheader("Customer performance in selected period")
customer_sales = (
    filtered.groupby("customer_id", as_index=False)
    .agg(order_count=("order_id", "nunique"),
         sample_sales=("total_amount", "sum"))
    .merge(customers, on="customer_id", how="left")
    .sort_values("sample_sales", ascending=False)
)
st.dataframe(
    customer_sales[["customer_id", "customer_name", "city", "order_count", "sample_sales"]],
    use_container_width=True, hide_index=True,
    column_config={
        "sample_sales": st.column_config.NumberColumn("Sample sales", format="$%.2f"),
        "order_count": st.column_config.NumberColumn("Orders", format="%d"),
    },
)

st.subheader("Orders in selected period")
st.dataframe(
    filtered.sort_values("sample_order_date", ascending=False),
    use_container_width=True, hide_index=True,
    column_config={
        "total_amount": st.column_config.NumberColumn("Sample order amount", format="$%.2f"),
        "sample_order_date": st.column_config.DateColumn("Sample date"),
    },
)
st.download_button(
    "Download filtered orders (CSV)",
    filtered.to_csv(index=False).encode("utf-8"),
    file_name="sample_orders.csv",
    mime="text/csv",
)
