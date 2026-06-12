# coding: utf-8
# @File        : test_schemathesis_smoke.py
# @Author      : NanMing
# @Date        : 2026/6/10 18:57
# @Description : Tests Schemathesis smoke command behavior.

import importlib.util
import subprocess
import sys
from pathlib import Path

import yaml


SCRIPT_PATH = Path("scripts/backend_schemathesis_smoke.py")
OPENAPI_PATH = Path("docs/api/openapi.yaml")
WRITE_METHODS = {"post", "put", "patch", "delete"}


def _load_smoke_module():
    spec = importlib.util.spec_from_file_location("backend_schemathesis_smoke", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_read_only_filter_removes_write_operations():
    smoke = _load_smoke_module()
    schema = {
        "openapi": "3.0.3",
        "info": {"title": "Example", "version": "1"},
        "paths": {
            "/api/a": {
                "parameters": [{"name": "token", "in": "query", "schema": {"type": "string"}}],
                "get": {"operationId": "getA", "responses": {"200": {"description": "ok"}}},
                "post": {"operationId": "postA", "responses": {"200": {"description": "ok"}}},
            },
            "/api/b": {
                "patch": {"operationId": "patchB", "responses": {"200": {"description": "ok"}}},
            },
            "/api/c": {
                "get": {"operationId": "getC", "responses": {"200": {"description": "ok"}}},
                "delete": {"operationId": "deleteC", "responses": {"200": {"description": "ok"}}},
            },
        },
        "components": {"schemas": {"Example": {"type": "object"}}},
    }

    filtered, operations = smoke.filter_read_only_get_schema(schema)

    assert operations == ["GET /api/a", "GET /api/c"]
    assert set(filtered["paths"]) == {"/api/a", "/api/c"}
    assert "get" in filtered["paths"]["/api/a"]
    assert "parameters" in filtered["paths"]["/api/a"]
    assert WRITE_METHODS.isdisjoint(filtered["paths"]["/api/a"])
    assert WRITE_METHODS.isdisjoint(filtered["paths"]["/api/c"])


def test_real_openapi_filter_contains_only_get_operations():
    smoke = _load_smoke_module()
    schema = smoke.load_openapi(OPENAPI_PATH)

    filtered, operations = smoke.filter_read_only_get_schema(schema)

    assert operations
    for path_item in filtered["paths"].values():
        methods = set(path_item) & smoke.HTTP_METHODS
        assert methods == {"get"}
    leakage_status = filtered["components"]["parameters"]["LeakageStatusQuery"]
    assert leakage_status["schema"] == {
        "type": "string",
        "enum": [smoke.LEAKAGE_STATUS_SMOKE_VALUE],
    }
    assert leakage_status["example"] == smoke.LEAKAGE_STATUS_SMOKE_VALUE
    leakage_parameters = filtered["paths"]["/api/leakage"]["get"]["parameters"]
    assert leakage_parameters[0]["name"] == "status"
    assert "$ref" not in leakage_parameters[0]
    assert leakage_parameters[0]["schema"]["enum"] == [smoke.LEAKAGE_STATUS_SMOKE_VALUE]


def test_dry_run_does_not_require_running_service_or_schemathesis_cli(tmp_path):
    schema = {
        "openapi": "3.0.3",
        "info": {"title": "Dry Run", "version": "1"},
        "paths": {
            "/api/health": {
                "get": {
                    "operationId": "getHealth",
                    "responses": {"200": {"description": "ok"}},
                },
                "delete": {
                    "operationId": "deleteHealth",
                    "responses": {"200": {"description": "ok"}},
                },
            }
        },
        "components": {"schemas": {}},
    }
    openapi_path = tmp_path / "openapi.yaml"
    openapi_path.write_text(yaml.safe_dump(schema), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--openapi",
            str(openapi_path),
            "--base-url",
            "http://127.0.0.1:9999",
            "--dry-run",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "dry-run ok (1 GET operations)" in result.stdout
    assert "--phases=fuzzing" in result.stdout
    assert "--mode=positive" in result.stdout
    assert "--max-examples=1" in result.stdout
    assert "GET /api/health" in result.stdout
    assert "DELETE" not in result.stdout
