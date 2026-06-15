# coding: utf-8
# @File        : test_results_contract.py
# @Author      : NanMing
# @Date        : 2026/6/11 11:43
# @Description : Tests results listing API contract behavior.


class FakeCursor:
    def __init__(self, documents):
        self.documents = documents
        self.calls = []

    def sort(self, field, direction):
        self.calls.append(("sort", field, direction))
        return self

    def limit(self, value):
        self.calls.append(("limit", value))
        return self

    def skip(self, value):
        self.calls.append(("skip", value))
        return self

    def __iter__(self):
        return iter(self.documents)


def test_leakage_results_list_uses_rest_filters_and_pagination(client, monkeypatch):
    from api.results import repository as result

    captured = {"create_indexes": 0}
    cursor = FakeCursor(
        [
            {
                "_id": "leak-1",
                "project": "org/repo",
                "tag": "github-token",
                "language": "Python",
                "security": 0,
                "ignore": 0,
            }
        ]
    )

    class FakeResultCollection:
        def find(self, filters, projection):
            captured["filters"] = filters
            captured["projection"] = projection
            return cursor

        def count_documents(self, filters):
            captured["count_filters"] = filters
            return 42

    def fake_create_indexes():
        captured["create_indexes"] += 1

    monkeypatch.setattr(result, "result_col", FakeResultCollection())
    monkeypatch.setattr(result, "create_indexes", fake_create_indexes)

    response = client.get(
        "/api/v1/leakages",
        query_string={
            "security": "0",
            "ignored": "false",
            "reviewed": "true",
            "tag": "github-token",
            "language": "Python",
            "page_size": "2",
            "page": "3",
        },
    )

    assert response.status_code == 200
    body = response.get_json()
    assert list(body) == ["data", "meta"]
    assert body == {
        "data": [
            {
                "_id": "leak-1",
                "project": "org/repo",
                "tag": "github-token",
                "language": "Python",
                "security": 0,
                "ignore": 0,
            }
        ],
        "meta": {"total": 42, "page": 3, "page_size": 2},
    }
    assert captured["create_indexes"] == 1
    assert captured["filters"] == {
        "security": 0,
        "ignore": 0,
        "desc": {"$exists": True},
        "tag": "github-token",
        "language": "Python",
    }
    assert captured["count_filters"] == captured["filters"]
    assert captured["projection"] == {"code": 0, "affect": 0}
    assert cursor.calls == [
        ("sort", "datetime", result.DESCENDING),
        ("limit", 2),
        ("skip", 4),
    ]


def test_leakage_results_list_returns_empty_rest_collection(client, monkeypatch):
    from api.results import repository as result

    class FakeResultCollection:
        def find(self, filters, projection):
            return FakeCursor([])

        def count_documents(self, filters):
            return 0

    monkeypatch.setattr(result, "result_col", FakeResultCollection())
    monkeypatch.setattr(result, "create_indexes", lambda: None)

    response = client.get("/api/v1/leakages", query_string={"ignored": "true"})

    assert response.status_code == 200
    assert response.get_json() == {
        "data": [],
        "meta": {"total": 0, "page": 1, "page_size": 20},
    }


def test_leakage_result_detail_uses_rest_path_and_projection(client, monkeypatch):
    from api.results import repository as result

    captured = {}

    class FakeResultCollection:
        def find_one(self, filters, projection):
            captured["filters"] = filters
            captured["projection"] = projection
            return {"project": "org/repo", "tag": "github-token", "security": 0}

    monkeypatch.setattr(result, "result_col", FakeResultCollection())

    response = client.get("/api/v1/leakages/leak-1")

    assert response.status_code == 200
    assert response.get_json() == {
        "data": {"project": "org/repo", "tag": "github-token", "security": 0},
    }
    assert captured == {
        "filters": {"_id": "leak-1"},
        "projection": {"_id": 0, "code": 0},
    }


def test_leakage_result_code_uses_rest_path_and_projection(client, monkeypatch):
    from api.results import repository as result

    captured = {}

    class FakeResultCollection:
        def find_one(self, filters, projection):
            captured["filters"] = filters
            captured["projection"] = projection
            return {"code": "token = 'redacted'", "affect": ["config.py"]}

    monkeypatch.setattr(result, "result_col", FakeResultCollection())

    response = client.get("/api/v1/leakages/leak-1/code")

    assert response.status_code == 200
    assert response.get_json() == {
        "data": {"code": "token = 'redacted'", "affect": ["config.py"]},
    }
    assert captured == {
        "filters": {"_id": "leak-1"},
        "projection": {"_id": 0, "code": 1, "affect": 1},
    }


def test_leakage_result_detail_returns_rest_404(client, monkeypatch):
    from api.results import repository as result

    class FakeResultCollection:
        def find_one(self, filters, projection):
            return None

    monkeypatch.setattr(result, "result_col", FakeResultCollection())

    response = client.get("/api/v1/leakages/missing")

    assert response.status_code == 404
    assert response.get_json() == {
        "error": "leakage_result_not_found",
        "message": "Leakage result not found",
        "detail": {"id": "missing"},
    }


def test_legacy_leakage_routes_are_not_registered(client):
    assert client.get("/api/leakage").status_code == 404
    assert client.get("/api/leakage/info?id=leak-1").status_code == 404
    assert client.get("/api/leakage/code?id=leak-1").status_code == 404
