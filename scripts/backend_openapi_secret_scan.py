#!/usr/bin/env python3
# coding: utf-8
# @File        : backend_openapi_secret_scan.py
# @Author      : NanMing
# @Date        : 2026/6/12 15:31
# @Description : Scan the hand-maintained OpenAPI contract for leaked secret examples.

"""Scan the hand-maintained OpenAPI contract for leaked secret examples."""

from loguru import logger
import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlsplit

import yaml



def configure_logging(stream=sys.stdout):
    logger.remove()
    logger.add(stream, level="INFO", format="{message}")


DEFAULT_OPENAPI_PATH = Path("docs/api/openapi.yaml")

TEXT_SURFACE_KEYS = {"description", "summary", "example", "examples", "default"}
EXAMPLE_SURFACE_KEYS = {"example", "examples", "default", "value"}
SENSITIVE_FIELD_KEYS = {
    "access_token",
    "auth_token",
    "github_token",
    "mongo_uri",
    "mongodb_uri",
    "password",
    "redis_password",
    "redis_url",
    "secret",
    "smtp_password",
    "token",
    "webhook_secret",
}
SAFE_PLACEHOLDER_WORDS = {
    "change-me",
    "changeme",
    "do_not_use",
    "dummy",
    "example",
    "fake",
    "masked",
    "placeholder",
    "redacted",
    "sample",
    "test",
    "your_",
    "your-",
}
SAFE_LITERAL_VALUES = {
    "",
    "***",
    "****",
    "<password>",
    "<secret>",
    "<token>",
    "password",
    "pass",
    "secret",
    "token",
}

GITHUB_TOKEN_PATTERNS = (
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{22,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,255}\b"),
)
DINGTALK_SECRET_PATTERN = re.compile(r"\bSEC[A-Za-z0-9]{20,}\b")
ACCESS_TOKEN_PATTERN = re.compile(r"(?i)(?:^|[?&])access_token=([^&#\s\"'<>]+)")


@dataclass(frozen=True)
class SecretFinding:
    path: str
    rule: str
    evidence: str


def load_openapi(path: Path = DEFAULT_OPENAPI_PATH) -> dict[str, Any]:
    try:
        schema = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"{path}: file not found") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"{path}: invalid YAML: {exc}") from exc

    if not isinstance(schema, dict):
        raise ValueError(f"{path}: expected a YAML object at document root")
    return schema


def _format_path(parts: tuple[str, ...]) -> str:
    if not parts:
        return "$"
    result = "$"
    for part in parts:
        if part.startswith("["):
            result += part
        else:
            result += f".{part}"
    return result


def _is_placeholder(value: str) -> bool:
    cleaned = value.strip().strip("\"'`")
    if cleaned in SAFE_LITERAL_VALUES:
        return True
    if cleaned and set(cleaned) <= {"*", "x", "X"}:
        return True

    lowered = cleaned.lower()
    return any(word in lowered for word in SAFE_PLACEHOLDER_WORDS)


def _redact(value: str) -> str:
    compact = " ".join(value.strip().split())
    if len(compact) <= 24:
        return compact
    return f"{compact[:10]}...{compact[-6:]}"


def _last_field_key(path: tuple[str, ...]) -> str | None:
    for part in reversed(path):
        if part.startswith("[") or part in EXAMPLE_SURFACE_KEYS:
            continue
        return part
    return None


def _sensitive_field_key(path: tuple[str, ...]) -> str | None:
    if _last_field_key(path) in {"description", "summary"}:
        return None

    for part in reversed(path):
        if part.startswith("[") or part in EXAMPLE_SURFACE_KEYS:
            continue
        normalized = part.lower().replace("-", "_")
        if normalized in SENSITIVE_FIELD_KEYS:
            return part
        if normalized.startswith(("mask_", "masked_", "has_")):
            return None
        if normalized.endswith(("_password", "_secret", "_token")):
            return part
    return None


def _query_values(value: str, query_key: str) -> list[str]:
    parsed = urlsplit(value)
    if not parsed.query:
        return []
    return [item_value for key, item_value in parse_qsl(parsed.query, keep_blank_values=True) if key == query_key]


def _credential_from_uri(value: str, schemes: tuple[str, ...]) -> str | None:
    parsed = urlsplit(value)
    if parsed.scheme not in schemes or "@" not in parsed.netloc:
        return None
    return parsed.password


def _detect_secret(value: str, path: tuple[str, ...]) -> list[tuple[str, str]]:
    findings: list[tuple[str, str]] = []

    for pattern in GITHUB_TOKEN_PATTERNS:
        for match in pattern.findall(value):
            if not _is_placeholder(match):
                findings.append(("github-token", match))

    for token in _query_values(value, "access_token"):
        if len(token) >= 8 and not _is_placeholder(token):
            findings.append(("webhook-access-token", token))

    for match in DINGTALK_SECRET_PATTERN.findall(value):
        if not _is_placeholder(match):
            findings.append(("webhook-secret", match))

    mongo_password = _credential_from_uri(value, ("mongodb", "mongodb+srv"))
    if mongo_password and not _is_placeholder(mongo_password):
        findings.append(("mongodb-uri-credential", mongo_password))

    redis_password = _credential_from_uri(value, ("redis", "rediss"))
    if redis_password and not _is_placeholder(redis_password):
        findings.append(("redis-uri-credential", redis_password))

    field_key = _sensitive_field_key(path)
    if field_key and len(value.strip()) >= 8 and not _is_placeholder(value):
        findings.append((f"sensitive-field:{field_key}", value))

    return findings


def _iter_text_values(
    value: Any,
    path: tuple[str, ...] = (),
    on_text_surface: bool = False,
) -> list[tuple[tuple[str, ...], str]]:
    values: list[tuple[tuple[str, ...], str]] = []

    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            child_path = (*path, key_text)
            child_surface = on_text_surface or key_text in TEXT_SURFACE_KEYS
            values.extend(_iter_text_values(child, child_path, child_surface))
        return values

    if isinstance(value, list):
        for index, child in enumerate(value):
            values.extend(_iter_text_values(child, (*path, f"[{index}]"), on_text_surface))
        return values

    if isinstance(value, str) and on_text_surface:
        values.append((path, value))
    return values


def scan_openapi(schema: dict[str, Any]) -> list[SecretFinding]:
    findings: list[SecretFinding] = []
    seen: set[tuple[str, str, str]] = set()

    for path, value in _iter_text_values(schema):
        for rule, evidence in _detect_secret(value, path):
            key = (_format_path(path), rule, evidence)
            if key in seen:
                continue
            seen.add(key)
            findings.append(SecretFinding(path=key[0], rule=rule, evidence=_redact(evidence)))

    return findings


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    parser = argparse.ArgumentParser(description="Scan docs/api/openapi.yaml for secret-like examples.")
    parser.add_argument(
        "--openapi",
        type=Path,
        default=DEFAULT_OPENAPI_PATH,
        help="OpenAPI YAML path. Defaults to docs/api/openapi.yaml.",
    )
    args = parser.parse_args(argv)

    try:
        schema = load_openapi(args.openapi)
    except ValueError as exc:
        configure_logging(stream=sys.stderr)
        logger.error(f"backend-openapi-secret-scan: {exc}")
        return 1

    findings = scan_openapi(schema)
    if findings:
        configure_logging(stream=sys.stderr)
        logger.error("backend-openapi-secret-scan: failed")
        for finding in findings:
            logger.error(f"- {finding.path}: {finding.rule} ({finding.evidence})")
        return 1

    logger.info("backend-openapi-secret-scan: ok (0 findings)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
