# coding: utf-8
# @File        : service.py
# @Author      : NanMing
# @Date        : 2026/6/12 15:37
# @Description : Implements statistics service logic.

import datetime

import psutil

from api.statistics import repository as statistic_repository


def trend(tag=None):
    today_start = int(
        datetime.datetime.combine(datetime.date.today(), datetime.time.min).timestamp()
    )
    if tag:
        total = {
            "total": statistic_repository.count_results({"tag": tag}),
            "ignore": statistic_repository.count_results({"tag": tag, "security": 1}),
            "risk": statistic_repository.count_results({"tag": tag, "security": 0, "desc": {"$exists": True}}),
        }
        today = {
            "total": statistic_repository.count_results({"tag": tag, "timestamp": {"$gte": today_start}}),
            "ignore": statistic_repository.count_results({"tag": tag, "timestamp": {"$gte": today_start}, "security": 1}),
            "risk": statistic_repository.count_results(
                {"tag": tag, "timestamp": {"$gte": today_start}, "security": 0, "desc": {"$exists": True}}
            ),
        }
    else:
        total = {
            "total": statistic_repository.count_results(),
            "ignore": statistic_repository.count_results({"security": 1}),
            "risk": statistic_repository.count_results({"security": 0, "desc": {"$exists": True}}),
        }
        today = {
            "total": statistic_repository.count_results({"timestamp": {"$gte": today_start}}),
            "ignore": statistic_repository.count_results({"timestamp": {"$gte": today_start}, "security": 1}),
            "risk": statistic_repository.count_results(
                {"timestamp": {"$gte": today_start}, "security": 0, "desc": {"$exists": True}}
            ),
        }
    if statistic_repository.count_settings({"key": "task"}):
        task_setting = statistic_repository.get_task_setting()
        engine = {
            "status": psutil.pid_exists(int(task_setting.get("pid"))),
            "last": task_setting.get("last"),
        }
    else:
        engine = {"status": False, "last": 0}
    return {"status": 200, "msg": "获取信息成功", "result": {"all": total, "today": today, "engine": engine}}


def statistic(by="tag", tag=""):
    filters = {"tag": tag, "security": 0} if tag else {"security": 0}
    pipeline = [
        {"$match": filters},
        {"$group": {"_id": "${}".format(by), "value": {"$sum": 1}}},
    ]
    result = statistic_repository.aggregate_results(pipeline)
    if not result:
        result = statistic_repository.aggregate_results([{"$group": {"_id": "${}".format(by), "value": {"$sum": 0}}}])
    return {"status": 200, "msg": "获取信息成功", "result": result}
