#!/usr/bin/env python3
# coding: utf-8
# @File        : backend_route_coverage.py
# @Author      : NanMing
# @Date        : 2026/6/11 13:54
# @Description : Check that the final /api/v1 OpenAPI contract is path-scoped.

"""Check that the final /api/v1 OpenAPI contract is path-scoped.

The hand-maintained OpenAPI file documents the final REST contract. Runtime
routes may lag while implementation work is split across workers, so the
default check no longer requires current unversioned routes to appear in the
contract. Use ``--check-registered-v1`` when v1 runtime routes exist and should
be compared against the contract.
"""

from __future__ import annotations

from loguru import logger

import argparse
import ast
import re
import sys
from pathlib import Path

import yaml



def configure_logging():
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{message}")


DEFAULT_OPENAPI_PATH = Path("docs/api/openapi.yaml")
DEFAULT_API_ROUTES_ROOT = Path("server/api")
FASTAPI_PATH_CONVERTER_PATTERN = re.compile(r"\{([^{}:]+):[^{}]+\}")


def load_openapi_paths(path: Path = DEFAULT_OPENAPI_PATH) -> set[str]:
    try:
        schema = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"{path}: file not found") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"{path}: invalid YAML: {exc}") from exc

    if not isinstance(schema, dict) or not isinstance(schema.get("paths"), dict):
        raise ValueError(f"{path}: expected OpenAPI document with paths object")
    return set(schema["paths"])


def normalize_path_template(path: str) -> str:
    return FASTAPI_PATH_CONVERTER_PATTERN.sub(r"{\1}", path)


def _literal_strings(args: list[ast.AST]) -> list[str]:
    values: list[str] = []
    for arg in args:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            values.append(arg.value)
    return values


def _is_method_on(call: ast.AST, object_names: set[str], names: set[str]) -> bool:
    return (
        isinstance(call, ast.Attribute)
        and call.attr in names
        and isinstance(call.value, ast.Name)
        and call.value.id in object_names
    )


def _registered_paths_from_module(path: Path) -> set[str]:
    routes: set[str] = set()
    try:
        module = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        raise ValueError(f"{path}: invalid Python syntax: {exc}") from exc

    for node in ast.walk(module):
        if not isinstance(node, ast.Call):
            continue
        call = node.func
        if _is_method_on(call, {"app", "api", "router"}, {"get", "post", "patch", "delete", "put"}):
            for route in _literal_strings(node.args[:1]):
                if route.startswith("/api/v1/"):
                    routes.add(normalize_path_template(route))
            continue

        if _is_method_on(call, {"app", "api", "router"}, {"add_api_route"}):
            for route in _literal_strings(node.args[:1]):
                if route.startswith("/api/v1/"):
                    routes.add(normalize_path_template(route))

    return routes


def registered_api_paths(path: Path = DEFAULT_API_ROUTES_ROOT) -> set[str]:
    if path.is_file():
        return _registered_paths_from_module(path)
    if not path.exists():
        raise ValueError(f"{path}: file not found")
    if not path.is_dir():
        raise ValueError(f"{path}: expected file or directory")

    routes: set[str] = set()
    for route_module in sorted(path.glob("*/routes.py")):
        routes.update(_registered_paths_from_module(route_module))
    return routes


def check_route_coverage(
    openapi_paths: set[str],
    registered_paths: set[str],
    *,
    check_registered_v1: bool = False,
) -> list[str]:
    errors: list[str] = []
    non_v1_paths = sorted(path for path in openapi_paths if not path.startswith("/api/v1/"))
    if non_v1_paths:
        errors.append("OpenAPI contains non-/api/v1 paths: " + ", ".join(non_v1_paths))

    if not check_registered_v1:
        return errors

    missing = sorted(registered_paths - openapi_paths)
    if missing:
        errors.append("registered /api/v1 paths missing from OpenAPI: " + ", ".join(missing))
    return errors


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    parser = argparse.ArgumentParser(description="Validate final /api/v1 OpenAPI path scope.")
    parser.add_argument("--openapi", type=Path, default=DEFAULT_OPENAPI_PATH)
    parser.add_argument("--api-registry", type=Path, default=DEFAULT_API_ROUTES_ROOT)
    parser.add_argument(
        "--check-registered-v1",
        action="store_true",
        help="Also require registered /api/v1 runtime routes to be present in OpenAPI.",
    )
    args = parser.parse_args(argv)

    try:
        openapi_paths = load_openapi_paths(args.openapi)
        routes = registered_api_paths(args.api_registry)
    except ValueError as exc:
        logger.error(f"backend-route-coverage: {exc}")
        return 1

    errors = check_route_coverage(
        openapi_paths,
        routes,
        check_registered_v1=args.check_registered_v1,
    )
    if errors:
        logger.error("backend-route-coverage: failed")
        for error in errors:
            logger.error(f"- {error}")
        return 1

    if args.check_registered_v1:
        logger.info(f"backend-route-coverage: ok ({len(routes)} registered /api/v1 routes covered)")
    else:
        logger.info(f"backend-route-coverage: ok ({len(openapi_paths)} final /api/v1 paths)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
