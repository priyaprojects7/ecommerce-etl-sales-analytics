"""Normalize and validate source payloads into analytics tables."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd


def _require_unique(frame: pd.DataFrame, column: str, table: str) -> None:
    if frame[column].isna().any() or frame[column].duplicated().any():
        raise ValueError(f"{table}.{column} must be non-null and unique")


def validate_tables(products: pd.DataFrame, customers: pd.DataFrame,
                    orders: pd.DataFrame, items: pd.DataFrame) -> None:
    _require_unique(products, "product_id", "products")
    _require_unique(customers, "customer_id", "customers")
    _require_unique(orders, "order_id", "orders")
    if (products["price"] < 0).any():
        raise ValueError("Product prices cannot be negative")
    if (items[["quantity", "unit_price"]] < 0).any().any():
        raise ValueError("Order item quantities and prices cannot be negative")
    if (items["quantity"] == 0).any():
        raise ValueError("Order item quantities must be positive")
    if not set(items["product_id"]).issubset(set(products["product_id"])):
        raise ValueError("Order items contain unknown product IDs")
    if not set(orders["customer_id"]).issubset(set(customers["customer_id"])):
        raise ValueError("Orders contain unknown customer IDs")
    if not set(items["order_id"]).issubset(set(orders["order_id"])):
        raise ValueError("Order items contain unknown order IDs")


def transform_payloads(payloads: dict[str, dict[str, Any]]) -> dict[str, pd.DataFrame]:
    products = pd.DataFrame(payloads["products"]["products"])
    users = pd.DataFrame(payloads["users"]["users"])
    product_rows = products[
        ["id", "title", "category", "brand", "price", "rating", "stock"]
    ].copy().rename(columns={"id": "product_id"})
    product_rows["brand"] = product_rows["brand"].fillna("Unknown")
    product_rows["category"] = product_rows["category"].fillna("Uncategorized")

    customer_rows = users[["id", "firstName", "lastName", "email", "address"]].copy()
    customer_rows["customer_id"] = customer_rows["id"]
    customer_rows["customer_name"] = (
        customer_rows["firstName"].fillna("").str.strip()
        + " " + customer_rows["lastName"].fillna("").str.strip()
    ).str.strip()
    customer_rows["city"] = customer_rows["address"].apply(
        lambda value: value.get("city") if isinstance(value, dict) else None
    )
    customer_rows = customer_rows[["customer_id", "customer_name", "email", "city"]]

    order_rows, item_rows = [], []
    for cart in payloads["carts"]["carts"]:
        cart_id = int(cart["id"])
        lines = cart.get("products", [])
        # The API has no purchase timestamp. This generated date is explicitly
        # synthetic and is only used to demonstrate time-series reporting.
        sample_date = date(2024, 1, 1) + timedelta(days=cart_id % 365)
        total = sum(float(line["price"]) * int(line["quantity"]) for line in lines)
        order_rows.append({
            "order_id": cart_id, "customer_id": int(cart["userId"]),
            "sample_order_date": sample_date,
            "total_quantity": sum(int(line["quantity"]) for line in lines),
            "total_amount": round(total, 2),
            "source_reported_total": float(cart.get("total", total)),
            "discounted_total": float(cart.get("discountedTotal", total)),
        })
        for line in lines:
            item_rows.append({
                "order_id": cart_id, "product_id": int(line["id"]),
                "quantity": int(line["quantity"]), "unit_price": float(line["price"]),
                "line_total": round(float(line["price"]) * int(line["quantity"]), 2),
                "discount_percentage": float(line.get("discountPercentage", 0)),
            })

    orders = pd.DataFrame(order_rows)
    items = pd.DataFrame(item_rows)
    validate_tables(product_rows, customer_rows, orders, items)
    return {"products": product_rows, "customers": customer_rows,
            "orders": orders, "order_items": items}
