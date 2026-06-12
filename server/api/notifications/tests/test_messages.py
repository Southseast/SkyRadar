# coding: utf-8
# @File        : test_messages.py
# @Author      : NanMing
# @Date        : 2026/6/12 15:40
# @Description : Tests webhook notification message payload builders.

from api.notifications import messages


def test_build_dingtalk_search_notice_payload_matches_markdown_contract():
    payload = messages.build_dingtalk_search_notice_payload(
        "github-token",
        [
            "[org/repo/secret.py](https://github.com/org/repo/blob/main/secret.py)",
            "[org/repo/token.py](https://github.com/org/repo/blob/main/token.py)",
        ],
        "https://skyradar.example.com",
    )

    assert payload == {
        "msgtype": "markdown",
        "markdown": {
            "title": "SkyRadar 监控告警",
            "text": (
                "### SkyRadar 监控告警\n\n"
                "- 规则名称: [github-token](https://skyradar.example.com/?tag=github-token)\n"
                "- 命中数量: 2\n\n"
                "#### 命中结果\n"
                "- [org/repo/secret.py](https://github.com/org/repo/blob/main/secret.py)\n"
                "- [org/repo/token.py](https://github.com/org/repo/blob/main/token.py)"
            ),
        },
        "at": {"atMobiles": [], "isAtAll": False},
    }


def test_build_dingtalk_search_notice_payload_limits_documented_size():
    payload = messages.build_dingtalk_search_notice_payload(
        "github-token",
        [
            "[org/repo/{0}.py](https://github.com/org/repo/blob/main/{0}.py)".format("x" * 80)
            for _ in range(20)
        ],
        "https://skyradar.example.com",
    )

    assert payload["msgtype"] == "markdown"
    assert len(payload["markdown"]["title"]) <= 30
    assert len(payload["markdown"]["text"]) <= 500
    assert "还有" in payload["markdown"]["text"]


def test_build_feishu_search_notice_payload_uses_text_message_contract():
    payload = messages.build_feishu_search_notice_payload(
        "github-token",
        ["[org/repo/secret.py](https://github.com/org/repo/blob/main/secret.py)"],
        "https://skyradar.example.com",
    )

    assert payload["msg_type"] == "text"
    assert "github-token" in payload["content"]["text"]
    assert "https://skyradar.example.com/?tag=github-token" in payload["content"]["text"]


def test_build_provider_test_payloads():
    assert messages.build_dingtalk_test_payload("https://skyradar.example.com")["msgtype"] == "markdown"
    assert messages.build_feishu_test_payload("https://skyradar.example.com")["msg_type"] == "text"
