# coding: utf-8
# @File        : test_api_docs.py
# @Author      : NanMing
# @Date        : 2026/6/10 16:05
# @Description : Tests API documentation route availability.

def test_api_docs_disabled_by_default(client, monkeypatch):
    monkeypatch.delenv("SKYRADAR_API_DOCS_ENABLED", raising=False)

    response = client.get("/api/v1/openapi.json")

    assert response.status_code == 404
    assert response.get_json() == {
        "error": "api_docs_disabled",
        "message": "API docs disabled",
    }


def test_openapi_json_can_be_enabled(client, monkeypatch):
    monkeypatch.setenv("SKYRADAR_API_DOCS_ENABLED", "true")

    response = client.get("/api/v1/openapi.json")

    assert response.status_code == 200
    body = response.get_json()
    assert body["openapi"].startswith("3.")
    assert "/api/v1/health" in body["paths"]


def test_openapi_contract_matches_runtime_field_names(client, monkeypatch):
    monkeypatch.setenv("SKYRADAR_API_DOCS_ENABLED", "true")

    response = client.get("/api/v1/openapi.json")

    assert response.status_code == 200
    body = response.get_json()
    health_schema = body["components"]["schemas"]["Health"]
    statistic_params = body["paths"]["/api/v1/statistics"]["get"]["parameters"]
    trend_counter = body["components"]["schemas"]["TrendCounter"]
    engine = body["components"]["schemas"]["Engine"]
    webhook_request = body["components"]["schemas"]["WebhookRequest"]
    error_detail = body["components"]["schemas"]["ErrorResponse"]["properties"]["detail"]

    assert "github" not in health_schema["required"]
    assert "github" not in health_schema["properties"]
    assert [param["name"] for param in statistic_params] == ["by", "tag"]
    assert set(trend_counter["required"]) == {"total", "ignore", "risk"}
    assert set(engine["required"]) == {"status", "last"}
    assert "secret" in webhook_request["required"]
    assert [schema["type"] for schema in error_detail["oneOf"]] == ["object", "array", "string"]


def test_swagger_docs_can_be_enabled(client, monkeypatch):
    monkeypatch.setenv("SKYRADAR_API_DOCS_ENABLED", "true")

    response = client.get("/api/v1/docs")

    assert response.status_code == 200
    assert response.mimetype == "text/html"
    assert b"SwaggerUIBundle" in response.data
    assert b"/api/v1/openapi.json" in response.data


def test_legacy_api_docs_routes_are_not_registered(client):
    assert client.get("/api/openapi.json").status_code == 404
    assert client.get("/api/docs").status_code == 404
