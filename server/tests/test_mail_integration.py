# coding: utf-8
# @File        : test_mail_integration.py
# @Author      : NanMing
# @Date        : 2026/6/12 15:28
# @Description : Tests SMTP mail integration behavior.

from email import message_from_string

from integrations.mail import send_smtp_notice


def test_send_smtp_notice_sends_html_message(monkeypatch):
    captured = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            captured["connection"] = (host, port, timeout)

        def starttls(self):
            captured["starttls"] = True

        def login(self, username, password):
            captured["login"] = (username, password)

        def sendmail(self, username, receivers, message):
            captured["sendmail"] = (username, receivers, message)

    monkeypatch.setattr("integrations.mail.smtplib.SMTP", FakeSMTP)

    result = send_smtp_notice(
        {
            "from": "SkyRadar",
            "host": "smtp.example.com",
            "port": 587,
            "tls": True,
            "username": "skyradar@example.com",
            "password": "smtp-secret",
        },
        ["sec@example.com"],
        "<p>leak</p>",
    )

    assert result is True
    assert captured["connection"] == ("smtp.example.com", 587, 300)
    assert captured["starttls"] is True
    assert captured["login"] == ("skyradar@example.com", "smtp-secret")
    assert captured["sendmail"][0] == "skyradar@example.com"
    assert captured["sendmail"][1] == ["sec@example.com"]
    message = message_from_string(captured["sendmail"][2])
    assert message.get_payload(decode=True).decode("utf-8") == "<p>leak</p>"


def test_send_smtp_notice_returns_false_when_connection_fails(monkeypatch):
    def fail_connect(*args, **kwargs):
        raise OSError("network unavailable")

    monkeypatch.setattr("integrations.mail.smtplib.SMTP_SSL", fail_connect)

    result = send_smtp_notice(
        {
            "from": "SkyRadar",
            "host": "smtp.example.com",
            "port": 465,
            "tls": False,
            "username": "skyradar@example.com",
            "password": "smtp-secret",
        },
        ["sec@example.com"],
        "<p>leak</p>",
    )

    assert result is False
