# coding: utf-8
# @File        : test_health_contract.py
# @Author      : NanMing
# @Date        : 2026/6/11 13:33
# @Description : Tests health check API contract behavior.

def test_health_contract_uses_stable_response_shape(client, monkeypatch):
    from api.health import service as health

    class FakeResponse:
        ok = True
        status_code = 200
        text = "https://api.github.com/"

    class FakeDatabase:
        def command(self, command):
            assert command == "ping"
            return {"ok": 1}

    class FakeMongoClient:
        def __init__(self, *args, **kwargs):
            pass

        def get_database(self, name):
            assert name == "skyradar"
            return FakeDatabase()

    monkeypatch.setattr(health.requests, "get", lambda *args, **kwargs: FakeResponse())
    monkeypatch.setattr(health, "create_mongo_client", FakeMongoClient)

    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.get_json()
    assert set(body) == {"github", "mongodb"}
    assert body["github"] is True
    assert body["mongodb"] == {"ok": 1}
