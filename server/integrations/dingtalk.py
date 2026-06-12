# coding: utf-8
# @File        : dingtalk.py
# @Author      : NanMing
# @Date        : 2026/6/12 15:38
# @Description : Builds and sends DingTalk notification payloads.

import base64
import hashlib
import hmac
import time
from urllib.parse import parse_qsl, quote, urlencode, urlparse, urlunparse

import requests


MARKDOWN_TITLE_MAX_LENGTH = 30
MARKDOWN_TEXT_MAX_LENGTH = 500
SENSITIVE_WEBHOOK_QUERY_KEYS = {
    "access_token",
    "secret",
    "sign",
    "signature",
    "timestamp",
    "token",
}


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
    return "{}/?tag={}".format(str(hostname).rstrip("/"), quote(str(tag), safe=""))


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


def build_dingtalk_markdown_payload(title, text):
    title = _truncate(title, MARKDOWN_TITLE_MAX_LENGTH) or "SkyRadar 通知"
    text = _truncate(text, MARKDOWN_TEXT_MAX_LENGTH) or title
    return {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": text,
        },
        "at": {"atMobiles": [], "isAtAll": False},
    }


def build_dingtalk_test_payload(domain):
    lines = [
        "### SkyRadar 通知测试",
        "",
        "- 类型: 钉钉 webhook",
        "- 状态: 配置可用",
    ]
    if domain:
        lines.append("- 控制台: [{}]({})".format(domain, domain))
    return build_dingtalk_markdown_payload("SkyRadar 通知测试", "\n".join(lines))


def build_dingtalk_search_notice_payload(tag, results, hostname):
    result_lines = [str(result).strip() for result in results if str(result).strip()]
    dashboard_url = _dashboard_url(hostname, tag)
    tag_text = "[{}]({})".format(tag, dashboard_url) if dashboard_url else str(tag)
    base_lines = [
        "### SkyRadar 监控告警",
        "",
        "- 规则名称: {}".format(tag_text),
        "- 命中数量: {}".format(len(result_lines)),
        "",
        "#### 命中结果",
    ]

    lines = list(base_lines)
    added = 0
    for index, result in enumerate(result_lines):
        remaining = len(result_lines) - index - 1
        suffix = "\n\n还有 {} 条，请在 SkyRadar 查看完整结果。".format(remaining) if remaining else ""
        candidate = "\n".join(lines + ["- {}".format(result)]) + suffix
        if len(candidate) <= MARKDOWN_TEXT_MAX_LENGTH:
            lines.append("- {}".format(result))
            added += 1
            continue
        break

    omitted = len(result_lines) - added
    suffix = "\n\n还有 {} 条，请在 SkyRadar 查看完整结果。".format(omitted) if omitted else ""
    if omitted and added == 0 and result_lines:
        base_text = "\n".join(lines)
        available = MARKDOWN_TEXT_MAX_LENGTH - len(base_text) - len(suffix) - len("\n- ")
        if available > 0:
            lines.append("- {}".format(_truncate(result_lines[0], available)))
            omitted = len(result_lines) - 1
            suffix = "\n\n还有 {} 条，请在 SkyRadar 查看完整结果。".format(omitted) if omitted else ""

    return build_dingtalk_markdown_payload("SkyRadar 监控告警", "\n".join(lines) + suffix)


def post_dingtalk_markdown(webhook, secret, content, timeout=10):
    return requests.post(
        prepare_dingtalk_webhook_url(webhook, secret),
        json=content,
        timeout=timeout,
    )
