#!/usr/bin/env python3
# coding: utf-8
# @File        : backend_openapi_check.py
# @Author      : NanMing
# @Date        : 2026/6/10 17:41
# @Description : Validate the hand-maintained SkyRadar OpenAPI contract.

"""Validate the hand-maintained SkyRadar OpenAPI contract."""

from __future__ import annotations

from loguru import logger

import argparse
import re
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import yaml



def configure_logging():
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{message}")


DEFAULT_OPENAPI_PATH = Path("docs/api/openapi.yaml")

HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}
PATH_ITEM_FIELDS = {"summary", "description", "servers", "parameters"}
PARAMETER_LOCATIONS = {"query", "header", "path", "cookie"}
STATUS_CODE_PATTERN = re.compile(r"^[1-5][0-9][0-9]$")
OPENAPI_3_PATTERN = re.compile(r"^3\.0(\.\d+)?$")


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


def _add_error(errors: list[str], location: str, message: str) -> None:
    errors.append(f"{location}: {message}")


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _local_ref_target_exists(schema: dict[str, Any], ref: str) -> bool:
    if not ref.startswith("#/"):
        return True

    current: Any = schema
    for raw_part in ref[2:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or part not in current:
            return False
        current = current[part]
    return True


def _iter_refs(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        ref = value.get("$ref")
        if isinstance(ref, str):
            yield ref
        for child in value.values():
            yield from _iter_refs(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_refs(child)


def _validate_parameter(parameter: Any, location: str, errors: list[str]) -> None:
    if isinstance(parameter, dict) and "$ref" in parameter:
        return
    if not isinstance(parameter, dict):
        _add_error(errors, location, "parameter must be an object or $ref")
        return

    name = parameter.get("name")
    param_in = parameter.get("in")
    if not _is_non_empty_string(name):
        _add_error(errors, location, "parameter.name must be a non-empty string")
    if param_in not in PARAMETER_LOCATIONS:
        _add_error(errors, location, "parameter.in must be query/header/path/cookie")
    if param_in == "path" and parameter.get("required") is not True:
        _add_error(errors, location, "path parameters must set required: true")
    if "schema" not in parameter and "content" not in parameter:
        _add_error(errors, location, "parameter must define schema or content")


def _validate_response(response: Any, location: str, errors: list[str]) -> None:
    if isinstance(response, dict) and "$ref" in response:
        return
    if not isinstance(response, dict):
        _add_error(errors, location, "response must be an object or $ref")
        return
    if not _is_non_empty_string(response.get("description")):
        _add_error(errors, location, "response.description is required")

    content = response.get("content")
    if content is None:
        return
    if not isinstance(content, dict) or not content:
        _add_error(errors, location, "response.content must be a non-empty object when present")
        return
    for media_type, media_value in content.items():
        media_location = f"{location}.content.{media_type}"
        if not _is_non_empty_string(media_type):
            _add_error(errors, media_location, "media type must be a non-empty string")
        if not isinstance(media_value, dict):
            _add_error(errors, media_location, "media type value must be an object")


def _validate_operation(
    operation: Any,
    location: str,
    operation_ids: dict[str, str],
    errors: list[str],
) -> None:
    if not isinstance(operation, dict):
        _add_error(errors, location, "operation must be an object")
        return

    operation_id = operation.get("operationId")
    if not _is_non_empty_string(operation_id):
        _add_error(errors, location, "operationId is required")
    elif operation_id in operation_ids:
        _add_error(errors, location, f"duplicate operationId also used at {operation_ids[operation_id]}")
    else:
        operation_ids[operation_id] = location

    parameters = operation.get("parameters", [])
    if not isinstance(parameters, list):
        _add_error(errors, f"{location}.parameters", "parameters must be an array")
    else:
        seen_parameters: set[tuple[str, str]] = set()
        for index, parameter in enumerate(parameters):
            parameter_location = f"{location}.parameters[{index}]"
            _validate_parameter(parameter, parameter_location, errors)
            if isinstance(parameter, dict) and "$ref" not in parameter:
                key = (parameter.get("name"), parameter.get("in"))
                if all(isinstance(part, str) for part in key):
                    if key in seen_parameters:
                        _add_error(errors, parameter_location, "duplicate parameter name/in pair")
                    seen_parameters.add(key)

    request_body = operation.get("requestBody")
    if request_body is not None and not isinstance(request_body, dict):
        _add_error(errors, f"{location}.requestBody", "requestBody must be an object or $ref")
    elif isinstance(request_body, dict) and "$ref" not in request_body:
        content = request_body.get("content")
        if not isinstance(content, dict) or not content:
            _add_error(errors, f"{location}.requestBody", "requestBody.content must be a non-empty object")

    responses = operation.get("responses")
    if not isinstance(responses, dict) or not responses:
        _add_error(errors, location, "responses is required and must be a non-empty object")
        return

    for status_code, response in responses.items():
        response_location = f"{location}.responses.{status_code}"
        if status_code != "default" and not STATUS_CODE_PATTERN.match(str(status_code)):
            _add_error(errors, response_location, "response key must be an HTTP status code or default")
        _validate_response(response, response_location, errors)


def validate_openapi(schema: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    openapi_version = schema.get("openapi")
    if not isinstance(openapi_version, str) or not OPENAPI_3_PATTERN.match(openapi_version):
        _add_error(errors, "openapi", "must be an OpenAPI 3.0.x version string")

    info = schema.get("info")
    if not isinstance(info, dict):
        _add_error(errors, "info", "is required and must be an object")
    else:
        if not _is_non_empty_string(info.get("title")):
            _add_error(errors, "info.title", "is required")
        if not _is_non_empty_string(info.get("version")):
            _add_error(errors, "info.version", "is required")

    paths = schema.get("paths")
    if not isinstance(paths, dict) or not paths:
        _add_error(errors, "paths", "is required and must be a non-empty object")
    else:
        operation_ids: dict[str, str] = {}
        for path, path_item in paths.items():
            path_location = f"paths.{path}"
            if not isinstance(path, str) or not path.startswith("/api/"):
                _add_error(errors, path_location, "SkyRadar API paths must start with /api/")
            if not isinstance(path_item, dict):
                _add_error(errors, path_location, "path item must be an object")
                continue

            operations = [key for key in path_item if key in HTTP_METHODS]
            if not operations:
                _add_error(errors, path_location, "path item must define at least one operation")

            path_parameters = path_item.get("parameters", [])
            if path_parameters and not isinstance(path_parameters, list):
                _add_error(errors, f"{path_location}.parameters", "parameters must be an array")

            for key in path_item:
                if key not in HTTP_METHODS and key not in PATH_ITEM_FIELDS and not key.startswith("x-"):
                    _add_error(errors, f"{path_location}.{key}", "unknown path item field")
            for method in operations:
                _validate_operation(path_item[method], f"{path_location}.{method}", operation_ids, errors)

    components = schema.get("components")
    if not isinstance(components, dict):
        _add_error(errors, "components", "is required and must be an object")
    else:
        schemas = components.get("schemas")
        if not isinstance(schemas, dict) or not schemas:
            _add_error(errors, "components.schemas", "is required and must be a non-empty object")
        parameters = components.get("parameters")
        if parameters is not None and not isinstance(parameters, dict):
            _add_error(errors, "components.parameters", "must be an object when present")

    for ref in _iter_refs(schema):
        if not _local_ref_target_exists(schema, ref):
            _add_error(errors, "$ref", f"unresolved local reference {ref}")

    return errors


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    parser = argparse.ArgumentParser(description="Validate docs/api/openapi.yaml structure.")
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
        logger.error(f"backend-openapi-check: {exc}")
        return 1

    errors = validate_openapi(schema)
    if errors:
        logger.error("backend-openapi-check: failed")
        for error in errors:
            logger.error(f"- {error}")
        return 1

    paths = schema.get("paths", {})
    operations = sum(
        1
        for path_item in paths.values()
        if isinstance(path_item, dict)
        for key in path_item
        if key in HTTP_METHODS
    )
    logger.info(f"backend-openapi-check: ok ({len(paths)} paths, {operations} operations)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
