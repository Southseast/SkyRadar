#!/usr/bin/env python3
# coding: utf-8
# @File        : frontend_release_gate_smoke.py
# @Author      : NanMing
# @Date        : 2026/6/12 10:11
# @Description : Run read-only release gate smoke checks for a SkyRadar frontend deployment.

"""Run read-only release gate smoke checks for a SkyRadar frontend deployment."""

from loguru import logger
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from base64 import b64encode
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen



def configure_logging():
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{message}")


DEFAULT_BASE_URL = "http://127.0.0.1:18080"
DEFAULT_SETTING_PATHS = (
    "/api/v1/github-accounts",
    "/api/v1/search-rules",
    "/api/v1/task-schedules/current",
    "/api/v1/blacklist-items",
    "/api/v1/notification-recipients",
    "/api/v1/mail-settings/current",
    "/api/v1/webhooks",
)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Validate a deployed SkyRadar frontend in read-only mode. The script checks "
            "API contracts, finds or uses a real leakage id, then runs Camoufox browser "
            "smoke with screenshots and a JSON report."
        )
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("SKYRADAR_BASE_URL", DEFAULT_BASE_URL),
        help="SkyRadar base URL, default: %(default)s",
    )
    parser.add_argument(
        "--artifact-dir",
        default=os.environ.get("SKYRADAR_RELEASE_ARTIFACT_DIR", ".artifacts/release-gate-smoke"),
        help="Directory for release smoke JSON and screenshots, default: %(default)s",
    )
    parser.add_argument(
        "--leakage-id",
        default=os.environ.get("SKYRADAR_RELEASE_LEAKAGE_ID"),
        help="Known leakage id to validate. If omitted, the script reads one from /api/v1/leakages.",
    )
    parser.add_argument(
        "--tag",
        default=os.environ.get("SKYRADAR_RELEASE_TAG"),
        help="Optional tag used for /api/v1/leakages and /?tag=... checks.",
    )
    parser.add_argument(
        "--basic-auth-username",
        default=os.environ.get("SKYRADAR_BASIC_AUTH_USERNAME"),
        help="Optional nginx Basic Auth username. Defaults to $SKYRADAR_BASIC_AUTH_USERNAME.",
    )
    parser.add_argument(
        "--basic-auth-password",
        default=os.environ.get("SKYRADAR_BASIC_AUTH_PASSWORD"),
        help="Optional nginx Basic Auth password. Defaults to $SKYRADAR_BASIC_AUTH_PASSWORD; never printed.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Read-only leakage list limit, default: %(default)s",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=20,
        help="HTTP and browser timeout in seconds, default: %(default)s",
    )
    parser.add_argument(
        "--skip-browser",
        action="store_true",
        help="Only run read-only API checks. Use when Camoufox is unavailable.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full JSON report instead of a human summary.",
    )
    return parser.parse_args()


def normalize_base_url(base_url):
    return base_url.rstrip("/") + "/"


def build_url(base_url, path, query=None):
    url = urljoin(normalize_base_url(base_url), path.lstrip("/"))
    if query:
        return url + "?" + urlencode(query)
    return url


def redact_sensitive(value):
    if isinstance(value, dict):
        return {key: redact_sensitive(item) for key, item in value.items() if key != "password"}
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    return value


def basic_auth_header(username, password):
    if not username and not password:
        return None
    if not username or not password:
        raise SystemExit("--basic-auth-username and --basic-auth-password must be set together")
    token = b64encode(("%s:%s" % (username, password)).encode("utf-8")).decode("ascii")
    return "Basic %s" % token


def http_get_json(base_url, path, query=None, timeout=20, basic_auth=None):
    url = build_url(base_url, path, query)
    headers = {"Accept": "application/json"}
    if basic_auth:
        headers["Authorization"] = basic_auth
    request = Request(url, headers=headers)
    with urlopen(request, timeout=timeout) as response:
        status = response.status
        body = response.read().decode("utf-8")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        payload = body
    return {"url": url, "status": status, "payload": redact_sensitive(payload)}


def check_health(base_url, timeout, basic_auth=None):
    result = http_get_json(base_url, "/api/v1/health", timeout=timeout, basic_auth=basic_auth)
    payload = result["payload"] if isinstance(result["payload"], dict) else {}
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    api = data.get("api")
    mongodb = data.get("mongodb")
    redis = data.get("redis")
    api_ok = isinstance(api, dict) and api.get("ok") is True
    mongodb_ok = isinstance(mongodb, dict) and mongodb.get("ok") is True
    redis_ok = isinstance(redis, dict) and redis.get("ok") is True
    errors = []
    if result["status"] != 200:
        errors.append("expected HTTP 200")
    if not api_ok:
        errors.append("api ok is not true")
    if not mongodb_ok:
        errors.append("mongodb ok is not true")
    if not redis_ok:
        errors.append("redis ok is not true")
    return {"name": "api health", "ok": not errors, "errors": errors, **result}


