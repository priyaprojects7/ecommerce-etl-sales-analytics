"""Plain-language e-commerce sample sales and product workspace."""
from pathlib import Path
from io import BytesIO

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

from config import DATABASE_PATH

st.set_page_config(page_title="E-Commerce Sales Tracker", page_icon="🛒", layout="wide")
st.title("E-Commerce Analytics")
st.caption("A business intelligence workspace for exploring sales, products, customers, and data quality.")

st.markdown("""
<style>
.block-container {padding-top: 1.7rem; padding-bottom: 3rem; max-width: 1500px;}
[data-testid="stMetric"] {background: linear-gradient(135deg, rgba(49, 92, 150, .13), rgba(49, 92, 150, .035)); border: 1px solid rgba(120,140,170,.22); padding: 16px 18px; border-radius: 14px;}
[data-testid="stTabs"] button {font-weight: 600; padding-top: 12px; padding-bottom: 12px;}
[data-testid="stSidebar"] {border-right: 1px solid rgba(120,140,170,.18);}
h1 {letter-spacing: -1.2px;}
div[data-testid="stDataFrame"] {border: 1px solid rgba(120,140,170,.2); border-radius: 12px;}
</style>
""", unsafe_allow_html=True)

st.write("Explore company performance, compare periods, investigate products and customers, and inspect the underlying records.")

with st.expander("Start here: what am I looking at?", expanded=True):
    st.markdown(
        """
        **This dashboard answers everyday shop questions:** How much was ordered?
        Which products appear most often? Which customers placed orders? Which
        products have low listed stock?

        **Important data note:** This version uses DummyJSON sample carts, not a
        real store's transaction history. The API does not provide actual purchase
        dates, so dates are generated to demonstrate date filters and charts.
        Values are sample-data values, not a store's verified revenue or profit.
        """
    )
    st.markdown(
        """
        - **Sales:** the order value recorded in the source data. It is not profit unless product costs and other expenses are included.
        - **Orders:** the number of orders in the current filters.
        - **Units:** the total quantity of items across those orders.
        - **Average order value:** sales divided by the number of orders.
        - **Product rating:** the rating value supplied by the dataset, when available.
        - **Stock:** the inventory quantity supplied by the dataset. Check its date and source before treating it as live stock.
        """
    )

def read_table(file):
    """Read supported tabular formats into a dataframe or workbook tables."""
    if file is None:
        return None
    suffix = Path(file.name).suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(file)
    if suffix in {".xlsx", ".xls"}:
        excel = pd.ExcelFile(file)
        required_sheets = ["orders", "order_items", "products", "customers"]
        if set(required_sheets).issubset(set(excel.sheet_names)):
            return {name: pd.read_excel(excel, sheet_name=name) for name in required_sheets}
        return pd.read_excel(excel, sheet_name=excel.sheet_names[0])
    if suffix == ".json":
        return pd.read_json(file)
    if suffix == ".parquet":
        return pd.read_parquet(file)
    raise ValueError("Supported formats: CSV, XLSX, XLS, JSON, and Parquet.")


