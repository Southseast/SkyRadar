# coding: utf-8
# @File        : test_statistics_contract.py
# @Author      : NanMing
# @Date        : 2026/6/8 14:23
# @Description : Tests statistics API contract behavior.


def test_statistics_breakdowns_uses_rest_path_and_collection_aggregate(client, monkeypatch):
    from api.statistics import repository as statistic

    captured = {}

    class FakeResultCollection:
        def aggregate(self, pipeline):
            captured["pipeline"] = pipeline
            return [{"_id": "github-token", "value": 2}]

    monkeypatch.setattr(statistic, "result_col", FakeResultCollection())

    response = client.get("/api/v1/statistics?by=tag&tag=")

    assert response.status_code == 200
    body = response.get_json()
    assert body == {"data": [{"_id": "github-token", "value": 2}]}
    assert captured["pipeline"] == [
        {"$match": {"security": 0}},
        {"$group": {"_id": "$tag", "value": {"$sum": 1}}},
    ]


def test_statistics_breakdowns_filters_by_tag(client, monkeypatch):
    from api.statistics import repository as statistic

    captured = {}

    class FakeResultCollection:
        def aggregate(self, pipeline):
            captured["pipeline"] = pipeline
            return [{"_id": "Python", "value": 1}]

    monkeypatch.setattr(statistic, "result_col", FakeResultCollection())

    response = client.get("/api/v1/statistics?by=language&tag=github-token")

    assert response.status_code == 200
    assert response.get_json() == {"data": [{"_id": "Python", "value": 1}]}
    assert captured["pipeline"] == [
        {"$match": {"tag": "github-token", "security": 0}},
        {"$group": {"_id": "$language", "value": {"$sum": 1}}},
    ]


def test_statistics_breakdowns_rejects_unknown_field(client):
    response = client.get("/api/v1/statistics?by=$where")

    assert response.status_code == 422
    body = response.get_json()
    assert body["error"] == "invalid_breakdown"
    assert body["message"] == "Unsupported breakdown field"


def test_statistics_summary_uses_rest_envelope(client, monkeypatch):
    from api.statistics import repository as statistic
    from api.statistics import service as statistics_service

    captured = []

    class FakeResultCollection:
        def count_documents(self, filters):
            captured.append(filters)
            return 7

    class FakeSettingCollection:
        def count_documents(self, filters):
            return 0

    monkeypatch.setattr(statistic, "result_col", FakeResultCollection())
    monkeypatch.setattr(statistic, "setting_col", FakeSettingCollection())
    monkeypatch.setattr(statistics_service.psutil, "pid_exists", lambda pid: False)

    response = client.get("/api/v1/trends")

    assert response.status_code == 200
    assert response.get_json()["data"]["engine"] == {"status": False, "last": 0}
    assert {"security": 1} in captured
    assert {"security": 0, "desc": {"$exists": True}} in captured


def test_legacy_statistics_routes_are_not_registered(client):
    assert client.get("/api/trend").status_code == 404
    assert client.get("/api/statistic?by=tag").status_code == 404
