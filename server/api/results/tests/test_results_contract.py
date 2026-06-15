# coding: utf-8
# @File        : test_results_contract.py
# @Author      : NanMing
# @Date        : 2026/6/11 11:43
# @Description : Tests results listing API contract behavior.

import json


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


def test_leakage_list_contract_preserves_status_filter_and_pagination(client, monkeypatch):
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
        "/api/leakage",
        query_string={
            "status": json.dumps({"security": 0, "ignore": 0}),
            "tag": "github-token",
            "language": "Python",
            "limit": "2",
            "from": "3",
        },
    )

    assert response.status_code == 200
    body = response.get_json()
    assert list(body) == ["status", "msg", "result", "total"]
    assert body == {
        "status": 200,
        "msg": "共 42 条记录",
        "result": [
            {
                "_id": "leak-1",
                "project": "org/repo",
                "tag": "github-token",
                "language": "Python",
                "security": 0,
                "ignore": 0,
            }
        ],
        "total": 42,
    }
    assert captured["create_indexes"] == 1
    assert captured["filters"] == {
        "security": 0,
        "ignore": 0,
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


def test_leakage_list_contract_returns_empty_message_when_no_records(client, monkeypatch):
    from api.results import repository as result

    class FakeResultCollection:
        def find(self, filters, projection):
            return FakeCursor([])

        def count_documents(self, filters):
            return 0

    monkeypatch.setattr(result, "result_col", FakeResultCollection())
    monkeypatch.setattr(result, "create_indexes", lambda: None)

    response = client.get(
        "/api/leakage",
        query_string={"status": json.dumps({"security": 1, "ignore": 1})},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert list(body) == ["status", "msg", "result", "total"]
    assert body == {
        "status": 200,
        "msg": "暂无数据",
        "result": [],
        "total": 0,
    }


def test_leakage_info_contract_uses_stable_projection(client, monkeypatch):
    from api.results import repository as result

    captured = {}

    class FakeResultCollection:
        def find_one(self, filters, projection):
            captured["filters"] = filters
            captured["projection"] = projection
            return {"project": "org/repo", "tag": "github-token", "security": 0}

    monkeypatch.setattr(result, "result_col", FakeResultCollection())

    response = client.get("/api/leakage/info?id=leak-1")

    assert response.status_code == 200
    assert response.get_json() == {
        "status": 200,
        "msg": "获取信息成功",
        "result": {"project": "org/repo", "tag": "github-token", "security": 0},
    }
    assert captured == {
        "filters": {"_id": "leak-1"},
        "projection": {"_id": 0, "code": 0},
    }


def test_leakage_code_contract_uses_stable_projection(client, monkeypatch):
    from api.results import repository as result

    captured = {}

    class FakeResultCollection:
        def find_one(self, filters, projection):
            captured["filters"] = filters
            captured["projection"] = projection
            return {"code": "token = 'redacted'", "affect": ["config.py"]}

    monkeypatch.setattr(result, "result_col", FakeResultCollection())

    response = client.get("/api/leakage/code?id=leak-1")

    assert response.status_code == 200
    assert response.get_json() == {
        "status": 200,
        "msg": "获取信息成功",
        "result": {"code": "token = 'redacted'", "affect": ["config.py"]},
    }
    assert captured == {
        "filters": {"_id": "leak-1"},
        "projection": {"_id": 0, "code": 1, "affect": 1},
    }
