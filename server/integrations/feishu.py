# coding: utf-8
# @File        : feishu.py
# @Author      : NanMing
# @Date        : 2026/6/12 15:34
# @Description : Builds and sends Feishu webhook notification payloads.

import base64
import hashlib
import hmac
import time
from urllib.parse import urlparse, urlunparse

import requests


TEXT_MAX_LENGTH = 20 * 1024


def _truncate(value, limit):
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    if limit <= 3:
        return text[:limit]
    return text[: limit - 3] + "..."


def _dashboard_url(hostname, tag):
    if not hostname:
        return ""
    return "{}/?tag={}".format(str(hostname).rstrip("/"), str(tag))


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


def build_feishu_text_payload(text, secret=None, timestamp=None):
    text = _truncate(text, TEXT_MAX_LENGTH) or "SkyRadar 通知"
    payload = {
        "msg_type": "text",
        "content": {"text": text},
    }
    if secret:
        timestamp, sign = sign_feishu_payload(secret, timestamp)
        payload["timestamp"] = timestamp
        payload["sign"] = sign
    return payload


def build_feishu_test_payload(domain, secret=None):
    lines = [
        "SkyRadar 通知测试",
        "类型: 飞书 webhook",
        "状态: 配置可用",
    ]
    if domain:
        lines.append("控制台: {}".format(domain))
    return build_feishu_text_payload("\n".join(lines), secret=secret)


def build_feishu_search_notice_payload(tag, results, hostname, secret=None):
    result_lines = [str(result).strip() for result in results if str(result).strip()]
    dashboard_url = _dashboard_url(hostname, tag)
    lines = [
        "SkyRadar 监控告警",
        "规则名称: {}".format(tag),
        "命中数量: {}".format(len(result_lines)),
    ]
    if dashboard_url:
        lines.append("控制台: {}".format(dashboard_url))
    lines.extend(["", "命中结果:"])

    added = 0
    for index, result in enumerate(result_lines):
        remaining = len(result_lines) - index - 1
        suffix = "\n还有 {} 条，请在 SkyRadar 查看完整结果。".format(remaining) if remaining else ""
        candidate = "\n".join(lines + ["- {}".format(result)]) + suffix
        if len(candidate) <= TEXT_MAX_LENGTH:
            lines.append("- {}".format(result))
            added += 1
            continue
        break

    omitted = len(result_lines) - added
    if omitted:
        lines.append("还有 {} 条，请在 SkyRadar 查看完整结果。".format(omitted))
    return build_feishu_text_payload("\n".join(lines), secret=secret)


def post_feishu_text(webhook, secret, content, timeout=10):
    if not is_feishu_webhook(webhook):
        raise ValueError("Only Feishu webhook is supported")
    return requests.post(webhook, json=content, timeout=timeout)
