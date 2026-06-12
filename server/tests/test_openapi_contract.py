# coding: utf-8
# @File        : test_openapi_contract.py
# @Author      : NanMing
# @Date        : 2026/6/9 15:21
# @Description : Tests OpenAPI contract integrity.

import ast
from pathlib import Path

import yaml


OPENAPI_PATH = Path("docs/api/openapi.yaml")
API_ROUTES_ROOT = Path("server/api")


def _registered_api_paths():
    paths = set()

    for path in API_ROUTES_ROOT.glob("*/routes.py"):
        module = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(module):
            if not isinstance(node, ast.Call):
                continue
            call = node.func
            if (
                isinstance(call, ast.Attribute)
                and isinstance(call.value, ast.Name)
                and call.value.id == "router"
                and call.attr in {"get", "post", "patch", "delete", "put"}
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                paths.add(node.args[0].value)

    return paths


def test_openapi_yaml_is_parseable():
    schema = yaml.safe_load(OPENAPI_PATH.read_text(encoding="utf-8"))

    assert schema["openapi"].startswith("3.")
    assert schema["info"]["title"] == "SkyRadar Backend API"
    assert isinstance(schema["paths"], dict)
    assert schema["paths"]


def test_openapi_paths_cover_api_registry():
    schema = yaml.safe_load(OPENAPI_PATH.read_text(encoding="utf-8"))
    openapi_paths = set(schema["paths"])
    registered_paths = _registered_api_paths()

    assert registered_paths
    assert registered_paths <= openapi_paths
