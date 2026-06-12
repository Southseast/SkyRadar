# coding: utf-8
# @File        : messages.py
# @Author      : NanMing
# @Date        : 2026/6/12 15:39
# @Description : Builds provider payloads for webhook notifications.

from urllib.parse import quote


DINGTALK_MARKDOWN_TITLE_MAX_LENGTH = 30
DINGTALK_MARKDOWN_TEXT_MAX_LENGTH = 500
FEISHU_TEXT_MAX_LENGTH = 20 * 1024


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


def _result_lines(results):
    return [str(result).strip() for result in results if str(result).strip()]


def build_dingtalk_markdown_payload(title, text):
    title = _truncate(title, DINGTALK_MARKDOWN_TITLE_MAX_LENGTH) or "SkyRadar 通知"
    text = _truncate(text, DINGTALK_MARKDOWN_TEXT_MAX_LENGTH) or title
    return {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": text,
        },
        "at": {"atMobiles": [], "isAtAll": False},
    }


def build_feishu_text_payload(text):
    text = _truncate(text, FEISHU_TEXT_MAX_LENGTH) or "SkyRadar 通知"
    return {
        "msg_type": "text",
        "content": {"text": text},
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


def build_feishu_test_payload(domain):
    lines = [
        "SkyRadar 通知测试",
        "类型: 飞书 webhook",
        "状态: 配置可用",
    ]
    if domain:
        lines.append("控制台: {}".format(domain))
    return build_feishu_text_payload("\n".join(lines))


def build_dingtalk_search_notice_payload(tag, results, hostname):
    results = _result_lines(results)
    dashboard_url = _dashboard_url(hostname, tag)
    tag_text = "[{}]({})".format(tag, dashboard_url) if dashboard_url else str(tag)
    base_lines = [
        "### SkyRadar 监控告警",
        "",
        "- 规则名称: {}".format(tag_text),
        "- 命中数量: {}".format(len(results)),
        "",
        "#### 命中结果",
    ]

    lines = list(base_lines)
    added = 0
    for index, result in enumerate(results):
        remaining = len(results) - index - 1
        suffix = "\n\n还有 {} 条，请在 SkyRadar 查看完整结果。".format(remaining) if remaining else ""
        candidate = "\n".join(lines + ["- {}".format(result)]) + suffix
        if len(candidate) <= DINGTALK_MARKDOWN_TEXT_MAX_LENGTH:
            lines.append("- {}".format(result))
            added += 1
            continue
        break

    omitted = len(results) - added
    suffix = "\n\n还有 {} 条，请在 SkyRadar 查看完整结果。".format(omitted) if omitted else ""
    if omitted and added == 0 and results:
        base_text = "\n".join(lines)
        available = DINGTALK_MARKDOWN_TEXT_MAX_LENGTH - len(base_text) - len(suffix) - len("\n- ")
        if available > 0:
            lines.append("- {}".format(_truncate(results[0], available)))
            omitted = len(results) - 1
            suffix = "\n\n还有 {} 条，请在 SkyRadar 查看完整结果。".format(omitted) if omitted else ""

    return build_dingtalk_markdown_payload("SkyRadar 监控告警", "\n".join(lines) + suffix)


def build_feishu_search_notice_payload(tag, results, hostname):
    results = _result_lines(results)
    dashboard_url = _dashboard_url(hostname, tag)
    lines = [
        "SkyRadar 监控告警",
        "规则名称: {}".format(tag),
        "命中数量: {}".format(len(results)),
    ]
    if dashboard_url:
        lines.append("控制台: {}".format(dashboard_url))
    lines.extend(["", "命中结果:"])

    added = 0
    for index, result in enumerate(results):
        remaining = len(results) - index - 1
        suffix = "\n还有 {} 条，请在 SkyRadar 查看完整结果。".format(remaining) if remaining else ""
        candidate = "\n".join(lines + ["- {}".format(result)]) + suffix
        if len(candidate) <= FEISHU_TEXT_MAX_LENGTH:
            lines.append("- {}".format(result))
            added += 1
            continue
        break

    omitted = len(results) - added
    if omitted:
        lines.append("还有 {} 条，请在 SkyRadar 查看完整结果。".format(omitted))
    return build_feishu_text_payload("\n".join(lines))
