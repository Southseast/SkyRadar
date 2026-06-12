# coding: utf-8
# @File        : service.py
# @Author      : NanMing
# @Date        : 2026/6/8 15:02
# @Description : Implements notification delivery service logic.

import smtplib

from api.notifications import messages as notification_messages
from api.notifications import repository as notification_repository
from core.logging import logger
from integrations import dingtalk as dingtalk_integration
from integrations import feishu as feishu_integration
from integrations import mail as mail_integration


def send_mail_notice(content):
    smtp_config = notification_repository.get_mail_setting()
    receivers = notification_repository.list_notice_receivers()
    try:
        if mail_integration.send_smtp_notice(smtp_config, receivers, content):
            logger.info("邮件发送成功")
        else:
            logger.critical("Error: 无法发送邮件")
    except smtplib.SMTPException as error:
        logger.critical("Error: 无法发送邮件 {}".format(error))


def send_webhook_notice(tag, results):
    if not results:
        return
    for webhook_setting in notification_repository.iter_enabled_webhook_settings():
        hostname = webhook_setting.get("domain")
        provider = webhook_setting.get("provider")
        webhook = webhook_setting.get("webhook")
        secret = webhook_setting.get("secret")
        if provider not in {"dingtalk", "feishu"}:
            logger.error("不支持的 webhook 类型，已跳过发送")
            continue
        if not secret:
            logger.error("webhook 缺少加签 Secret，已跳过发送")
            continue

        try:
            if provider == "feishu":
                content = notification_messages.build_feishu_search_notice_payload(tag, results, hostname)
                feishu_integration.post_feishu_webhook(webhook, secret, content, timeout=10)
                continue

            content = notification_messages.build_dingtalk_search_notice_payload(tag, results, hostname)
            dingtalk_integration.post_dingtalk_webhook(webhook, secret, content, timeout=10)
        except Exception as error:
            logger.error(error)
