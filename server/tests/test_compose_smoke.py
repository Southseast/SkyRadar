# coding: utf-8
# @File        : test_compose_smoke.py
# @Author      : NanMing
# @Date        : 2026/6/12 12:47
# @Description : Tests Docker Compose smoke command behavior.

import json
import subprocess
import sys

from scripts import backend_compose_smoke

def test_resolve_services_prefers_split_compose_names():
    args = backend_compose_smoke.parse_args([])

    services = backend_compose_smoke.resolve_services(
        ["mongo", "redis", "skyradar", "nginx", "worker"],
        args,
    )

    assert services.mongo == "mongo"
    assert services.redis == "redis"
    assert services.web == "skyradar"
    assert services.nginx == "nginx"
    assert services.worker == "worker"

def test_resolve_services_requires_standard_compose_services():
    args = backend_compose_smoke.parse_args([])

    try:
        backend_compose_smoke.resolve_services(["mongo", "skyradar"], args)
    except backend_compose_smoke.SmokeFailure as error:
        assert "compose services missing" in str(error)
    else:
        raise AssertionError("expected SmokeFailure")

def test_startup_commands_support_fresh_volume_rebuild():
    args = backend_compose_smoke.parse_args(
        ["--fresh-volumes", "--project-name", "skyradar-smoke", "--http-port", "18081"]
    )

    commands = [" ".join(command) for command in backend_compose_smoke.startup_commands(args)]
    shutdown = " ".join(backend_compose_smoke.shutdown_command(args, include_volumes=True))

    assert commands == [
        "docker compose -f compose.yml -p skyradar-smoke down -v --remove-orphans",
        "docker compose -f compose.yml -p skyradar-smoke up -d --build",
    ]
    assert shutdown == "docker compose -f compose.yml -p skyradar-smoke down -v --remove-orphans"

def test_smoke_request_adds_basic_auth_from_environment(monkeypatch):
    monkeypatch.setenv("SKYRADAR_BASIC_AUTH_USERNAME", "skyradar")
    monkeypatch.setenv("SKYRADAR_BASIC_AUTH_PASSWORD", "test-password-not-secret")

    request = backend_compose_smoke.smoke_request(
        "http://127.0.0.1:18081/api/health",
        {"Accept": "application/json"},
    )

    assert request.headers["Accept"] == "application/json"
    assert request.headers["Authorization"].startswith("Basic ")

def test_basic_auth_environment_requires_username_and_password(monkeypatch):
    monkeypatch.setenv("SKYRADAR_BASIC_AUTH_USERNAME", "skyradar")
    monkeypatch.delenv("SKYRADAR_BASIC_AUTH_PASSWORD", raising=False)

    try:
        backend_compose_smoke.basic_auth_headers_from_env()
    except backend_compose_smoke.SmokeFailure as error:
        assert "must be set together" in str(error)
    else:
        raise AssertionError("expected SmokeFailure")

def test_backend_compose_smoke_dry_run_reports_current_service_mapping():
    result = subprocess.run(
        [
            sys.executable,
            "scripts/backend_compose_smoke.py",
            "--dry-run",
            "--json",
            "--http-port",
            "18081",
            "--no-build",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["dry_run"] is True
    assert payload["environment"]["SKYRADAR_HTTP_PORT"] == "18081"
    assert payload["commands"]["startup"] == ["docker compose -f compose.yml up -d"]
    assert payload["mapping"]["mongo"] == "mongo"
    assert payload["mapping"]["web"] in {"web", "skyradar"}
    assert payload["mapping"]["nginx"] in {"nginx", "web", "skyradar"}
    assert payload["mapping"]["redis"] in {"redis", "skyradar"}
    assert payload["mapping"]["worker"] in {"worker", "skyradar"}

def test_compose_log_scan_patterns_detect_failures_and_secrets():
    logs = "\n".join(
        [
            "worker-1 | huey running",
            "worker-1 | Traceback (most recent call last):",
            "skyradar-1 | token=abc123",
        ]
    )

    failures = backend_compose_smoke.matching_lines(
        logs,
        backend_compose_smoke.LOG_FAILURE_PATTERNS,
    )
    secrets = backend_compose_smoke.matching_lines(
        logs,
        backend_compose_smoke.SECRET_PATTERNS,
    )

    assert failures == ["worker-1 | Traceback (most recent call last):"]
    assert secrets == ["skyradar-1 | token=abc123"]
