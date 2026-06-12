# coding: utf-8
# @File        : test_architecture_guard.py
# @Author      : NanMing
# @Date        : 2026/6/9 18:54
# @Description : Tests backend architecture guard behavior.

import json
import subprocess
import sys
from pathlib import Path


GUARD_SCRIPT = Path("scripts/backend_architecture_guard.py")


def test_backend_architecture_guard_passes_current_tree():
    result = subprocess.run(
        [sys.executable, str(GUARD_SCRIPT), "--json"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert {check["name"] for check in payload["checks"]} == {
        "unsupported backend source paths absent",
        "unsupported imports absent from runtime source",
        "internal function names stay provider-specific",
        "unsupported Flask dependencies absent",
        "domain routes import local services",
        "domain directories keep local implementation and tests",
        "routes and workers stay behind service boundary",
        "async routes isolate sync services with threadpool",
        "Huey supervisor uses workers.huey",
        "supervisor programs start from project root",
    }
