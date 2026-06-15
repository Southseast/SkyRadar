#!/usr/bin/env python3
# coding: utf-8
# @File        : frontend_camoufox_smoke.py
# @Author      : NanMing
# @Date        : 2026/6/12 12:34
# @Description : Run browser smoke checks with Camoufox against a running SkyRadar frontend.

"""Run browser smoke checks with Camoufox against a running SkyRadar frontend."""

from loguru import logger
import argparse
import json
import os
from pathlib import Path
import sys
from urllib.parse import urljoin



def configure_logging():
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{message}")


DEFAULT_BASE_URL = "http://127.0.0.1:18080"
DEFAULT_VIEWPORTS = ("1440x900", "1280x720", "768x1024", "375x812")
DEFAULT_PATHS = (
    "/",
    "/setting",
    "/setting/github",
    "/setting/rule",
    "/setting/task",
    "/setting/blacklist",
    "/setting/notice",
    "/api/v1/health",
)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Open SkyRadar pages in a real Camoufox browser and fail on blank "
            "screens, HTTP navigation errors, page errors, or severe console errors."
        )
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("SKYRADAR_BASE_URL", DEFAULT_BASE_URL),
        help="Frontend base URL, default: %(default)s",
    )
    parser.add_argument(
        "--path",
        action="append",
        default=[],
        help="Extra route to check. Repeat for multiple routes.",
    )
    parser.add_argument(
        "--leakage-id",
        default=os.environ.get("SKYRADAR_SMOKE_LEAKAGE_ID"),
        help="Optional real leakage id used to check /view/leakage/:id.",
    )
    parser.add_argument(
        "--skip-api-health",
        action="store_true",
        help="Skip /api/v1/health. Use this for Vite preview without a backend proxy.",
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
        "--viewport",
        action="append",
        default=[],
        help="Viewport in WIDTHxHEIGHT form. Repeat for multiple viewports.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=15,
        help="Per-navigation timeout in seconds, default: %(default)s",
    )
    parser.add_argument(
        "--screenshot-dir",
        help="Optional directory for screenshots of each checked page.",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run Camoufox with a visible browser window.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON output.",
    )
    return parser.parse_args()


def import_camoufox():
    try:
        from camoufox.sync_api import Camoufox
    except ModuleNotFoundError as error:
        logger.error(
            "camoufox is not installed. Run:\n"
            "  uv run --with camoufox==0.4.11 python scripts/frontend_camoufox_smoke.py\n",
        )
        raise SystemExit(2) from error

    return Camoufox


def normalize_base_url(base_url):
    return base_url.rstrip("/") + "/"


def build_url(base_url, path):
    return urljoin(normalize_base_url(base_url), path.lstrip("/"))


def parse_viewport(value):
    try:
        width_text, height_text = value.lower().split("x", 1)
        width = int(width_text)
        height = int(height_text)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "viewport must use WIDTHxHEIGHT, for example 1440x900"
        ) from error

    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError("viewport dimensions must be positive")

    return {"width": width, "height": height, "label": "%sx%s" % (width, height)}


def collect_paths(args):
    paths = list(DEFAULT_PATHS)
    if args.skip_api_health:
        paths = [path for path in paths if path != "/api/v1/health"]
    paths.extend(args.path)
    if args.leakage_id:
        paths.append("/view/leakage/%s" % args.leakage_id)
    return dedupe(paths)


def dedupe(values):
    seen = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def ensure_screenshot_dir(path):
    if not path:
        return None
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def screenshot_path(directory, viewport_label, route):
    safe_route = route.strip("/").replace("/", "__") or "root"
    return directory / ("%s__%s.png" % (viewport_label, safe_route))


def is_allowed_console_message(message):
    text = message.get("text", "")
    if "Failed to load resource: the server responded with a status of 404" in text:
        return True
    return False


def check_page(page, base_url, route, viewport, timeout_ms, screenshot_dir):
    result = {
        "route": route,
        "url": build_url(base_url, route),
        "viewport": viewport["label"],
        "ok": False,
        "status": None,
        "title": None,
        "body_text_length": 0,
        "root_text_length": 0,
        "console_errors": [],
        "page_errors": [],
        "request_failures": [],
        "screenshot": None,
        "errors": [],
    }

    console_messages = []
    page_errors = []
    request_failures = []

    def on_console(message):
        if message.type in ("error",):
            console_messages.append({"type": message.type, "text": message.text})

    def on_page_error(error):
        page_errors.append(str(error))

    def on_request_failed(request):
        failure = request.failure
        failure_text = failure.get("errorText") if isinstance(failure, dict) else str(failure)
        request_failures.append({"url": request.url, "error": failure_text})

    page.on("console", on_console)
    page.on("pageerror", on_page_error)
    page.on("requestfailed", on_request_failed)

    try:
        response = page.goto(result["url"], wait_until="networkidle", timeout=timeout_ms)
        if response is not None:
            result["status"] = response.status
        page.wait_for_selector("#root", state="attached", timeout=timeout_ms)
        page.wait_for_function(
            "() => document.querySelector('#root')?.innerText.trim().length > 0",
            timeout=timeout_ms,
        )
        result["title"] = page.title()
        result["body_text_length"] = page.locator("body").inner_text(timeout=timeout_ms).__len__()
        result["root_text_length"] = page.locator("#root").inner_text(timeout=timeout_ms).__len__()

        if screenshot_dir:
            path = screenshot_path(screenshot_dir, viewport["label"], route)
            page.screenshot(path=str(path), full_page=True)
            result["screenshot"] = str(path)
    except Exception as error:
        result["errors"].append(str(error))
    finally:
        page.remove_listener("console", on_console)
        page.remove_listener("pageerror", on_page_error)
        page.remove_listener("requestfailed", on_request_failed)

    result["console_errors"] = [
        message for message in console_messages if not is_allowed_console_message(message)
    ]
    result["page_errors"] = page_errors
    result["request_failures"] = request_failures

    if result["status"] is None:
        result["errors"].append("navigation did not return an HTTP response")
    elif not (200 <= result["status"] < 400):
        result["errors"].append("navigation returned HTTP %s" % result["status"])

    if result["title"] != "SkyRadar":
        result["errors"].append("expected document title SkyRadar, got %r" % result["title"])

    if result["body_text_length"] <= 0 or result["root_text_length"] <= 0:
        result["errors"].append("page body or #root is blank")

    if result["console_errors"]:
        result["errors"].append("console error count: %d" % len(result["console_errors"]))
    if result["page_errors"]:
        result["errors"].append("page error count: %d" % len(result["page_errors"]))
    if result["request_failures"]:
        result["errors"].append("request failure count: %d" % len(result["request_failures"]))

    result["ok"] = not result["errors"]
    return result


