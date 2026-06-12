# coding: utf-8
# @File        : mail.py
# @Author      : NanMing
# @Date        : 2026/6/9 15:29
# @Description : Sends email notices through SMTP.

import smtplib
from email.header import Header
from email.mime.text import MIMEText

from loguru import logger


class SMTPClient:
    def __init__(self, smtp_config):
        self.host = smtp_config.get("host")
        self.port = int(smtp_config.get("port"))
        self.tls = smtp_config.get("tls")
        self.username = smtp_config.get("username")
        self.password = smtp_config.get("password")
        if self.tls:
            self.smtp = smtplib.SMTP(self.host, self.port, timeout=300)
        else:
            self.smtp = smtplib.SMTP_SSL(self.host, self.port, timeout=300)

    def login(self):
        if self.tls:
            self.smtp.starttls()
        self.smtp.login(self.username, self.password)

    def sendmail(self, receivers, message):
        self.smtp.sendmail(self.username, receivers, message.as_string())


def send_smtp_notice(smtp_config, receivers, content):
    message = MIMEText(content, _subtype="html", _charset="utf-8")
    message["From"] = Header(
        "{}<{}>".format(smtp_config.get("from"), smtp_config.get("username")),
        "utf-8",
    )
    message["To"] = Header(";".join(receivers), "utf-8")
    message["Subject"] = Header("[GitHub] 监控告警", "utf-8")
    try:
        smtp = SMTPClient(smtp_config)
        smtp.login()
        smtp.sendmail(receivers, message)
        return True
    except (OSError, smtplib.SMTPException, TypeError, ValueError) as error:
        logger.exception("Unable to send SMTP notice: {}", error)
        return False
