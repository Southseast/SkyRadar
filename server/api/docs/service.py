# coding: utf-8
# @File        : service.py
# @Author      : NanMing
# @Date        : 2026/6/10 13:33
# @Description : Loads and exposes the OpenAPI documentation contract.

import yaml

from core.config import get_settings


SWAGGER_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>SkyRadar API Docs</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>
    window.onload = function () {
      window.ui = SwaggerUIBundle({
        url: "/api/openapi.json",
        dom_id: "#swagger-ui",
      });
    };
  </script>
</body>
</html>
"""


def api_docs_enabled():
    return get_settings().api_docs_enabled


def load_openapi_schema():
    with get_settings().openapi_path.open(encoding="utf-8") as schema_file:
        return yaml.safe_load(schema_file)
