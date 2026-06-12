# coding: utf-8
# @File        : repository.py
# @Author      : NanMing
# @Date        : 2026/6/11 13:13
# @Description : Provides statistics repository operations.

from core.database import result_col, setting_col


def count_results(filters=None):
    return result_col.count_documents(filters or {})


def count_settings(filters=None):
    return setting_col.count_documents(filters or {})


def get_task_setting():
    return setting_col.find_one({"key": "task"})


def aggregate_results(pipeline):
    return list(result_col.aggregate(pipeline))
