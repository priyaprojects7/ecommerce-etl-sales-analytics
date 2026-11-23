import pytest


@pytest.fixture
def sample_payloads():
    return {
        "products": {"products": [
            {"id": 1, "title": "Notebook", "category": "stationery",
             "brand": "PaperCo", "price": 5.0, "rating": 4.5, "stock": 20}
        ]},
        "users": {"users": [
            {"id": 7, "firstName": "Ava", "lastName": "Lee",
             "email": "ava@example.com", "address": {"city": "Boston"}}
        ]},
        "carts": {"carts": [
            {"id": 3, "userId": 7, "total": 10.0, "discountedTotal": 9.0,
             "products": [{"id": 1, "quantity": 2, "price": 5.0,
                           "discountPercentage": 10}]}
        ]},
    }
