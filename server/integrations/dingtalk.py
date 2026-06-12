# coding: utf-8
# @File        : dingtalk.py
# @Author      : NanMing
# @Date        : 2026/6/12 15:38
# @Description : Signs and sends DingTalk webhook requests.

import base64
import hashlib
import hmac
import time
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests


SENSITIVE_WEBHOOK_QUERY_KEYS = {
    "access_token",
    "secret",
    "sign",
    "signature",
    "timestamp",
    "token",
}


def is_dingtalk_webhook(webhook):
    return urlparse(webhook).netloc == "oapi.dingtalk.com"


def mask_dingtalk_webhook_url(webhook):
    if not webhook:
        return webhook
    parsed = urlparse(webhook)
    query = parse_qsl(parsed.query, keep_blank_values=True)
    if not query:
        return webhook
    masked_query = [
        (key, "***" if key.lower() in SENSITIVE_WEBHOOK_QUERY_KEYS else value)
        for key, value in query
    ]
    return urlunparse(parsed._replace(query=urlencode(masked_query, safe="*")))


def sign_dingtalk_webhook_url(webhook, secret, timestamp=None):
    if not secret:
        raise ValueError("DingTalk webhook secret is required")

    timestamp = str(timestamp or round(time.time() * 1000))
    string_to_sign = "{}\n{}".format(timestamp, secret)
    hmac_code = hmac.new(
        secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    sign = base64.b64encode(hmac_code).decode("utf-8")

    parsed = urlparse(webhook)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["timestamp"] = timestamp
    query["sign"] = sign
    return urlunparse(parsed._replace(query=urlencode(query)))


def prepare_dingtalk_webhook_url(webhook, secret):
    if not is_dingtalk_webhook(webhook):
        raise ValueError("Only DingTalk webhook is supported")
    return sign_dingtalk_webhook_url(webhook, secret)


def post_dingtalk_webhook(webhook, secret, payload, timeout=10):
    return requests.post(
        prepare_dingtalk_webhook_url(webhook, secret),
        json=payload,
        timeout=timeout,
    )
