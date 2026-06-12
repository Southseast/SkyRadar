# coding: utf-8
# @File        : repository.py
# @Author      : NanMing
# @Date        : 2026/6/8 15:14
# @Description : Provides settings repository operations.

import hashlib

from core.database import blacklist_col, github_col, notice_col, query_col, result_col, setting_col


GITHUB_ACCOUNT_PUBLIC_PROJECTION = {"_id": 0, "password": 0}
MAIL_SETTING_PUBLIC_PROJECTION = {"_id": 0, "password": 0}


def get_task_setting(projection=None):
    return setting_col.find_one({"key": "task"}, projection)


def upsert_task_setting(page, minute):
    return setting_col.update_many(
        {"key": "task"},
        {"$set": {"key": "task", "page": page, "minute": minute}},
        upsert=True,
    )


def list_settings(projection=None):
    return list(setting_col.find({}, projection))


def list_github_accounts():
    return list(github_col.find({}, GITHUB_ACCOUNT_PUBLIC_PROJECTION))


def save_github_account(document):
    return github_col.replace_one({"_id": document["_id"]}, document, upsert=True)


def delete_github_account(username):
    return github_col.delete_many({"username": username})


def list_queries():
    return list(query_col.find({}).sort("enabled", -1))


def query_exists(tag):
    return query_col.count_documents({"tag": tag})


def update_query(tag, values):
    return query_col.update_one({"tag": tag}, {"$set": values})


def insert_query(document):
    return query_col.insert_one(document)


def delete_query(query_id):
    return query_col.delete_many({"_id": query_id})


def delete_results_by_tag(tag):
    return result_col.delete_many({"tag": tag})


def list_blacklist():
    return list(blacklist_col.find({}, {"_id": 0}))


def save_blacklist(document):
    return blacklist_col.replace_one({"_id": document["_id"]}, document, upsert=True)


def delete_blacklist(text):
    return blacklist_col.delete_many({"text": text})


def list_notices():
    return list(notice_col.find({}, {"_id": 0}))


def insert_notice(document):
    return notice_col.insert_one(document)


def delete_notice(mail):
    return notice_col.delete_many({"mail": mail})


def get_mail_setting():
    return setting_col.find_one({"key": "mail"}, MAIL_SETTING_PUBLIC_PROJECTION)


def upsert_mail_setting(setting):
    return setting_col.update_many({"key": "mail"}, {"$set": {"key": "mail", **setting}}, upsert=True)


def list_webhook_settings():
    return list(setting_col.find({"webhook": {"$exists": True}, "provider": {"$exists": True}}, {"_id": 0}))


def upsert_webhook_setting(webhook_url, values):
    return setting_col.update_one({"webhook": webhook_url}, {"$set": values}, upsert=True)


def count_webhook_setting(webhook_url):
    return setting_col.count_documents({"webhook": webhook_url})


def find_webhook_url_by_hash(webhook_hash):
    for item in list_webhook_settings():
        webhook = item.get("webhook")
        if (
            webhook
            and hashlib.md5(str(webhook).encode("utf-8")).hexdigest() == webhook_hash
        ):
            return webhook
    return None


def delete_webhook_setting(webhook_url):
    return setting_col.delete_one({"webhook": webhook_url})
