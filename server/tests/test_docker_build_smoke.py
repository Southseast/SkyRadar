# coding: utf-8
# @File        : test_docker_build_smoke.py
# @Author      : NanMing
# @Date        : 2026/6/12 14:50
# @Description : Tests backend Docker build smoke command behavior.

import subprocess
import sys
from pathlib import Path


SCRIPT = Path("scripts/backend_docker_build_smoke.py")


def run_dry_run(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--dry-run", *args],
        check=False,
        capture_output=True,
        text=True,
    )


def test_backend_docker_build_smoke_default_dry_run_command():
    result = run_dry_run()

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == (
        "docker build -t skyradar-backend-build-smoke ."
    )
    assert result.stderr == ""


def test_backend_docker_build_smoke_custom_dry_run_command():
    result = run_dry_run(
        "--platform",
        "linux/arm64",
        "--tag",
        "skyradar:test",
        "--context",
        "backend context",
        "--dockerfile",
        "Dockerfile.test",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == (
        "docker build --platform linux/arm64 "
        "-t skyradar:test -f Dockerfile.test 'backend context'"
    )
    assert result.stderr == ""
