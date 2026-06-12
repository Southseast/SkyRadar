#!/usr/bin/env python3
# coding: utf-8
# @File        : backend_github_pat_smoke.py
# @Author      : NanMing
# @Date        : 2026/6/10 15:14
# @Description : Run a controlled live GitHub PAT smoke for search and rate limit.

"""Run a controlled live GitHub PAT smoke for search and rate limit."""

from loguru import logger
import argparse
import json
import os
import sys



def configure_logging():
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{message}")


SERVER_ROOT = "server"

DEFAULT_QUERY = "repo:octocat/Hello-World Hello"
USERNAME_ENV = "SKYRADAR_GITHUB_SMOKE_USERNAME"
TOKEN_ENV = "SKYRADAR_GITHUB_SMOKE_TOKEN"
QUERY_ENV = "SKYRADAR_GITHUB_SMOKE_QUERY"

if SERVER_ROOT not in sys.path:
    sys.path.insert(0, SERVER_ROOT)


class SmokeFailure(Exception):
    pass


def _check(name, ok, detail):
    return {"name": name, "ok": bool(ok), "detail": detail}


def _redact(value, token):
    if token:
        value = value.replace(token, "***")
    return value


def _mask_identity(value):
    if not value:
        return ""
    if "@" in value:
        prefix, domain = value.split("@", 1)
        return f"{prefix[:2]}***@{domain}"
    return f"{value[:2]}***"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Validate a dedicated GitHub username/PAT can read search rate limits "
            "and execute a tiny code search. Use --dry-run for CI-safe planning."
        )
    )
    parser.add_argument("--username", default=os.environ.get(USERNAME_ENV), help=f"GitHub username. Defaults to ${USERNAME_ENV}.")
    parser.add_argument("--token", default=os.environ.get(TOKEN_ENV), help=f"GitHub PAT. Defaults to ${TOKEN_ENV}; never printed.")
    parser.add_argument("--query", default=os.environ.get(QUERY_ENV, DEFAULT_QUERY), help=f"Search query. Defaults to ${QUERY_ENV} or a public octocat query.")
    parser.add_argument("--max-results", type=int, default=1, help="Maximum first-page results to inspect.")
    parser.add_argument("--dry-run", action="store_true", help="Validate command shape without contacting GitHub.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    return parser.parse_args(argv)


def run_live_smoke(args):
    from integrations import github as github_integration

    checks = []
    if not args.username:
        raise SmokeFailure(f"missing GitHub username; set {USERNAME_ENV} or pass --username")
    if not args.token:
        raise SmokeFailure(f"missing GitHub PAT; set {TOKEN_ENV} or pass --token")
    if not args.query:
        raise SmokeFailure(f"missing GitHub search query; set {QUERY_ENV} or pass --query")

    checks.append(
        _check(
            "dedicated credentials configured",
            True,
            f"username={_mask_identity(args.username)}, token=***",
        )
    )
    checks.append(_check("search query configured", True, args.query))

    client = github_integration.create_client(args.username, args.token)
    rate = github_integration.search_rate_limit(client)
    checks.append(
        _check(
            "search rate limit readable",
            rate["limit"] >= 0 and rate["remaining"] >= 0,
            f"remaining={rate['remaining']}, limit={rate['limit']}",
        )
    )

    repos = github_integration.search_code(client, args.query)
    page = list(repos.get_page(0))[: max(args.max_results, 0)]
    checks.append(
        _check(
            "code search first page readable",
            True,
            f"total={int(getattr(repos, 'totalCount', 0))}, inspected={len(page)}",
        )
    )
    results = [
        {
            "repository": getattr(getattr(item, "repository", None), "full_name", None),
            "path": getattr(item, "path", None),
            "sha": getattr(item, "sha", "")[:12],
        }
        for item in page
    ]
    return {
        "ok": all(check["ok"] for check in checks),
        "dry_run": False,
        "query": args.query,
        "rate": rate,
        "results": results,
        "checks": checks,
    }

def run_dry_run(args):
    checks = [
        _check("live network disabled", True, "dry-run mode does not contact GitHub"),
        _check("credential input supported", True, f"use {USERNAME_ENV}/{TOKEN_ENV} or --username/--token"),
        _check("search query configured", bool(args.query), args.query or f"set {QUERY_ENV} or pass --query"),
    ]
    return {
        "ok": all(check["ok"] for check in checks),
        "dry_run": True,
        "query": args.query,
        "rate": None,
        "results": [],
        "checks": checks,
    }

def print_result(payload, as_json):
    if as_json:
        logger.info(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return
    logger.info(f"backend-github-pat-smoke: {'ok' if payload['ok'] else 'failed'}")
    for check in payload["checks"]:
        marker = "ok" if check["ok"] else "failed"
        logger.info(f"- {marker}: {check['name']} - {check['detail']}")

def main(argv=None):
    configure_logging()
    args = parse_args(argv)
    try:
        payload = run_dry_run(args) if args.dry_run else run_live_smoke(args)
    except Exception as error:
        message = _redact(str(error), args.token)
        payload = {
            "ok": False,
            "dry_run": args.dry_run,
            "query": args.query,
            "rate": None,
            "results": [],
            "checks": [_check("github pat smoke failed", False, message)],
        }
    print_result(payload, args.json)
    return 0 if payload["ok"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
