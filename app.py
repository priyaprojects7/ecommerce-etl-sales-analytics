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

st.write(
    "A simple workspace for exploring orders, products, customers, and stock. "
    "You do not need SQL or data-analysis experience to use it."
)

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
        - **Sample gross sales:** the sum of item price × quantity before the
          cart-level discounted total is applied. It is not profit.
        - **Orders:** the number of sample carts in the current filters.
        - **Units sold:** the total quantity of items across those carts.
        - **Average order value:** sample gross sales divided by the number of carts.
        - **Product rating:** the rating supplied by the sample product API.
        - **Listed stock:** the stock number supplied by the sample product API;
          it is not a live inventory feed.
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
    "Sample date range", value=(low, high), min_value=low, max_value=high,
    help="These dates are generated for demonstration; they are not actual purchase dates."
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

overview_tab, products_tab, customers_tab, orders_tab, guide_tab = st.tabs(
    ["Overview", "Products & stock", "Customers", "Orders", "Metric guide"]
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

    left, right = st.columns(2)
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
                       labels={"category": "Category", "sample_sales": "Sample sales"},
                       hover_data=["units"]),
                use_container_width=True,
            )
        else:
            st.info("No product lines match the selected filters.")
    with right:
        st.subheader("Order discount summary")
        st.metric("Difference before and after cart discount", currency(discount_savings))
        st.caption(
            "This is the sum of sample cart totals minus sample discounted totals. "
            "It is not a measure of profit or a verified promotion cost."
        )

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
                labels={"sample_sales": "Sample sales", "title": "Product"},
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
            "sample_sales": st.column_config.NumberColumn("Sample sales", format="$%.2f"),
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
            "total_amount": st.column_config.NumberColumn("Sample order amount", format="$%.2f"),
            "discounted_total": st.column_config.NumberColumn("Sample discounted total", format="$%.2f"),
            "sample_order_date": st.column_config.DateColumn("Generated sample date"),
        },
    )
    st.download_button(
        "Download filtered orders (CSV)",
        display_orders.to_csv(index=False).encode("utf-8"),
        "sample_orders.csv", "text/csv",
    )

with guide_tab:
    st.subheader("Metric guide")
    st.markdown(
        """
        | Term | What it means | What it does not tell you |
        |---|---|---|
        | Sample gross sales | Sum of item prices multiplied by quantities | Profit, cash received, or verified revenue |
        | Orders | Number of sample carts | Number of completed or paid purchases |
        | Units | Total quantity in the carts | Number of unique products |
        | Average order | Sample gross sales divided by cart count | What a real customer typically spends |
        | Sample sales by product | Sum of item line totals for a product | Product profit or margin |
        | Listed stock | Stock value in the sample product feed | Live warehouse availability |
        | Product rating | Rating value from the sample API | A verified review analysis |
        | Discount difference | Cart total minus discounted cart total | Actual promotion cost or margin impact |
        """
    )
    st.info(
        "For real business decisions, connect a source with genuine order dates, "
        "payment status, refunds, shipping costs, product costs, and live inventory. "
        "This demo does not contain those fields."
    )

st.divider()
st.caption(
    "Built as a learning and portfolio demo using DummyJSON sample data. "
    "The generated dates and sample values should not be treated as real company performance."
)
