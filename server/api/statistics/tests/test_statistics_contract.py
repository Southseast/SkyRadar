# coding: utf-8
# @File        : test_statistics_contract.py
# @Author      : NanMing
# @Date        : 2026/6/8 14:23
# @Description : Tests statistics API contract behavior.

def test_statistic_contract_uses_collection_aggregate(client, monkeypatch):
    from api.statistics import repository as statistic

    captured = {}

    class FakeResultCollection:
        def aggregate(self, pipeline):
            captured["pipeline"] = pipeline
            return [{"_id": "github-token", "value": 2}]

    monkeypatch.setattr(statistic, "result_col", FakeResultCollection())

    response = client.get("/api/statistic?by=tag&tag=")

    assert response.status_code == 200
    body = response.get_json()
    assert body == {
        "status": 200,
        "msg": "获取信息成功",
        "result": [{"_id": "github-token", "value": 2}],
    }
    assert captured["pipeline"] == [
        {"$match": {"security": 0}},
        {"$group": {"_id": "$tag", "value": {"$sum": 1}}},
    ]
