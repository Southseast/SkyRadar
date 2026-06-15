#!/usr/bin/env python3
# coding: utf-8
# @File        : backend_http_smoke.py
# @Author      : NanMing
# @Date        : 2026/6/10 10:19
# @Description : Run real HTTP smoke checks against a running SkyRadar backend.

"""Run real HTTP smoke checks against a running SkyRadar backend."""

from loguru import logger
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request



def configure_logging():
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{message}")


DEFAULT_BASE_URL = "http://127.0.0.1"
DEFAULT_TIMEOUT_SECONDS = 10


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Send real HTTP requests to a running SkyRadar backend. "
            "The default check validates GET /api/v1/health."
        )
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("SKYRADAR_BASE_URL", DEFAULT_BASE_URL),
        help="Backend base URL, default: %(default)s",
    )
    parser.add_argument(
        "--endpoint",
        action="append",
        default=[],
        help=(
            "Extra read-only endpoint to request after /api/v1/health. "
            "Repeat for multiple endpoints, for example --endpoint /api/v1/statistics."
        ),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Per-request timeout in seconds, default: %(default)s",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON output.",
    )
    return parser.parse_args()


def normalize_base_url(base_url):
    return base_url.rstrip("/") + "/"


def build_url(base_url, endpoint):
    return urllib.parse.urljoin(normalize_base_url(base_url), endpoint.lstrip("/"))


def request_json(base_url, endpoint, timeout):
    url = build_url(base_url, endpoint)
    result = {
        "endpoint": endpoint,
        "url": url,
        "ok": False,
        "status": None,
        "json": None,
        "errors": [],
    }

    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "skyradar-backend-http-smoke/1.0",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result["status"] = response.getcode()
            raw_body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as error:
        result["status"] = error.code
        raw_body = error.read().decode("utf-8", errors="replace")
        result["errors"].append("HTTP request failed with status %s" % error.code)
    except urllib.error.URLError as error:
        result["errors"].append("HTTP request failed: %s" % error.reason)
        return result
    except TimeoutError:
        result["errors"].append("HTTP request timed out after %.1fs" % timeout)
        return result

    if result["status"] is not None and not (200 <= result["status"] < 300):
        if not result["errors"]:
            result["errors"].append("HTTP request failed with status %s" % result["status"])

    try:
        result["json"] = json.loads(raw_body)
    except json.JSONDecodeError as error:
        result["errors"].append("Response is not valid JSON: %s" % error)

    return result


def validate_health(result):
    body = result.get("json")
    if result["errors"] and body is None:
        return result
    if not isinstance(body, dict):
        result["errors"].append("/api/v1/health response must be a JSON object")
        return result

    data = body.get("data")
    if not isinstance(data, dict):
        result["errors"].append("/api/v1/health response is missing data object")
        return result

    if "github" not in data:
        result["errors"].append("/api/v1/health response is missing github")
    if "mongodb" not in data:
        result["errors"].append("/api/v1/health response is missing mongodb")

    github = data.get("github")
    if not isinstance(github, dict) or github.get("ok") is not True:
        result["errors"].append("GitHub health check failed: %r" % github)

    mongodb = data.get("mongodb")
    if isinstance(mongodb, str):
        result["errors"].append("MongoDB health check failed: %s" % mongodb)
    elif isinstance(mongodb, dict):
        ok_value = mongodb.get("ok")
        if ok_value is not True:
            result["errors"].append("MongoDB health check returned ok=%r" % ok_value)
    else:
        result["errors"].append(
            "MongoDB health check must return an object on success, got %r" % mongodb
        )

    return result


def validate_generic_read_only(result):
    if result["errors"] and result.get("json") is None:
        return result
    if result.get("json") is None:
        result["errors"].append("Read-only endpoint did not return JSON")
    return result


def run_checks(base_url, endpoints, timeout):
    checks = []

    health = request_json(base_url, "/api/v1/health", timeout)
    checks.append(validate_health(health))

    for endpoint in endpoints:
        if endpoint == "/api/v1/health":
            continue
        result = request_json(base_url, endpoint, timeout)
        checks.append(validate_generic_read_only(result))

    for check in checks:
        check["ok"] = not check["errors"]

    return checks


def print_human(base_url, checks):
    logger.info("SkyRadar backend HTTP smoke")
    logger.info("Base URL: %s" % base_url)
    logger.info("")

    for check in checks:
        label = "PASS" if check["ok"] else "FAIL"
        status = check["status"] if check["status"] is not None else "n/a"
        logger.info("[%s] GET %s (HTTP %s)" % (label, check["endpoint"], status))
        if check["endpoint"] == "/api/v1/health" and isinstance(check.get("json"), dict):
            data = check["json"].get("data") if isinstance(check["json"].get("data"), dict) else {}
            logger.info("  github: %r" % data.get("github"))
            logger.info("  mongodb: %r" % data.get("mongodb"))
        for error in check["errors"]:
            logger.info("  error: %s" % error)
        logger.info("")


def main():
    configure_logging()
    args = parse_args()
    checks = run_checks(args.base_url, args.endpoint, args.timeout)

    if args.json:
        logger.info(json.dumps({"base_url": args.base_url, "checks": checks}, indent=2))
    else:
        print_human(args.base_url, checks)

    return 0 if all(check["ok"] for check in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
