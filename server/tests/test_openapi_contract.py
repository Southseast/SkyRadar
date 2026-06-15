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
EXPECTED_RUNTIME_PATHS = {
    "/api/v1/health",
    "/api/v1/openapi.json",
    "/api/v1/docs",
    "/api/v1/leakages",
    "/api/v1/leakages/{leakage_id}",
    "/api/v1/leakages/{leakage_id}/code",
    "/api/v1/trends",
    "/api/v1/statistics",
    "/api/v1/github-accounts",
    "/api/v1/github-accounts/{username}",
    "/api/v1/search-rules",
    "/api/v1/search-rules/{tag}",
    "/api/v1/task-schedules/current",
    "/api/v1/blacklist-items",
    "/api/v1/blacklist-items/{text:path}",
    "/api/v1/notification-recipients",
    "/api/v1/notification-recipients/{mail}",
    "/api/v1/mail-settings/current",
    "/api/v1/webhooks",
    "/api/v1/webhooks/{webhook_id}",
    "/api/v1/webhook-tests",
}


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
    assert schema["info"]["title"] == "SkyRadar REST API"
    assert isinstance(schema["paths"], dict)
    assert schema["paths"]


def test_registered_api_paths_match_final_rest_v1_contract():
    registered_paths = _registered_api_paths()

    assert registered_paths == EXPECTED_RUNTIME_PATHS
