#!/usr/bin/env python3
# coding: utf-8
# @File        : backend_route_coverage.py
# @Author      : NanMing
# @Date        : 2026/6/11 13:54
# @Description : Check that backend /api routes are documented in OpenAPI.

"""Check that backend /api routes are documented in OpenAPI."""

from __future__ import annotations

from loguru import logger

import argparse
import ast
import sys
from pathlib import Path

import yaml



def configure_logging():
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{message}")


DEFAULT_OPENAPI_PATH = Path("docs/api/openapi.yaml")
DEFAULT_API_ROUTES_ROOT = Path("server/api")


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
                if route.startswith("/api/"):
                    routes.add(route)
            continue

        if _is_method_on(call, {"app", "api", "router"}, {"add_api_route"}):
            for route in _literal_strings(node.args[:1]):
                if route.startswith("/api/"):
                    routes.add(route)

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


def check_route_coverage(openapi_paths: set[str], registered_paths: set[str]) -> list[str]:
    errors: list[str] = []
    if not registered_paths:
        errors.append("server/api did not register any /api/* routes")

    missing = sorted(registered_paths - openapi_paths)
    extra = sorted(openapi_paths - registered_paths)
    if missing:
        errors.append("missing OpenAPI paths: " + ", ".join(missing))
    if extra:
        errors.append("OpenAPI paths not registered in server/api routes: " + ", ".join(extra))
    return errors


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    parser = argparse.ArgumentParser(description="Compare backend API routes with OpenAPI paths.")
    parser.add_argument("--openapi", type=Path, default=DEFAULT_OPENAPI_PATH)
    parser.add_argument("--api-registry", type=Path, default=DEFAULT_API_ROUTES_ROOT)
    args = parser.parse_args(argv)

    try:
        openapi_paths = load_openapi_paths(args.openapi)
        routes = registered_api_paths(args.api_registry)
    except ValueError as exc:
        logger.error(f"backend-route-coverage: {exc}")
        return 1

    errors = check_route_coverage(openapi_paths, routes)
    if errors:
        logger.error("backend-route-coverage: failed")
        for error in errors:
            logger.error(f"- {error}")
        return 1

    logger.info(f"backend-route-coverage: ok ({len(routes)} /api routes covered)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
