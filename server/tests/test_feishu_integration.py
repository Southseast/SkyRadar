# coding: utf-8
# @File        : test_feishu_integration.py
# @Author      : NanMing
# @Date        : 2026/6/12 15:32
# @Description : Tests Feishu webhook integration helpers.

import base64
import hashlib
import hmac

from integrations.feishu import (
    build_feishu_text_payload,
    is_feishu_webhook,
    mask_feishu_webhook_url,
    sign_feishu_payload,
)


def test_is_feishu_webhook_requires_official_hook_url():
    assert is_feishu_webhook("https://open.feishu.cn/open-apis/bot/v2/hook/example")
    assert not is_feishu_webhook("https://open.feishu.cn/open-apis/other/example")
    assert not is_feishu_webhook("http://open.feishu.cn/open-apis/bot/v2/hook/example")


def test_mask_feishu_webhook_url_masks_hook_token():
    assert (
        mask_feishu_webhook_url("https://open.feishu.cn/open-apis/bot/v2/hook/example-token")
        == "https://open.feishu.cn/open-apis/bot/v2/hook/***"
    )


def test_sign_feishu_payload_matches_documented_hmac_sha256():
    timestamp, sign = sign_feishu_payload("demo", timestamp=1599360473)
    expected = base64.b64encode(
        hmac.new("1599360473\ndemo".encode("utf-8"), digestmod=hashlib.sha256).digest()
    ).decode("utf-8")

    assert timestamp == "1599360473"
    assert sign == expected


def test_build_feishu_text_payload_adds_signature_when_secret_is_set():
    payload = build_feishu_text_payload("request example", secret="demo", timestamp=1599360473)

    assert payload["msg_type"] == "text"
    assert payload["content"] == {"text": "request example"}
    assert payload["timestamp"] == "1599360473"
    assert payload["sign"]
