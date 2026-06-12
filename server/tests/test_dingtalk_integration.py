# coding: utf-8
# @File        : test_dingtalk_integration.py
# @Author      : NanMing
# @Date        : 2026/6/12 15:33
# @Description : Tests DingTalk notification integration behavior.

from urllib.parse import parse_qs, urlparse

import pytest

from integrations.dingtalk import (
    mask_dingtalk_webhook_url,
    prepare_dingtalk_webhook_url,
    sign_dingtalk_webhook_url,
)


def test_sign_dingtalk_webhook_url_adds_timestamp_and_sign():
    signed_url = sign_dingtalk_webhook_url(
        "https://oapi.dingtalk.com/robot/send?access_token=abc",
        "SEC000000",
        timestamp=1710000000000,
    )

    parsed = urlparse(signed_url)
    query = parse_qs(parsed.query)

    assert parsed.scheme == "https"
    assert parsed.netloc == "oapi.dingtalk.com"
    assert query["access_token"] == ["abc"]
    assert query["timestamp"] == ["1710000000000"]
    assert query["sign"] == ["BXeeRWh7T4PkibaXvZRpazMMqxx74szvpNeRFb96HFA="]


def test_prepare_dingtalk_webhook_url_requires_dingtalk_and_secret():
    dingtalk_url = "https://oapi.dingtalk.com/robot/send?access_token=abc"
    unsupported_url = "https://example.com/webhook"

    with pytest.raises(ValueError, match="secret is required"):
        prepare_dingtalk_webhook_url(dingtalk_url, "")

    with pytest.raises(ValueError, match="Only DingTalk webhook is supported"):
        prepare_dingtalk_webhook_url(unsupported_url, "SEC000000")


def test_mask_dingtalk_webhook_url_masks_sensitive_query_values():
    webhook = "https://oapi.dingtalk.com/robot/send?access_token=abc&foo=bar"

    assert mask_dingtalk_webhook_url(webhook) == (
        "https://oapi.dingtalk.com/robot/send?access_token=***&foo=bar"
    )
