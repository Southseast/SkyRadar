# coding: utf-8
# @File        : repository.py
# @Author      : NanMing
# @Date        : 2026/6/8 10:36
# @Description : Provides GitHub search repository operations.

import random

from pymongo import ASCENDING, DESCENDING, errors

from core.database import blacklist_col, github_col, notice_col, query_col, result_col, setting_col


DuplicateKeyError = errors.DuplicateKeyError


def task_minute(default=10):
    if setting_col.count_documents({"key": "task", "minute": {"$exists": True}, "page": {"$exists": True}}):
        return int(setting_col.find_one({"key": "task"}).get("minute"))
    return default


def ensure_task_setting(pid, now, default_minute=10, default_page=3):
    if setting_col.count_documents({"key": "task", "minute": {"$exists": True}, "page": {"$exists": True}}):
        setting_col.update_one({"key": "task"}, {"$set": {"key": "task", "pid": pid, "last": now}}, upsert=True)
        return
    setting_col.update_one(
        {"key": "task"},
        {"$set": {"key": "task", "pid": pid, "minute": default_minute, "page": default_page, "last": now}},
        upsert=True,
    )


def touch_task(pid, now):
    return setting_col.update_one({"key": "task"}, {"$set": {"key": "task", "pid": pid, "last": now}}, upsert=True)


def update_task_pid(pid):
    return setting_col.update_one({"key": "task"}, {"$set": {"pid": pid}}, upsert=True)


def task_page():
    if not setting_col.count_documents({"key": "task", "page": {"$exists": True}}):
        return None
    return int(setting_col.find_one({"key": "task"}).get("page"))


def enabled_query_count():
    return query_col.count_documents({"enabled": True})


def iter_enabled_queries():
    return query_col.find({"enabled": True}).sort("last", ASCENDING)


def has_github_capacity():
    return bool(github_col.count_documents({"rate_remaining": {"$gt": 5}}))


def choose_github_account():
    accounts = list(github_col.find({"rate_limit": {"$gt": 5}}).sort("rate_remaining", DESCENDING))
    if not accounts:
        return None
    return random.choice(accounts)


def update_github_rate_remaining(username, remaining):
    return github_col.update_one({"username": username}, {"$set": {"rate_remaining": int(remaining)}})


def update_github_rate_limit(username, remaining, limit):
    return github_col.update_one(
        {"username": username},
        {"$set": {"rate_remaining": int(remaining), "rate_limit": int(limit)}},
    )


def result_exists(filters):
    return bool(result_col.count_documents(filters))


def insert_result(leakage):
    return result_col.insert_one(leakage)


def iter_blacklist():
    return blacklist_col.find({})


def update_query_success(tag, page, api_total, now):
    return query_col.update_one(
        {"tag": tag},
        {
            "$set": {
                "last": int(now),
                "status": 1,
                "reason": "抓取第{}页成功".format(page),
                "api_total": api_total,
                "found_total": result_col.count_documents({"tag": tag}),
            }
        },
    )


def get_mail_setting():
    return setting_col.find_one({"key": "mail"})


def list_notice_receivers():
    return [data.get("mail") for data in notice_col.find({})]


def iter_enabled_webhook_settings():
    return setting_col.find(
        {"webhook": {"$exists": True}, "provider": {"$exists": True}, "enabled": True},
        {"domain": 1, "provider": 1, "webhook": 1, "secret": 1, "_id": 0},
    )


def iter_github_accounts():
    return github_col.find()
