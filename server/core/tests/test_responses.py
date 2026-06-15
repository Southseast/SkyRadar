# coding: utf-8
# @File        : test_responses.py
# @Author      : NanMing
# @Date        : 2026/6/9 14:55
# @Description : Tests API response helper payload shapes.

from datetime import datetime, timezone
import json


def test_jsonable_normalizes_nested_api_values():
    from core.responses import jsonable

    assert jsonable(
        {
            "items": ({"tag": "github-token"},),
            "generated_at": datetime(2026, 6, 9, 10, 30, tzinfo=timezone.utc),
        }
    ) == {
        "items": [{"tag": "github-token"}],
        "generated_at": "2026-06-09T10:30:00+00:00",
    }


def test_json_response_returns_raw_json_body():
    from core.responses import json_response

    response = json_response({"openapi": "3.0.3"}, status_code=200)

    assert response.status_code == 200
    assert json.loads(response.body) == {"openapi": "3.0.3"}


def test_rest_payload_uses_data_meta_links_shape():
    from core.responses import rest_payload

    payload = rest_payload(
        [{"tag": "github-token"}],
        meta={"total": 1, "page": 1, "page_size": 20},
        links={"self": "/api/v1/leakages?page=1&page_size=20"},
    )

    assert payload == {
        "data": [{"tag": "github-token"}],
        "meta": {"total": 1, "page": 1, "page_size": 20},
        "links": {"self": "/api/v1/leakages?page=1&page_size=20"},
    }
    assert list(payload) == ["data", "meta", "links"]


def test_rest_error_response_uses_error_message_shape():
    from core.responses import rest_error_response

    response = rest_error_response(
        "not_found",
        "Resource not found",
        status_code=404,
        detail={"id": "missing"},
    )

    assert response.status_code == 404
    assert json.loads(response.body) == {
        "error": "not_found",
        "message": "Resource not found",
        "detail": {"id": "missing"},
    }
