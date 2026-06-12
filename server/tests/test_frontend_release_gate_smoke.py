# coding: utf-8
# @File        : test_frontend_release_gate_smoke.py
# @Author      : NanMing
# @Date        : 2026/6/10 12:38
# @Description : Tests frontend release gate smoke command behavior.

import importlib.util
import json
from pathlib import Path


SMOKE_SCRIPT = Path("scripts/frontend_release_gate_smoke.py")


def load_smoke_module():
    spec = importlib.util.spec_from_file_location("frontend_release_gate_smoke", SMOKE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_release_gate_health_requires_body_subchecks(monkeypatch):
    smoke = load_smoke_module()

    monkeypatch.setattr(
        smoke,
        "http_get_json",
        lambda *args, **kwargs: {
            "url": "http://skyradar.example.com/api/health",
            "status": 200,
            "payload": {"github": True, "mongodb": {"ok": 1.0}},
        },
    )

    result = smoke.check_health("http://skyradar.example.com", timeout=1)

    assert result["ok"] is True
    assert result["errors"] == []


def test_release_gate_health_fails_when_mongodb_subcheck_is_unhealthy(monkeypatch):
    smoke = load_smoke_module()

    monkeypatch.setattr(
        smoke,
        "http_get_json",
        lambda *args, **kwargs: {
            "url": "http://skyradar.example.com/api/health",
            "status": 200,
            "payload": {"github": True, "mongodb": {"ok": 0.0}},
        },
    )

    result = smoke.check_health("http://skyradar.example.com", timeout=1)

    assert result["ok"] is False
    assert result["errors"] == ["mongodb ok is not 1.0"]


def test_release_gate_leakage_list_uses_frontend_pagination_contract(monkeypatch):
    smoke = load_smoke_module()
    captured = {}

    def fake_get_json(base_url, path, query=None, timeout=20, basic_auth=None):
        captured.update({"base_url": base_url, "path": path, "query": query, "timeout": timeout})
        return {
            "url": "http://skyradar.example.com/api/leakage",
            "status": 200,
            "payload": {
                "status": 200,
                "total": 1,
                "result": [{"_id": "real-leakage-id"}],
            },
        }

    monkeypatch.setattr(smoke, "http_get_json", fake_get_json)

    result = smoke.check_leakage_list(
        "http://skyradar.example.com",
        "REAL_TAG",
        {"ignore": 0},
        limit=10,
        timeout=5,
    )

    assert result["ok"] is True
    assert result["leakage_id"] == "real-leakage-id"
    assert captured["query"] == {
        "status": json.dumps({"ignore": 0}, separators=(",", ":")),
        "from": 1,
        "limit": 10,
        "tag": "REAL_TAG",
    }


def test_release_gate_redacts_password_from_report_payload():
    smoke = load_smoke_module()

    payload = smoke.redact_sensitive(
        {
            "username": "octocat",
            "password": "ghp_secret",
            "nested": [{"password": "smtp-secret", "enabled": True}],
        }
    )

    assert payload == {
        "username": "octocat",
        "nested": [{"enabled": True}],
    }


def test_release_gate_builds_basic_auth_header():
    smoke = load_smoke_module()

    assert smoke.basic_auth_header("admin", "secret") == "Basic YWRtaW46c2VjcmV0"
    assert smoke.basic_auth_header(None, None) is None


def test_release_gate_browser_command_includes_tag_route(tmp_path, monkeypatch):
    smoke = load_smoke_module()
    captured = {}

    class Completed:
        returncode = 0
        stdout = json.dumps({"base_url": "http://skyradar.example.com", "checks": []})
        stderr = ""

    def fake_run(command, text, capture_output, check):
        captured.update(
            {
                "command": command,
                "text": text,
                "capture_output": capture_output,
                "check": check,
            }
        )
        return Completed()

    monkeypatch.setattr(smoke.subprocess, "run", fake_run)

    result = smoke.run_browser_smoke(
        "http://skyradar.example.com",
        "real-leakage-id",
        "REAL_TAG",
        tmp_path,
        timeout=15,
    )

    assert result["ok"] is True
    assert captured["text"] is True
    assert captured["capture_output"] is True
    assert captured["check"] is False
    assert "--leakage-id" in captured["command"]
    assert "real-leakage-id" in captured["command"]
    assert "--path" in captured["command"]
    assert "/?tag=REAL_TAG" in captured["command"]


def test_release_gate_browser_command_redacts_basic_auth_password(tmp_path, monkeypatch):
    smoke = load_smoke_module()
    captured = {}

    class Completed:
        returncode = 0
        stdout = json.dumps({"base_url": "http://skyradar.example.com", "checks": []})
        stderr = ""

    def fake_run(command, text, capture_output, check):
        captured["raw_command"] = command
        return Completed()

    monkeypatch.setattr(smoke.subprocess, "run", fake_run)

    result = smoke.run_browser_smoke(
        "http://skyradar.example.com",
        "real-leakage-id",
        None,
        tmp_path,
        timeout=15,
        basic_auth_username="admin",
        basic_auth_password="secret-password",
    )

    assert result["ok"] is True
    assert "secret-password" in captured["raw_command"]
    assert "secret-password" not in result["command"]
    assert "***" in result["command"]
