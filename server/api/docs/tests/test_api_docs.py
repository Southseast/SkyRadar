# coding: utf-8
# @File        : test_api_docs.py
# @Author      : NanMing
# @Date        : 2026/6/10 16:05
# @Description : Tests API documentation route availability.

def test_api_docs_disabled_by_default(client, monkeypatch):
    monkeypatch.delenv("SKYRADAR_API_DOCS_ENABLED", raising=False)

    response = client.get("/api/openapi.json")

    assert response.status_code == 404
    assert response.get_json() == {
        "status": 404,
        "msg": "API docs disabled",
        "result": [],
    }


def test_openapi_json_can_be_enabled(client, monkeypatch):
    monkeypatch.setenv("SKYRADAR_API_DOCS_ENABLED", "true")

    response = client.get("/api/openapi.json")

    assert response.status_code == 200
    body = response.get_json()
    assert body["openapi"].startswith("3.")
    assert "/api/health" in body["paths"]


def test_swagger_docs_can_be_enabled(client, monkeypatch):
    monkeypatch.setenv("SKYRADAR_API_DOCS_ENABLED", "true")

    response = client.get("/api/docs")

    assert response.status_code == 200
    assert response.mimetype == "text/html"
    assert b"SwaggerUIBundle" in response.data
    assert b"/api/openapi.json" in response.data
