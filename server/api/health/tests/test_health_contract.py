# coding: utf-8
# @File        : test_health_contract.py
# @Author      : NanMing
# @Date        : 2026/6/11 13:33
# @Description : Tests health check API contract behavior.

def test_health_contract_uses_stable_response_shape(client, monkeypatch):
    from api.health import service as health

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

    class FakeRedis:
        def __init__(self, *args, **kwargs):
            pass

        def ping(self):
            return True

    monkeypatch.setattr(health, "create_mongo_client", FakeMongoClient)
    monkeypatch.setattr(health, "Redis", FakeRedis)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.get_json()
    assert set(body) == {"data"}
    assert body["data"] == {
        "api": {"ok": True, "message": "ok"},
        "mongodb": {"ok": True, "message": "ping ok"},
        "redis": {"ok": True, "message": "ping ok"},
    }


def test_legacy_health_route_is_not_registered(client):
    assert client.get("/api/health").status_code == 404
