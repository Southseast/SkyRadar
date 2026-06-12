# coding: utf-8
# @File        : test_notification_payloads.py
# @Author      : NanMing
# @Date        : 2026/6/9 13:30
# @Description : Tests notification payload delivery behavior.

from api.notifications import service as notifications


def test_send_mail_passes_smtp_receivers_and_content(monkeypatch):
    smtp_config = {
        "host": "smtp.example.com",
        "port": 587,
        "username": "skyradar@example.com",
        "password": "smtp-secret",
        "enabled": True,
    }
    receivers = ["sec@example.com", "ops@example.com"]
    captured = {}

    monkeypatch.setattr(notifications.worker_repository, "get_mail_setting", lambda: smtp_config)
    monkeypatch.setattr(notifications.worker_repository, "list_notice_receivers", lambda: receivers)

    def fake_send_smtp_notice(actual_smtp_config, actual_receivers, actual_content):
        captured["smtp_config"] = actual_smtp_config
        captured["receivers"] = actual_receivers
        captured["content"] = actual_content
        return True

    monkeypatch.setattr(notifications.mail_integration, "send_smtp_notice", fake_send_smtp_notice)

    notifications.send_mail_notice("<p>leakage result</p>")

    assert captured == {
        "smtp_config": smtp_config,
        "receivers": receivers,
        "content": "<p>leakage result</p>",
    }


def test_send_webhook_notice_posts_dingtalk_markdown_payload(monkeypatch):
    settings = [
        {
            "domain": "https://skyradar.example.com",
            "provider": "dingtalk",
            "webhook": "https://oapi.dingtalk.com/robot/send?access_token=abc",
            "secret": "SEC000000",
        }
    ]
    results = [
        "[org/repo/secret.py](https://github.com/org/repo/blob/main/secret.py)",
        "[org/repo/token.py](https://github.com/org/repo/blob/main/token.py)",
    ]
    captured = []

    monkeypatch.setattr(notifications.worker_repository, "iter_enabled_webhook_settings", lambda: settings)
    monkeypatch.setattr(notifications.dingtalk_integration, "is_dingtalk_webhook", lambda webhook: True)

    def fake_post_dingtalk_markdown(webhook, secret, content, timeout):
        captured.append(
            {
                "webhook": webhook,
                "secret": secret,
                "content": content,
                "timeout": timeout,
            }
        )

    monkeypatch.setattr(notifications.dingtalk_integration, "post_dingtalk_markdown", fake_post_dingtalk_markdown)

    notifications.send_webhook_notice("github-token", results)

    assert captured == [
        {
            "webhook": "https://oapi.dingtalk.com/robot/send?access_token=abc",
            "secret": "SEC000000",
            "content": {
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
            },
            "timeout": 10,
        }
    ]


def test_send_webhook_notice_limits_markdown_to_dingtalk_documented_size(monkeypatch):
    settings = [
        {
            "domain": "https://skyradar.example.com",
            "provider": "dingtalk",
            "webhook": "https://oapi.dingtalk.com/robot/send?access_token=abc",
            "secret": "SEC000000",
        }
    ]
    results = [
        "[org/repo/{0}.py](https://github.com/org/repo/blob/main/{0}.py)".format("x" * 80)
        for _ in range(20)
    ]
    captured = []

    monkeypatch.setattr(notifications.worker_repository, "iter_enabled_webhook_settings", lambda: settings)
    monkeypatch.setattr(notifications.dingtalk_integration, "is_dingtalk_webhook", lambda webhook: True)
    monkeypatch.setattr(
        notifications.dingtalk_integration,
        "post_dingtalk_markdown",
        lambda webhook, secret, content, timeout: captured.append(content),
    )

    notifications.send_webhook_notice("github-token", results)

    assert len(captured) == 1
    content = captured[0]
    assert content["msgtype"] == "markdown"
    assert len(content["markdown"]["title"]) <= 30
    assert len(content["markdown"]["text"]) <= 500
    assert "还有" in content["markdown"]["text"]
    assert content["at"] == {"atMobiles": [], "isAtAll": False}


def test_send_webhook_notice_posts_feishu_text_payload(monkeypatch):
    settings = [
        {
            "domain": "https://skyradar.example.com",
            "provider": "feishu",
            "webhook": "https://open.feishu.cn/open-apis/bot/v2/hook/example",
            "secret": "SEC000000",
        }
    ]
    captured = []

    monkeypatch.setattr(notifications.worker_repository, "iter_enabled_webhook_settings", lambda: settings)
    monkeypatch.setattr(
        notifications.feishu_integration,
        "post_feishu_text",
        lambda webhook, secret, content, timeout: captured.append(
            {
                "webhook": webhook,
                "secret": secret,
                "content": content,
                "timeout": timeout,
            }
        ),
    )

    notifications.send_webhook_notice(
        "github-token",
        ["[org/repo/secret.py](https://github.com/org/repo/blob/main/secret.py)"],
    )

    assert captured[0]["webhook"] == "https://open.feishu.cn/open-apis/bot/v2/hook/example"
    assert captured[0]["secret"] == "SEC000000"
    assert captured[0]["timeout"] == 10
    assert captured[0]["content"]["msg_type"] == "text"
    assert captured[0]["content"]["timestamp"]
    assert captured[0]["content"]["sign"]
    assert "github-token" in captured[0]["content"]["content"]["text"]


def test_send_webhook_notice_skips_when_results_are_empty(monkeypatch):
    calls = []

    def fail_iter_enabled_webhook_settings():
        raise AssertionError("webhook settings must not be loaded without results")

    monkeypatch.setattr(
        notifications.worker_repository,
        "iter_enabled_webhook_settings",
        fail_iter_enabled_webhook_settings,
    )
    monkeypatch.setattr(
        notifications.dingtalk_integration,
        "post_dingtalk_markdown",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    notifications.send_webhook_notice("github-token", [])

    assert calls == []


def test_send_webhook_notice_skips_unsupported_or_missing_secret(monkeypatch):
    settings = [
        {
            "domain": "https://skyradar.example.com",
            "provider": "slack",
            "webhook": "https://example.com/webhook",
            "secret": "SEC000000",
        },
        {
            "domain": "https://skyradar.example.com",
            "provider": "dingtalk",
            "webhook": "https://oapi.dingtalk.com/robot/send?access_token=abc",
            "secret": "",
        },
    ]
    calls = []

    monkeypatch.setattr(notifications.worker_repository, "iter_enabled_webhook_settings", lambda: settings)
    monkeypatch.setattr(
        notifications.dingtalk_integration,
        "is_dingtalk_webhook",
        lambda webhook: "oapi.dingtalk.com" in webhook,
    )
    monkeypatch.setattr(
        notifications.dingtalk_integration,
        "post_dingtalk_markdown",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    notifications.send_webhook_notice(
        "github-token",
        ["[org/repo/secret.py](https://github.com/org/repo/blob/main/secret.py)"],
    )

    assert calls == []