def check_leakage_list(base_url, tag, limit, timeout, basic_auth=None):
    query = {
        "security": 0,
        "reviewed": "false",
        "page": 1,
        "page_size": limit,
    }
    if tag:
        query["tag"] = tag
    result = http_get_json(base_url, "/api/v1/leakages", query=query, timeout=timeout, basic_auth=basic_auth)
    payload = result["payload"] if isinstance(result["payload"], dict) else {}
    rows = payload.get("data") if isinstance(payload.get("data"), list) else []
    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    errors = []
    if result["status"] != 200:
        errors.append("expected HTTP 200")
    if not rows:
        errors.append("expected at least one leakage result")
    leakage_id = None
    if rows and isinstance(rows[0], dict):
        leakage_id = rows[0].get("id") or rows[0].get("_id")
    return {
        "name": "leakage list",
        "ok": not errors,
        "errors": errors,
        "leakage_id": leakage_id,
        "total": meta.get("total"),
        **result,
    }


def check_detail_endpoint(base_url, path, leakage_id, timeout, basic_auth=None):
    result = http_get_json(base_url, path % leakage_id, timeout=timeout, basic_auth=basic_auth)
    payload = result["payload"] if isinstance(result["payload"], dict) else {}
    errors = []
    if result["status"] != 200:
        errors.append("expected HTTP 200")
    if payload.get("data") in (None, [], ""):
        errors.append("expected non-empty data")
    return {"name": path, "ok": not errors, "errors": errors, **result}


def check_settings(base_url, timeout, basic_auth=None):
    checks = []
    for path in DEFAULT_SETTING_PATHS:
        result = http_get_json(base_url, path, timeout=timeout, basic_auth=basic_auth)
        payload = result["payload"] if isinstance(result["payload"], dict) else {}
        errors = []
        if result["status"] != 200:
            errors.append("expected HTTP 200")
        if "data" not in payload:
            errors.append("expected REST data envelope")
        checks.append({"name": path, "ok": not errors, "errors": errors, **result})
    return checks


def redact_command(command, secret):
    if not secret:
        return command
    return ["***" if item == secret else item for item in command]


def run_browser_smoke(base_url, leakage_id, tag, artifact_dir, timeout, basic_auth_username=None, basic_auth_password=None):
    screenshot_dir = artifact_dir / "screenshots"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "scripts/frontend_camoufox_smoke.py",
        "--base-url",
        base_url,
        "--leakage-id",
        leakage_id,
        "--screenshot-dir",
        str(screenshot_dir),
        "--timeout",
        str(timeout),
        "--json",
    ]
    if tag:
        command.extend(["--path", "/?tag=%s" % tag])
    if basic_auth_username or basic_auth_password:
        command.extend(
            [
                "--basic-auth-username",
                basic_auth_username,
                "--basic-auth-password",
                basic_auth_password,
            ]
        )
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        payload = {"stdout": completed.stdout}
    return {
        "name": "camoufox browser smoke",
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "command": redact_command(command, basic_auth_password),
        "report": payload,
        "stderr": completed.stderr,
    }


def run_release_smoke(args):
    base_url = args.base_url.rstrip("/")
    artifact_dir = Path(args.artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    basic_auth = basic_auth_header(args.basic_auth_username, args.basic_auth_password)

    checks = []
    checks.append(check_health(base_url, args.timeout, basic_auth=basic_auth))
    leakage_list = check_leakage_list(base_url, args.tag, args.limit, args.timeout, basic_auth=basic_auth)
    checks.append(leakage_list)
    leakage_id = args.leakage_id or leakage_list.get("leakage_id")
    if leakage_id:
        checks.append(check_detail_endpoint(base_url, "/api/v1/leakages/%s", leakage_id, args.timeout, basic_auth=basic_auth))
        checks.append(check_detail_endpoint(base_url, "/api/v1/leakages/%s/code", leakage_id, args.timeout, basic_auth=basic_auth))
    else:
        checks.append(
            {
                "name": "leakage detail",
                "ok": False,
                "errors": ["missing leakage id; pass --leakage-id or provide list data"],
            }
        )

    checks.extend(check_settings(base_url, args.timeout, basic_auth=basic_auth))

    browser = None
    if not args.skip_browser and leakage_id:
        browser = run_browser_smoke(
            base_url,
            leakage_id,
            args.tag,
            artifact_dir,
            args.timeout,
            basic_auth_username=args.basic_auth_username,
            basic_auth_password=args.basic_auth_password,
        )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "tag": args.tag,
        "leakage_id": leakage_id,
        "basic_auth": bool(basic_auth),
        "checks": checks,
        "browser": browser,
    }
    report["ok"] = all(check["ok"] for check in checks) and (browser is None or browser["ok"])

    report_path = artifact_dir / "release-gate-smoke.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["report_path"] = str(report_path)
    return report


def print_human(report):
    logger.info("SkyRadar release gate smoke")
    logger.info("Base URL: %s" % report["base_url"])
    logger.info("Report: %s" % report["report_path"])
    logger.info("")
    for check in report["checks"]:
        logger.info("[%s] %s" % ("PASS" if check["ok"] else "FAIL", check["name"]))
        for error in check.get("errors", []):
            logger.info("  error: %s" % error)
    if report["browser"] is not None:
        logger.info("[%s] %s" % ("PASS" if report["browser"]["ok"] else "FAIL", report["browser"]["name"]))
        if report["browser"].get("stderr"):
            logger.info("  stderr: %s" % report["browser"]["stderr"].strip())


def main():
    configure_logging()
    args = parse_args()
    report = run_release_smoke(args)
    if args.json:
        logger.info(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_human(report)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
