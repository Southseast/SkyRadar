# coding: utf-8
# @File        : repository.py
# @Author      : NanMing
# @Date        : 2026/6/12 16:45
# @Description : Provides notification repository operations.

from core.database import notice_col, setting_col


def get_mail_setting():
    return setting_col.find_one({"key": "mail"})


def list_notice_receivers():
    return [data.get("mail") for data in notice_col.find({})]


def iter_enabled_webhook_settings():
    return setting_col.find(
        {"webhook": {"$exists": True}, "provider": {"$exists": True}, "enabled": True},
        {"domain": 1, "provider": 1, "webhook": 1, "secret": 1, "_id": 0},
    )
