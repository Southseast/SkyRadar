# coding: utf-8
# @File        : test_github_pat_smoke.py
# @Author      : NanMing
# @Date        : 2026/6/11 15:19
# @Description : Tests GitHub PAT smoke command behavior.

import json
import importlib.util
import os
import subprocess
import sys
from pathlib import Path


SMOKE_SCRIPT = Path("scripts/backend_github_pat_smoke.py")


def load_smoke_module():
    spec = importlib.util.spec_from_file_location("backend_github_pat_smoke", SMOKE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_smoke(*args, env=None):
    smoke_env = os.environ.copy()
    if env:
        smoke_env.update(env)
    return subprocess.run(
        [sys.executable, str(SMOKE_SCRIPT), *args],
        env=smoke_env,
        check=False,
        capture_output=True,
        text=True,
    )


def test_github_pat_smoke_dry_run_does_not_require_credentials():
    result = run_smoke("--dry-run", "--json")

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)

    assert payload["ok"] is True
    assert payload["dry_run"] is True
    assert payload["query"]
    assert {check["name"] for check in payload["checks"]} == {
        "live network disabled",
        "credential input supported",
        "search query configured",
    }


def test_github_pat_smoke_does_not_print_token_on_missing_username():
    token = "ghp_test_token_should_not_be_printed"
    result = run_smoke("--json", env={"SKYRADAR_GITHUB_SMOKE_TOKEN": token})

    assert result.returncode == 1
    assert token not in result.stdout
    assert token not in result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert "missing GitHub username" in payload["checks"][0]["detail"]


def test_github_pat_smoke_masks_username_in_log_detail():
    smoke = load_smoke_module()

    assert smoke._mask_identity("st.southsea@example.com") == "st***@example.com"
    assert smoke._mask_identity("octocat") == "oc***"
