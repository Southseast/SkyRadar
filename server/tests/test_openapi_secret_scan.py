# coding: utf-8
# @File        : test_openapi_secret_scan.py
# @Author      : NanMing
# @Date        : 2026/6/11 16:44
# @Description : Tests OpenAPI secret scan command behavior.

import importlib.util
import subprocess
import sys
from pathlib import Path

import yaml


SCRIPT_PATH = Path("scripts/backend_openapi_secret_scan.py")
OPENAPI_PATH = Path("docs/api/openapi.yaml")


def _load_scan_module():
    spec = importlib.util.spec_from_file_location("backend_openapi_secret_scan", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _minimal_schema(value):
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "Secret Scan Test",
            "version": "1",
            "description": value if isinstance(value, str) else "ok",
        },
        "paths": {
            "/api/example": {
                "post": {
                    "operationId": "postExample",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"type": "object"},
                                "example": value,
                            }
                        }
                    },
                    "responses": {"200": {"description": "ok"}},
                }
            }
        },
        "components": {"schemas": {"Example": {"type": "object"}}},
    }


def test_real_openapi_has_no_secret_findings():
    scan = _load_scan_module()
    schema = scan.load_openapi(OPENAPI_PATH)

    assert scan.scan_openapi(schema) == []


def test_placeholder_values_are_ignored():
    scan = _load_scan_module()
    schema = _minimal_schema(
        {
            "site": "https://example.com",
            "mail": "test@example.com",
            "github_token": "ghp_example_token_do_not_use",
            "password": "example-password",
            "webhook": "https://oapi.dingtalk.com/robot/send?access_token=example",
            "secret": "SEC-example",
            "redacted": "REDACTED",
            "masked": "***",
            "dummy": "dummy-token",
            "fake": "fake-secret",
        }
    )

    assert scan.scan_openapi(schema) == []


def test_detects_github_pat_and_classic_token():
    scan = _load_scan_module()
    schema = _minimal_schema(
        {
            "classic": "ghp_" + ("A" * 36),
            "fine_grained": "github_pat_" + ("B" * 30),
        }
    )

    findings = scan.scan_openapi(schema)

    assert [finding.rule for finding in findings] == ["github-token", "github-token"]
    assert all("github-token" in finding.rule for finding in findings)


def test_detects_smtp_password_and_webhook_secret_material():
    scan = _load_scan_module()
    schema = _minimal_schema(
        {
            "password": "smtp-prod-password-123",
            "webhook": "https://oapi.dingtalk.com/robot/send?access_token=" + ("C" * 32),
            "secret": "SEC" + ("D" * 40),
        }
    )

    findings = scan.scan_openapi(schema)
    rules = {finding.rule for finding in findings}

    assert "sensitive-field:password" in rules
    assert "webhook-access-token" in rules
    assert "webhook-secret" in rules
    assert "sensitive-field:secret" in rules


def test_detects_mongodb_and_redis_uri_credentials():
    scan = _load_scan_module()
    schema = _minimal_schema(
        {
            "mongo_uri": "mongodb://skyradar:ProdMongoPass123@mongo:27017/skyradar",
            "redis_url": "redis://:ProdRedisPass123@redis:6379/0",
        }
    )

    findings = scan.scan_openapi(schema)
    rules = {finding.rule for finding in findings}

    assert "mongodb-uri-credential" in rules
    assert "redis-uri-credential" in rules
    assert "sensitive-field:mongo_uri" in rules
    assert "sensitive-field:redis_url" in rules


def test_cli_failure_lists_paths(tmp_path):
    openapi_path = tmp_path / "openapi.yaml"
    schema = _minimal_schema({"password": "smtp-prod-password-123"})
    openapi_path.write_text(yaml.safe_dump(schema), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--openapi", str(openapi_path)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "backend-openapi-secret-scan: failed" in result.stderr
    assert "$.paths./api/example.post.requestBody.content.application/json.example.password" in result.stderr
    assert "sensitive-field:password" in result.stderr
