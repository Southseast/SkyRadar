# coding: utf-8
# @File        : feishu.py
# @Author      : NanMing
# @Date        : 2026/6/12 15:34
# @Description : Signs and sends Feishu webhook requests.

import base64
import hashlib
import hmac
import time
from urllib.parse import urlparse, urlunparse

import requests


def is_feishu_webhook(webhook):
    parsed = urlparse(webhook)
    return parsed.scheme == "https" and parsed.netloc == "open.feishu.cn" and parsed.path.startswith("/open-apis/bot/v2/hook/")


def mask_feishu_webhook_url(webhook):
    if not webhook:
        return webhook
    parsed = urlparse(webhook)
    parts = parsed.path.rstrip("/").split("/")
    if not parts:
        return webhook
    parts[-1] = "***"
    return urlunparse(parsed._replace(path="/".join(parts)))


def sign_feishu_payload(secret, timestamp=None):
    if not secret:
        raise ValueError("Feishu webhook secret is required")

    timestamp = str(timestamp or int(time.time()))
    string_to_sign = "{}\n{}".format(timestamp, secret)
    hmac_code = hmac.new(
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    return timestamp, base64.b64encode(hmac_code).decode("utf-8")


def prepare_feishu_payload(payload, secret, timestamp=None):
    timestamp, sign = sign_feishu_payload(secret, timestamp)
    return {**payload, "timestamp": timestamp, "sign": sign}


def post_feishu_webhook(webhook, secret, payload, timeout=10):
    if not is_feishu_webhook(webhook):
        raise ValueError("Only Feishu webhook is supported")
    return requests.post(webhook, json=prepare_feishu_payload(payload, secret), timeout=timeout)
