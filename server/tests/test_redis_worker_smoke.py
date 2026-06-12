# coding: utf-8
# @File        : test_redis_worker_smoke.py
# @Author      : NanMing
# @Date        : 2026/6/10 16:30
# @Description : Tests Redis worker smoke command behavior.

import json
import subprocess
import sys
from pathlib import Path


SMOKE_SCRIPT = Path("scripts/backend_redis_worker_smoke.py")


def run_smoke(*args):
    return subprocess.run(
        [sys.executable, str(SMOKE_SCRIPT), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def test_redis_worker_smoke_dry_run_generates_module_and_consumer_command():
    result = run_smoke("--dry-run", "--json")

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)

    assert payload["ok"] is True
    assert payload["mode"] == "dry-run"
    assert payload["module"]["name"] == "skyradar_redis_worker_smoke_app"
    assert payload["module"]["source_sha256"]
    assert payload["consumer_command"][-1] == "skyradar_redis_worker_smoke_app.huey"
    assert {check["name"] for check in payload["checks"]} == {
        "temporary Huey module generated",
        "consumer command constructed",
        "smoke task source generated",
    }


def test_redis_worker_smoke_reports_clear_error_when_redis_is_unreachable():
    result = run_smoke(
        "--json",
        "--redis-host",
        "127.0.0.1",
        "--redis-port",
        "1",
        "--connect-timeout",
        "0.1",
        "--timeout",
        "0.1",
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert "Redis is not reachable at 127.0.0.1:1" in payload["error"]