def normalize_single_csv(frame):
    """Turn a flat order-line CSV into the four related tables used by the dashboard."""
    frame = frame.copy()
    frame.columns = [str(col).strip().lower().replace(" ", "_") for col in frame.columns]
    aliases = {
        "order_date": "sample_order_date",
        "product_name": "title",
        "product_title": "title",
        "item_quantity": "quantity",
        "unit_cost": "unit_price",
        "customer": "customer_name",
        "name": "customer_name",
        "location": "city",
    }
    frame = frame.rename(columns={k: v for k, v in aliases.items() if k in frame.columns and v not in frame.columns})
    required = {"order_id", "customer_id", "sample_order_date", "product_id", "quantity", "unit_price", "title", "category"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(
            "A single CSV must contain order-line columns: " + ", ".join(sorted(required)) +
            ". Missing: " + ", ".join(sorted(missing)) +
            ". For separate files, use the four CSV uploaders below."
        )
    if "line_total" not in frame.columns:
        frame["line_total"] = pd.to_numeric(frame["quantity"], errors="coerce") * pd.to_numeric(frame["unit_price"], errors="coerce")
    if "total_amount" not in frame.columns:
        frame["total_amount"] = frame.groupby("order_id")["line_total"].transform("sum")
    if "price" not in frame.columns:
        frame["price"] = frame["unit_price"]
    if "stock" not in frame.columns:
        frame["stock"] = 0
    if "rating" not in frame.columns:
        frame["rating"] = 0
    if "customer_name" not in frame.columns:
        frame["customer_name"] = frame["customer_id"].astype(str)
    if "city" not in frame.columns:
        frame["city"] = "Unknown"
    if "brand" not in frame.columns:
        frame["brand"] = "Unknown"
    orders = frame[["order_id", "customer_id", "sample_order_date", "total_amount"]].drop_duplicates("order_id").copy()
    items = frame[["order_id", "product_id", "quantity", "unit_price", "line_total"]].copy()
    products = frame[["product_id", "title", "category", "price", "stock", "rating", "brand"]].drop_duplicates("product_id").copy()
    customers = frame[["customer_id", "customer_name", "city"]].drop_duplicates("customer_id").copy()
    return {"orders": orders, "order_items": items, "products": products, "customers": customers}



def normalize_walmart_csv(frame):
    """Adapt the common public Walmart sales CSV layout to dashboard tables."""
    frame = frame.copy()
    frame.columns = [str(col).strip().lower().replace(" ", "_") for col in frame.columns]
    aliases = {
        "invoice_id": "order_id",
        "product_line": "title",
        "unit_price": "unit_price",
        "quantity": "quantity",
        "date": "sample_order_date",
        "city": "city",
        "rating": "rating",
        "total": "total_amount",
    }
    frame = frame.rename(columns={k: v for k, v in aliases.items() if k in frame.columns and v not in frame.columns})
    needed = {"order_id", "title", "unit_price", "quantity", "sample_order_date", "total_amount", "city"}
    missing = needed - set(frame.columns)
    if missing:
        raise ValueError(
            "This file does not match the supported flat order-line or Walmart sales layouts. "
            "Missing columns: " + ", ".join(sorted(missing))
        )
    if "customer_id" not in frame.columns:
        frame["customer_id"] = pd.factorize(frame["order_id"].astype(str))[0] + 1
    if "product_id" not in frame.columns:
        frame["product_id"] = pd.factorize(frame["title"].astype(str))[0] + 1
    if "category" not in frame.columns:
        frame["category"] = frame["title"].astype(str)
    if "price" not in frame.columns:
        frame["price"] = frame["unit_price"]
    if "stock" not in frame.columns:
        frame["stock"] = 0
    if "rating" not in frame.columns:
        frame["rating"] = 0
    if "customer_name" not in frame.columns:
        frame["customer_name"] = "Customer " + frame["customer_id"].astype(str)
    if "brand" not in frame.columns:
        frame["brand"] = "Unknown"
    frame["line_total"] = pd.to_numeric(frame["unit_price"], errors="coerce") * pd.to_numeric(frame["quantity"], errors="coerce")
    orders = frame[["order_id", "customer_id", "sample_order_date", "total_amount"]].drop_duplicates("order_id").copy()
    items = frame[["order_id", "product_id", "quantity", "unit_price", "line_total"]].copy()
    products = frame[["product_id", "title", "category", "price", "stock", "rating", "brand"]].drop_duplicates("product_id").copy()
    customers = frame[["customer_id", "customer_name", "city"]].drop_duplicates("customer_id").copy()
    return {"orders": orders, "order_items": items, "products": products, "customers": customers}


def normalize_uploads(uploaded):
    """Validate uploaded tables and standardize the columns used by this app."""
    required = {
        "orders": {"order_id", "customer_id", "sample_order_date", "total_amount"},
        "order_items": {"order_id", "product_id", "quantity", "unit_price"},
        "products": {"product_id", "title", "category", "price", "stock", "rating"},
        "customers": {"customer_id", "customer_name", "city"},
    }
    cleaned = {}
    for name, frame in uploaded.items():
        if frame is None:
            raise ValueError(f"Missing required {name} table.")
        frame = frame.copy()
        frame.columns = [str(col).strip().lower().replace(" ", "_") for col in frame.columns]
        if name == "orders" and "sample_order_date" not in frame.columns and "order_date" in frame.columns:
            frame = frame.rename(columns={"order_date": "sample_order_date"})
        missing = required[name] - set(frame.columns)
        if missing:
            raise ValueError(f"{name}: missing required columns: {', '.join(sorted(missing))}")
        cleaned[name] = frame

    orders = cleaned["orders"]
    orders["sample_order_date"] = pd.to_datetime(orders["sample_order_date"], errors="coerce")
    if orders["sample_order_date"].isna().any():
        raise ValueError("orders.sample_order_date contains blank or invalid dates.")
    for col in ("order_id", "customer_id", "total_amount"):
        orders[col] = pd.to_numeric(orders[col], errors="coerce")
    if orders[["order_id", "customer_id", "total_amount"]].isna().any().any():
        raise ValueError("Orders contain blank or non-numeric IDs or totals.")
    if orders["order_id"].duplicated().any():
        raise ValueError("orders.order_id must be unique.")
    if (orders["total_amount"] < 0).any():
        raise ValueError("Order totals cannot be negative.")
    if "total_quantity" not in orders.columns:
        orders["total_quantity"] = 0

    items = cleaned["order_items"]
    for col in ("order_id", "product_id", "quantity", "unit_price"):
        items[col] = pd.to_numeric(items[col], errors="coerce")
    if items[["order_id", "product_id", "quantity", "unit_price"]].isna().any().any():
        raise ValueError("Order items contain blank or non-numeric required values.")
    if (items["quantity"] <= 0).any() or (items["unit_price"] < 0).any():
        raise ValueError("Order item quantities must be positive and prices cannot be negative.")
    if "line_total" not in items.columns:
        items["line_total"] = items["quantity"] * items["unit_price"]
    if "discount_percentage" not in items.columns:
        items["discount_percentage"] = 0
    if "discounted_total" not in orders.columns:
        orders["discounted_total"] = orders["total_amount"]
    if "source_reported_total" not in orders.columns:
        orders["source_reported_total"] = orders["total_amount"]

    products = cleaned["products"]
    for col in ("product_id", "price", "stock", "rating"):
        products[col] = pd.to_numeric(products[col], errors="coerce")
    customers = cleaned["customers"]
    customers["customer_id"] = pd.to_numeric(customers["customer_id"], errors="coerce")
    if products["product_id"].isna().any() or customers["customer_id"].isna().any():
        raise ValueError("Product and customer IDs must be numeric and non-empty.")
    if "brand" not in products.columns:
        products["brand"] = "Unknown"
    if not set(items["order_id"]).issubset(set(orders["order_id"])):
        raise ValueError("Some order items refer to orders that are missing.")
    if not set(items["product_id"]).issubset(set(products["product_id"])):
        raise ValueError("Some order items refer to products that are missing.")
    if not set(orders["customer_id"]).issubset(set(customers["customer_id"])):
        raise ValueError("Some orders refer to customers that are missing.")
    if "total_quantity" not in orders.columns or (orders["total_quantity"] == 0).all():
        quantities = items.groupby("order_id")["quantity"].sum()
        orders["total_quantity"] = orders["order_id"].map(quantities).fillna(0)
    orders["total_amount"] = pd.to_numeric(orders["total_amount"])
    orders["sample_order_date"] = pd.to_datetime(orders["sample_order_date"])
    return orders, items, products, customers


st.sidebar.header("Use your own data")
st.sidebar.caption("Upload one data file. Supported formats: CSV, Excel, JSON, and Parquet.")
data_file = st.sidebar.file_uploader(
    "Choose a dataset",
    type=["csv", "xlsx", "xls", "json", "parquet"],
    key="dataset_upload",
)
uploaded_tables = None
try:
    if data_file is not None:
        raw_data = read_table(data_file)
        if isinstance(raw_data, dict):
            uploaded_tables = raw_data
        else:
            normalized_columns = {str(col).strip().lower().replace(" ", "_") for col in raw_data.columns}
            if {"invoice_id", "product_line", "unit_price", "quantity", "date", "total", "city"}.issubset(normalized_columns):
                uploaded_tables = normalize_walmart_csv(raw_data)
            else:
                uploaded_tables = normalize_single_csv(raw_data)
        orders, order_items, products, customers = normalize_uploads(uploaded_tables)
        st.sidebar.success(f"Loaded {len(orders):,} orders from {data_file.name}.")
    else:
        orders = order_items = products = customers = None
except Exception as exc:
    st.sidebar.error(f"Upload could not be used: {exc}")
    st.stop()

if uploaded_tables is None and not Path(DATABASE_PATH).exists():
    st.warning("Warehouse not found. Run `python -m src.pipeline` or upload your own dataset in the sidebar.")
    st.stop()

if uploaded_tables is None:
    con = duckdb.connect(str(DATABASE_PATH), read_only=True)
    try:
        orders = con.execute("SELECT * FROM orders").df()
        order_items = con.execute("SELECT * FROM order_items").df()
        products = con.execute("SELECT * FROM products").df()
        customers = con.execute("SELECT * FROM customers").df()
    finally:
        con.close()
    st.caption("Showing the built-in DummyJSON demo dataset. Upload your own files in the sidebar to switch datasets.")
else:
    st.caption("Showing your uploaded dataset. Files are used in this browser session and are not saved to the repository.")

is_sample = uploaded_tables is None
sales_label = "Sample gross sales" if is_sample else "Sales total"

if orders.empty:
    st.info("No sample carts were returned by the source.")
    st.stop()

orders["sample_order_date"] = pd.to_datetime(orders["sample_order_date"])
low = orders["sample_order_date"].min().date()
high = orders["sample_order_date"].max().date()

st.sidebar.header("Explore the data")
date_range = st.sidebar.date_input(
    "Order date range" if not is_sample else "Sample date range", value=(low, high), min_value=low, max_value=high,
    help="These dates are generated for demonstration, not actual purchase dates." if is_sample else "Filter using the order dates in your uploaded data."
)
if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start, end = date_range
else:
    start = end = date_range

available_categories = sorted(products["category"].dropna().unique().tolist())
categories = st.sidebar.multiselect(
    "Product categories", available_categories, help="Choose one or more product types."
)
available_cities = sorted(customers["city"].dropna().unique().tolist())
cities = st.sidebar.multiselect(
    "Customer cities", available_cities, help="Filter orders to customers in selected cities."
)
search_text = st.sidebar.text_input(
    "Find an order or customer", placeholder="e.g. 105 or Ava"
)
st.sidebar.caption("Filters apply to the order, product, and customer views below.")

filtered = orders[orders["sample_order_date"].dt.date.between(start, end)].copy()
if cities:
    city_ids = customers.loc[customers["city"].isin(cities), "customer_id"]
    filtered = filtered[filtered["customer_id"].isin(city_ids)]
filtered_items = order_items[order_items["order_id"].isin(filtered["order_id"])].copy()
if categories:
    category_ids = products.loc[products["category"].isin(categories), "product_id"]
    filtered_items = filtered_items[filtered_items["product_id"].isin(category_ids)]
    filtered = filtered[filtered["order_id"].isin(filtered_items["order_id"])].copy()
    filtered_items = filtered_items[filtered_items["order_id"].isin(filtered["order_id"])]

if search_text.strip():
    term = search_text.strip().lower()
    customer_ids = customers[
        customers["customer_name"].str.lower().str.contains(term, na=False)
        | customers["customer_id"].astype(str).str.contains(term, na=False)
    ]["customer_id"]
    matching_orders = filtered[
        filtered["order_id"].astype(str).str.contains(term, na=False)
        | filtered["customer_id"].isin(customer_ids)
    ]
    filtered = matching_orders
    filtered_items = filtered_items[filtered_items["order_id"].isin(filtered["order_id"])]

revenue = float(filtered["total_amount"].sum())
order_count = len(filtered)
units = int(filtered["total_quantity"].sum())
aov = revenue / order_count if order_count else 0.0
discount_savings = float(
    (filtered["total_amount"] - filtered["discounted_total"]).clip(lower=0).sum()
) if order_count else 0.0

def currency(value: float) -> str:
    return f"${value:,.2f}"

st.subheader("At a glance")
k1, k2, k3, k4 = st.columns(4)
k1.metric(sales_label, currency(revenue), help="Sales total from the selected orders. This is not profit unless costs are included.")
k2.metric("Orders", f"{order_count:,}", help="Number of orders remaining after your filters.")
k3.metric("Units", f"{units:,}", help="Total item quantity across the filtered carts.")
k4.metric("Average order value", currency(aov), help="Sales total divided by filtered order count.")
st.caption(
    f"Showing {order_count:,} of {len(orders):,} orders · "
    f"{len(filtered_items):,} product lines · {start} to {end}"
)

if filtered.empty:
    st.info("No orders match those filters. Try widening the date range or removing a filter.")
    st.stop()

overview_tab, compare_tab, explore_tab, products_tab, customers_tab, orders_tab, guide_tab = st.tabs(
    ["Overview", "Compare", "Explore data", "Products", "Customers", "Orders", "Data guide"]
)

with overview_tab:
    st.subheader("Sales performance")
    st.caption("Weekly sales total for the selected orders." if not is_sample else "Each point is sample order value assigned to a generated week.")
    weekly = (
        filtered.set_index("sample_order_date")["total_amount"]
        .resample("W").sum().rename("sample_sales").reset_index()
    )
    chart = px.line(
        weekly, x="sample_order_date", y="sample_sales", markers=True,
        labels={"sample_order_date": "Week", "sample_sales": "Sales total"},
    )
    st.plotly_chart(chart, use_container_width=True)

    left, right = st.columns([1.15, 0.85], gap="large")
    with left:
        st.subheader("Sales by category")
        category_sales = (
            filtered_items.merge(
                products[["product_id", "category"]], on="product_id", how="left"
            ).groupby("category", as_index=False)
            .agg(sample_sales=("line_total", "sum"), units=("quantity", "sum"))
            .sort_values("sample_sales", ascending=False)
        )
        if not category_sales.empty:
            st.plotly_chart(
                px.bar(category_sales, x="category", y="sample_sales",
                       labels={"category": "Category", "sample_sales": "Sales"},
                       hover_data=["units"]),
                use_container_width=True,
            )
        else:
            st.info("No product lines match the selected filters.")
    with right:
        st.subheader("Top categories")
        st.plotly_chart(px.pie(category_sales, names="category", values="sample_sales", hole=0.55, title="Share of sales by category"), use_container_width=True)


with compare_tab:
    st.subheader("Compare two periods")
    st.caption("Compare sales, order volume, average order value and category mix across two date windows.")
    default_mid = low + (high - low) // 2
    ca, cb = st.columns(2)
    with ca:
        st.markdown("**Period A**")
        range_a = st.date_input("Period A", value=(low, default_mid), min_value=low, max_value=high, key="compare_a")
    with cb:
        st.markdown("**Period B**")
        range_b = st.date_input("Period B", value=(default_mid, high), min_value=low, max_value=high, key="compare_b")
    def slice_period(bounds):
        if isinstance(bounds, (tuple, list)) and len(bounds) == 2:
            return filtered[filtered["sample_order_date"].dt.date.between(bounds[0], bounds[1])]
        return filtered.iloc[0:0]
    pa, pb = slice_period(range_a), slice_period(range_b)
    def summarize_period(frame):
        count = len(frame)
        total = float(frame["total_amount"].sum())
        return {"Sales": total, "Orders": count, "Average order value": total / count if count else 0}
    sa, sb = summarize_period(pa), summarize_period(pb)
    metric_cols = st.columns(3)
    for col, metric in zip(metric_cols, sa):
        change = sb[metric] - sa[metric]
        pct = (change / abs(sa[metric]) * 100) if sa[metric] else None
        shown = currency(sb[metric]) if metric != "Orders" else f"{sb[metric]:,.0f}"
        delta = f"{change:+,.1f} ({pct:+.1f}%)" if pct is not None else f"{change:+,.1f} (no Period A baseline)"
        col.metric(f"{metric} · Period B", shown, delta=delta)
    compare_table = pd.DataFrame([{"Metric": key, "Period A": value, "Period B": sb[key]} for key, value in sa.items()])
    st.dataframe(compare_table, use_container_width=True, hide_index=True)
    if not pa.empty or not pb.empty:
        daily = pd.concat([
            pa.assign(period="Period A"),
            pb.assign(period="Period B")
        ])
        daily["week"] = daily["sample_order_date"].dt.to_period("W").dt.start_time
        period_trend = daily.groupby(["week", "period"], as_index=False)["total_amount"].sum()
        st.plotly_chart(px.line(period_trend, x="week", y="total_amount", color="period", markers=True,
                                title="Weekly sales comparison", labels={"week":"Week","total_amount":"Sales"}), use_container_width=True)
    else:
        st.info("Choose date windows that contain orders to compare them.")
    st.info("Period comparisons reflect the dates and filters in the uploaded data. If the dates are synthetic, the comparison is illustrative only.")

with explore_tab:
    st.subheader("Build your own analysis")
    st.caption("Choose what to group by, which measure to calculate, and how to visualize it. The table and chart respond to your selections.")
    dimension_options = {
        "Product category": ("category", products, "product_id"),
        "Product": ("title", products, "product_id"),
        "Customer city": ("city", customers, "customer_id"),
        "Customer": ("customer_name", customers, "customer_id"),
        "Order month": ("month", None, None),
        "Order weekday": ("weekday", None, None),
    }
    e1, e2, e3 = st.columns(3)
    with e1:
        dimension_label = st.selectbox("Group results by", list(dimension_options), key="explore_dimension")
    with e2:
        measure_label = st.selectbox("Measure", ["Sales", "Orders", "Units", "Average order value"], key="explore_measure")
    with e3:
        chart_style = st.selectbox("Chart style", ["Bar", "Line", "Treemap", "Pie"], key="explore_chart")
    dimension, lookup, join_key = dimension_options[dimension_label]
    if dimension in {"category", "title"}:
        explore_base = filtered_items.merge(products[["product_id", dimension]], on="product_id", how="left")
        explore_base = explore_base.merge(filtered[["order_id", "total_amount"]], on="order_id", how="left")
        group_col = dimension
    elif dimension in {"city", "customer_name"}:
        explore_base = filtered.merge(customers[["customer_id", dimension]], on="customer_id", how="left")
        explore_base = explore_base.merge(order_items.groupby("order_id", as_index=False).agg(units=("quantity","sum")), on="order_id", how="left")
        group_col = dimension
    else:
        explore_base = filtered.copy()
        if dimension == "month":
            explore_base["month"] = explore_base["sample_order_date"].dt.to_period("M").astype(str)
            group_col = "month"
        else:
            explore_base["weekday"] = explore_base["sample_order_date"].dt.day_name()
            group_col = "weekday"
    if measure_label == "Sales":
        value_col, agg_fn = ("line_total", "sum") if dimension in {"category", "title"} else ("total_amount", "sum")
        if dimension in {"city", "customer_name"}:
            value_col = "total_amount"
    elif measure_label == "Orders":
        value_col, agg_fn = "order_id", "nunique"
    elif measure_label == "Units":
        if dimension in {"category", "title"}:
            value_col, agg_fn = "quantity", "sum"
        else:
            if "units" not in explore_base.columns:
                explore_base = explore_base.merge(order_items.groupby("order_id", as_index=False).agg(units=("quantity","sum")), on="order_id", how="left")
            value_col, agg_fn = "units", "sum"
    else:
        value_col, agg_fn = "total_amount", "mean"
    result = explore_base.groupby(group_col, dropna=False).agg(value=(value_col, agg_fn)).reset_index().sort_values("value", ascending=False)
    top_n = st.slider("Number of groups to show", min_value=5, max_value=30, value=min(10, max(5, len(result))), key="explore_top_n")
    result = result.head(top_n)
    if chart_style == "Line":
        fig = px.line(result.sort_values(group_col), x=group_col, y="value", markers=True)
    elif chart_style == "Treemap":
        fig = px.treemap(result, path=[group_col], values="value")
    elif chart_style == "Pie":
        fig = px.pie(result, names=group_col, values="value", hole=0.35)
    else:
        fig = px.bar(result.sort_values("value"), x="value", y=group_col, orientation="h")
    fig.update_layout(title=f"{measure_label} by {dimension_label.lower()}", margin=dict(l=15,r=15,t=55,b=15))
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(result.rename(columns={group_col: dimension_label, "value": measure_label}), use_container_width=True, hide_index=True)
    st.download_button("Download this analysis (CSV)", result.to_csv(index=False).encode("utf-8"), "custom_analysis.csv", "text/csv")

with products_tab:
    st.subheader("Product performance")
    product_summary = (
        filtered_items.groupby("product_id", as_index=False)
        .agg(units_sold=("quantity", "sum"), sample_sales=("line_total", "sum"),
             order_count=("order_id", "nunique"))
        .merge(products, on="product_id", how="left")
        .sort_values("sample_sales", ascending=False)
    )
    if product_summary.empty:
        st.info("No products match the selected filters.")
    else:
        st.markdown("**Top products**")
        st.caption("Ranked by item sales within the selected orders.")
        st.plotly_chart(
            px.bar(
                product_summary.head(10).sort_values("sample_sales"),
                x="sample_sales", y="title", orientation="h",
                labels={"sample_sales": "Sales", "title": "Product"},
                hover_data=["category", "units_sold", "order_count"],
            ),
            use_container_width=True,
        )
        st.markdown("**Stock watch**")
        st.caption("The low-stock flag below means the API's listed stock is 10 units or fewer. It is a demo indicator, not a live alert.")
        stock_watch = products[["title", "category", "stock", "rating", "price"]].copy()
        stock_watch["stock_status"] = stock_watch["stock"].apply(
            lambda value: "Low listed stock" if value <= 10 else "Listed stock above 10"
        )
        stock_watch = stock_watch.sort_values(["stock", "title"])
        st.dataframe(
            stock_watch,
            use_container_width=True,
            hide_index=True,
            column_config={
                "price": st.column_config.NumberColumn("Listed price", format="$%.2f"),
                "rating": st.column_config.NumberColumn("Sample rating", format="%.1f / 5"),
                "stock": st.column_config.NumberColumn("Listed stock", format="%d"),
            },
        )
        st.download_button(
            "Download product summary (CSV)",
            product_summary.to_csv(index=False).encode("utf-8"),
            "product_summary.csv", "text/csv",
        )

with customers_tab:
    st.subheader("Customer performance")
    customer_summary = (
        filtered.groupby("customer_id", as_index=False)
        .agg(order_count=("order_id", "nunique"),
             sample_sales=("total_amount", "sum"),
             units=("total_quantity", "sum"))
        .merge(customers, on="customer_id", how="left")
        .sort_values("sample_sales", ascending=False)
    )
    st.caption("Customer totals reflect only the orders currently selected.")
    st.dataframe(
        customer_summary[["customer_name", "city", "order_count", "units", "sample_sales"]],
        use_container_width=True, hide_index=True,
        column_config={
            "sample_sales": st.column_config.NumberColumn("Sales", format="$%.2f"),
            "order_count": st.column_config.NumberColumn("Orders", format="%d"),
            "units": st.column_config.NumberColumn("Units", format="%d"),
        },
    )
    st.download_button(
        "Download customer summary (CSV)",
        customer_summary.to_csv(index=False).encode("utf-8"),
        "customer_summary.csv", "text/csv",
    )

with orders_tab:
    st.subheader("Find and review orders")
    st.caption("One row represents one order in the selected dataset.")
    display_orders = filtered.sort_values("sample_order_date", ascending=False).copy()
    st.dataframe(
        display_orders,
        use_container_width=True, hide_index=True,
        column_config={
            "total_amount": st.column_config.NumberColumn("Order amount", format="$%.2f"),
            "discounted_total": st.column_config.NumberColumn("Discounted total", format="$%.2f"),
            "sample_order_date": st.column_config.DateColumn("Order date"),
        },
    )
    st.download_button(
        "Download filtered orders (CSV)",
        display_orders.to_csv(index=False).encode("utf-8"),
        "filtered_orders.csv", "text/csv",
    )

with guide_tab:
    st.subheader("Data coverage and metric guide")
    coverage = pd.DataFrame([{"Business area":"Sales","Available":"Orders and order totals","Limit":"Revenue recognition, taxes, payment status and refunds may be absent"},{"Business area":"Products","Available":"Product names, categories, item prices and quantities","Limit":"Cost, margin, supplier and product lifecycle may be absent"},{"Business area":"Customers","Available":"Customer IDs, names and locations when supplied","Limit":"Acquisition channel, consent, demographics and lifetime history may be absent"},{"Business area":"Marketing","Available":"Campaign fields only if uploaded","Limit":"Ad spend, attribution and conversion tracking are not inferred"},{"Business area":"Operations","Available":"Order dates and item quantities","Limit":"Fulfillment, shipping, delivery, returns and service levels need source data"},{"Business area":"Finance","Available":"Sales totals","Limit":"COGS, operating expenses, cash flow and profit cannot be calculated without costs"}])
    st.dataframe(coverage, use_container_width=True, hide_index=True)
    st.markdown("**Metrics and definitions**")
    st.markdown(
        """
        | Term | What it means | What it does not tell you |
        |---|---|---|
        | Sales | Order total or item sales, depending on the selected view | Profit, cash received, or verified revenue |
        | Orders | Number of distinct orders | Number of completed or paid purchases unless status is supplied |
        | Units | Total quantity in the carts | Number of unique products |
        | Average order value | Sales divided by distinct orders | What a real customer typically spends if the source is incomplete |
        | Sales by product | Sum of item line totals for a product | Product profit or margin |
        | Stock | Stock quantity in the source data | Live warehouse availability unless refreshed |
        | Product rating | Rating value from the source | A verified review analysis |
        | Discount difference | Order total minus discounted total when supplied | Actual promotion cost or margin impact |
        """
    )
    st.info(
        "For real business decisions, connect a source with genuine order dates, "
        "payment status, refunds, shipping costs, product costs, and live inventory. "
        "This demo does not contain those fields."
    )

st.divider()
st.caption("Built with Python, DuckDB, pandas, Plotly and Streamlit. Results depend on the completeness and accuracy of the uploaded dataset.")
