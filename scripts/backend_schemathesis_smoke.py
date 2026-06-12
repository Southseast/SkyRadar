#!/usr/bin/env python3
# coding: utf-8
# @File        : backend_schemathesis_smoke.py
# @Author      : NanMing
# @Date        : 2026/6/8 14:06
# @Description : Run a read-only Schemathesis smoke against the SkyRadar OpenAPI contract.

"""Run a read-only Schemathesis smoke against the SkyRadar OpenAPI contract."""

from __future__ import annotations

from loguru import logger

import argparse
import copy
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml



def configure_logging():
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{message}")


DEFAULT_OPENAPI_PATH = Path("docs/api/openapi.yaml")
DEFAULT_BASE_URL = "http://127.0.0.1"

HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}
READ_ONLY_METHOD = "get"
PATH_ITEM_FIELDS = {"summary", "description", "servers", "parameters"}
LEAKAGE_STATUS_SMOKE_VALUE = '{"security":0,"ignore":0}'


def load_openapi(path: Path) -> dict[str, Any]:
    try:
        schema = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"{path}: file not found") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"{path}: invalid YAML: {exc}") from exc

    if not isinstance(schema, dict):
        raise ValueError(f"{path}: expected a YAML object at document root")
    if not isinstance(schema.get("paths"), dict):
        raise ValueError(f"{path}: expected OpenAPI document with paths object")
    return schema


def filter_read_only_get_schema(schema: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Return a copy of the schema that exposes only GET operations."""
    filtered = copy.deepcopy(schema)
    filtered_paths: dict[str, Any] = {}
    operations: list[str] = []

    for path, path_item in schema.get("paths", {}).items():
        if not isinstance(path_item, dict) or READ_ONLY_METHOD not in path_item:
            continue

        filtered_path_item: dict[str, Any] = {}
        for key, value in path_item.items():
            if key in PATH_ITEM_FIELDS or key.startswith("x-"):
                filtered_path_item[key] = copy.deepcopy(value)
            elif key == READ_ONLY_METHOD:
                filtered_path_item[key] = copy.deepcopy(value)
            elif key in HTTP_METHODS:
                continue
            else:
                filtered_path_item[key] = copy.deepcopy(value)

        filtered_paths[path] = filtered_path_item
        operations.append(f"GET {path}")

    if not filtered_paths:
        raise ValueError("OpenAPI document does not contain any GET operations")

    filtered["paths"] = filtered_paths
    constrain_read_only_smoke_inputs(filtered)
    return filtered, operations


def constrain_read_only_smoke_inputs(schema: dict[str, Any]) -> None:
    """Constrain open string inputs to safe examples in the smoke schema."""
    leakage_status_parameter = {
        "name": "status",
        "in": "query",
        "required": True,
        "description": "Smoke-safe JSON string for the leakage status filter.",
        "schema": {
            "type": "string",
            "enum": [LEAKAGE_STATUS_SMOKE_VALUE],
        },
        "example": LEAKAGE_STATUS_SMOKE_VALUE,
    }
    parameters = schema.get("components", {}).get("parameters", {})
    leakage_status = parameters.get("LeakageStatusQuery")
    if isinstance(leakage_status, dict):
        leakage_status.clear()
        leakage_status.update(copy.deepcopy(leakage_status_parameter))

    leakage_get = schema.get("paths", {}).get("/api/leakage", {}).get("get")
    if not isinstance(leakage_get, dict):
        return
    normalized_parameters = []
    for parameter in leakage_get.get("parameters", []):
        if parameter == {"$ref": "#/components/parameters/LeakageStatusQuery"}:
            normalized_parameters.append(copy.deepcopy(leakage_status_parameter))
        else:
            normalized_parameters.append(parameter)
    leakage_get["parameters"] = normalized_parameters


def find_schemathesis_cli() -> str | None:
    for executable in ("schemathesis", "st"):
        path = shutil.which(executable)
        if path:
            return path
    return None


def build_command(cli: str, openapi_path: Path, base_url: str) -> list[str]:
    return [
        cli,
        "run",
        str(openapi_path),
        "--url",
        base_url,
        "--phases=fuzzing",
        "--mode=positive",
        "--max-examples=1",
        "--generation-deterministic",
        "--checks=status_code_conformance,response_schema_conformance",
    ]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run Schemathesis against a temporary OpenAPI file that contains only "
            "read-only GET operations."
        )
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("SKYRADAR_BASE_URL", DEFAULT_BASE_URL),
        help="Backend base URL, default: %(default)s",
    )
    parser.add_argument(
        "--openapi",
        type=Path,
        default=DEFAULT_OPENAPI_PATH,
        help="OpenAPI YAML path, default: docs/api/openapi.yaml.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build the read-only schema and print the planned command without running Schemathesis.",
    )
    return parser.parse_args(argv)


def write_filtered_schema(path: Path, schema: dict[str, Any]) -> None:
    path.write_text(
        yaml.safe_dump(schema, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    args = parse_args(argv)

    try:
        schema = load_openapi(args.openapi)
        filtered_schema, operations = filter_read_only_get_schema(schema)
    except ValueError as exc:
        logger.error(f"backend-schemathesis-smoke: {exc}")
        return 1

    if args.dry_run:
        command = build_command("schemathesis", Path("<temp-readonly-openapi.yaml>"), args.base_url)
        logger.info(
            "backend-schemathesis-smoke: dry-run ok "
            f"({len(operations)} GET operations)"
        )
        logger.info("Command: " + " ".join(command))
        for operation in operations:
            logger.info(f"- {operation}")
        return 0

    cli = find_schemathesis_cli()
    if cli is None:
        logger.error(
            "backend-schemathesis-smoke: Schemathesis CLI not found. "
            "Run through uv with "
            "`uv run --no-project --with-requirements deploy/pyenv/requirements-dev.txt python scripts/backend_schemathesis_smoke.py`.",
        )
        return 1

    with tempfile.TemporaryDirectory(prefix="skyradar-schemathesis-") as temp_dir:
        filtered_path = Path(temp_dir) / "openapi-readonly.yaml"
        write_filtered_schema(filtered_path, filtered_schema)
        command = build_command(cli, filtered_path, args.base_url)
        logger.info(
            "backend-schemathesis-smoke: running "
            f"{len(operations)} GET operations with positive fuzzing smoke"
        )
        return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
