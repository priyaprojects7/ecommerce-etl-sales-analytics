# E-Commerce ETL & Sales Analytics

An end-to-end portfolio project that extracts public e-commerce sample data, validates and transforms it with Python, loads analytics tables into DuckDB, and displays sales insights in Streamlit.

**Source limitation:** This first version uses the public DummyJSON API. Its carts are demo records, not a real merchant's historical transactions. The API does not supply genuine purchase dates, so the pipeline creates clearly labelled sample dates only to demonstrate time-series charts.

## Run locally

Requires Python 3.10+.

~~~bash
git clone https://github.com/priyaprojects7/ecommerce-etl-sales-analytics.git
cd ecommerce-etl-sales-analytics
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m src.pipeline
streamlit run app.py
~~~

On Windows PowerShell, activate with .venv\Scripts\Activate.ps1.

## Dashboard features\n\n- Executive overview with sales, order, unit, and average-order metrics\n- Comparison Lab for two date windows and category performance\n- Product Intelligence with product rankings and stock watch\n- Customer Intelligence with customer-level order and sales summaries\n- Sales Trends with weekly history and a basic four-week linear projection when uploaded data contains enough genuine history\n- Business Insights calculated from the selected data\n- Order Explorer with filters and CSV exports\n- Data Quality checks for missing cells and duplicate rows\n- Upload your own data using the downloadable Excel template or four CSV files\n\nThe Excel workbook must contain `orders`, `order_items`, `products`, and `customers` sheets. The `orders` sheet accepts `order_date` (recommended) or `sample_order_date`. Uploaded files stay in the current Streamlit session. Forecasts are disabled for the built-in demo data because its dates are generated.\n\n## Pipeline

1. Extract products, users, and carts with API pagination.
2. Preserve raw JSON responses.
3. Normalize carts into orders and order items.
4. Validate keys, quantities, prices, and relationships.
5. Load tables and reporting views into DuckDB.
6. Explore sales, products, and customers in Streamlit.

## Data model

- products: product attributes and current sample prices
- customers: customer identity and city
- orders: one row per sample cart
- order_items: one row per product line
- daily_sales, product_performance, customer_performance: reporting views

## Tests

~~~bash
pytest -q
ruff check .
~~~

Generated files in data/raw and data/warehouse are excluded from Git. The next project iteration can add a historical retail dataset, dbt models, richer data-quality reporting, Docker, and deployment.
