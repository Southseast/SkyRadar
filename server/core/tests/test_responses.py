# coding: utf-8
# @File        : test_responses.py
# @Author      : NanMing
# @Date        : 2026/6/9 14:55
# @Description : Tests API response helper payload shapes.

import json
from datetime import datetime, timezone


def test_api_payload_preserves_status_msg_result_shape():
    from core.responses import api_payload

    assert api_payload([{"tag": "github-token"}]) == {
        "status": 200,
        "msg": "获取信息成功",
        "result": [{"tag": "github-token"}],
    }
    assert list(api_payload([{"tag": "github-token"}])) == ["status", "msg", "result"]


def test_api_payload_allows_business_statuses_messages_and_extra_fields():
    from core.responses import api_payload

    payload = api_payload(
        [],
        status=404,
        msg="删除成功",
        total=0,
        generated_at=datetime(2026, 6, 9, 10, 30, tzinfo=timezone.utc),
    )

    assert payload == {
        "status": 404,
        "msg": "删除成功",
        "result": [],
        "total": 0,
        "generated_at": "2026-06-09T10:30:00+00:00",
    }
    assert list(payload) == ["status", "msg", "result", "total", "generated_at"]


def test_fastapi_response_keeps_body_status_separate_from_http_status():
    from core.responses import fastapi_response

    response = fastapi_response([], status=404, msg="删除成功")

    assert response.status_code == 200
    assert json.loads(response.body) == {"status": 404, "msg": "删除成功", "result": []}


def test_fastapi_response_allows_explicit_http_status():
    from core.responses import fastapi_response

    response = fastapi_response([], status=404, msg="API docs disabled", http_status=404)

    assert response.status_code == 404
