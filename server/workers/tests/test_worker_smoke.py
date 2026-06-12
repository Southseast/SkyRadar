# coding: utf-8
# @File        : test_worker_smoke.py
# @Author      : NanMing
# @Date        : 2026/6/11 17:23
# @Description : Tests local Huey worker smoke command behavior.

import json
import subprocess
import sys

def test_backend_worker_smoke_script_runs_without_external_services():
    result = subprocess.run(
        [sys.executable, "scripts/backend_worker_smoke.py", "--json"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert {check["name"] for check in payload["checks"]} >= {
        "import workers module with fake database",
        "huey name is stable",
        "expected tasks are registered",
        "expected periodic tasks are registered",
        "fake database handled import side effects",
        "huey immediate local task executes",
    }