def check_api_page(page, base_url, route, viewport, timeout_ms, screenshot_dir):
    result = {
        "route": route,
        "url": build_url(base_url, route),
        "viewport": viewport["label"],
        "ok": False,
        "status": None,
        "title": None,
        "body_text_length": 0,
        "root_text_length": None,
        "console_errors": [],
        "page_errors": [],
        "request_failures": [],
        "screenshot": None,
        "errors": [],
    }

    console_messages = []
    page_errors = []
    request_failures = []

    def on_console(message):
        if message.type in ("error",):
            console_messages.append({"type": message.type, "text": message.text})

    def on_page_error(error):
        page_errors.append(str(error))

    def on_request_failed(request):
        failure = request.failure
        failure_text = failure.get("errorText") if isinstance(failure, dict) else str(failure)
        request_failures.append({"url": request.url, "error": failure_text})

    page.on("console", on_console)
    page.on("pageerror", on_page_error)
    page.on("requestfailed", on_request_failed)

    try:
        response = page.goto(result["url"], wait_until="networkidle", timeout=timeout_ms)
        if response is not None:
            result["status"] = response.status
        result["title"] = page.title()
        result["body_text_length"] = len(page.locator("body").inner_text(timeout=timeout_ms))

        if screenshot_dir:
            path = screenshot_path(screenshot_dir, viewport["label"], route)
            page.screenshot(path=str(path), full_page=True)
            result["screenshot"] = str(path)
    except Exception as error:
        result["errors"].append(str(error))
    finally:
        page.remove_listener("console", on_console)
        page.remove_listener("pageerror", on_page_error)
        page.remove_listener("requestfailed", on_request_failed)

    result["console_errors"] = [
        message for message in console_messages if not is_allowed_console_message(message)
    ]
    result["page_errors"] = page_errors
    result["request_failures"] = request_failures

    if result["status"] is None:
        result["errors"].append("navigation did not return an HTTP response")
    elif not (200 <= result["status"] < 400):
        result["errors"].append("navigation returned HTTP %s" % result["status"])

    if result["body_text_length"] <= 0:
        result["errors"].append("API response body is blank")

    if result["console_errors"]:
        result["errors"].append("console error count: %d" % len(result["console_errors"]))
    if result["page_errors"]:
        result["errors"].append("page error count: %d" % len(result["page_errors"]))
    if result["request_failures"]:
        result["errors"].append("request failure count: %d" % len(result["request_failures"]))

    result["ok"] = not result["errors"]
    return result


def run_smoke(args):
    Camoufox = import_camoufox()
    base_url = normalize_base_url(args.base_url)
    viewports = [parse_viewport(value) for value in (args.viewport or DEFAULT_VIEWPORTS)]
    paths = collect_paths(args)
    screenshot_dir = ensure_screenshot_dir(args.screenshot_dir)
    timeout_ms = int(args.timeout * 1000)
    checks = []
    http_credentials = None
    if args.basic_auth_username or args.basic_auth_password:
        if not args.basic_auth_username or not args.basic_auth_password:
            raise SystemExit("--basic-auth-username and --basic-auth-password must be set together")
        http_credentials = {
            "username": args.basic_auth_username,
            "password": args.basic_auth_password,
        }

    with Camoufox(headless=not args.headed) as browser:
        for viewport in viewports:
            context = browser.new_context(
                viewport={"width": viewport["width"], "height": viewport["height"]},
                locale="zh-CN",
                http_credentials=http_credentials,
            )
            try:
                for route in paths:
                    page = context.new_page()
                    try:
                        if route.startswith("/api/"):
                            checks.append(
                                check_api_page(
                                    page, base_url, route, viewport, timeout_ms, screenshot_dir
                                )
                            )
                        else:
                            checks.append(
                                check_page(
                                    page, base_url, route, viewport, timeout_ms, screenshot_dir
                                )
                            )
                    finally:
                        page.close()
            finally:
                context.close()

    return {"base_url": base_url.rstrip("/"), "checks": checks}


def print_human(report):
    logger.info("SkyRadar Camoufox browser smoke")
    logger.info("Base URL: %s" % report["base_url"])
    logger.info("")
    for check in report["checks"]:
        label = "PASS" if check["ok"] else "FAIL"
        logger.info("[%s] %s %s HTTP %s" % (label, check["viewport"], check["route"], check["status"]))
        if check["screenshot"]:
            logger.info("  screenshot: %s" % check["screenshot"])
        for error in check["errors"]:
            logger.info("  error: %s" % error)
        logger.info("")


def main():
    configure_logging()
    args = parse_args()
    report = run_smoke(args)
    if args.json:
        logger.info(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_human(report)

    return 0 if all(check["ok"] for check in report["checks"]) else 1


if __name__ == "__main__":
    sys.exit(main())
