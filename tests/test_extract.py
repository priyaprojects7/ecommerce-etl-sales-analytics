from src.extract import fetch_resource


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self):
        self.calls = 0

    def get(self, url, params, timeout):
        self.calls += 1
        if params["skip"] == 0:
            return FakeResponse({"products": [{"id": 1}], "total": 2})
        return FakeResponse({"products": [{"id": 2}], "total": 2})


def test_fetch_resource_follows_pagination():
    session = FakeSession()
    result = fetch_resource("products", base_url="https://example.test", session=session)
    assert [row["id"] for row in result["products"]] == [1, 2]
    assert session.calls == 2
