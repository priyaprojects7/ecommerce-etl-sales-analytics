import pytest

from src.transform import transform_payloads


def test_transform_creates_expected_tables(sample_payloads):
    tables = transform_payloads(sample_payloads)
    assert set(tables) == {"products", "customers", "orders", "order_items"}
    assert tables["orders"].iloc[0]["total_amount"] == 10.0
    assert tables["order_items"].iloc[0]["quantity"] == 2
    assert tables["customers"].iloc[0]["city"] == "Boston"


def test_transform_rejects_unknown_product(sample_payloads):
    sample_payloads["carts"]["carts"][0]["products"][0]["id"] = 999
    with pytest.raises(ValueError, match="unknown product"):
        transform_payloads(sample_payloads)


def test_transform_rejects_zero_quantity(sample_payloads):
    sample_payloads["carts"]["carts"][0]["products"][0]["quantity"] = 0
    with pytest.raises(ValueError, match="quantities must be positive"):
        transform_payloads(sample_payloads)
