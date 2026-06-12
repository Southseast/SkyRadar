# coding: utf-8
# @File        : service.py
# @Author      : NanMing
# @Date        : 2026/6/9 15:12
# @Description : Implements results service logic.

import json

from api.results import repository as result_repository


def leakage_list(status, tag=None, language=None, limit=10, from_=1):
    filters = json.loads(status)
    result_repository.ensure_indexes()
    if tag:
        filters = {"tag": tag, **filters}
    if language:
        filters = {"language": language, **filters}
    results = result_repository.list_leakages(filters, limit, from_)
    total = result_repository.count_leakages(filters)
    return {
        "msg": "共 {} 条记录".format(total) if total else "暂无数据",
        "status": 200,
        "result": results,
        "total": total,
    }


def patch_leakage(params):
    desc = params.get("desc") or ""
    security = int(params.get("security"))
    ignore = int(params.get("ignore"))
    result_repository.update_leakage(params.get("id"), {"security": security, "ignore": ignore, "desc": desc})
    if not security:
        if not ignore:
            result_repository.update_project_leakages(params.get("project"), {"security": 0, "ignore": 0, "desc": desc})
    if security and ignore:
        result_repository.update_project_leakages(params.get("project"), {"security": 1, "ignore": 1, "desc": desc})
    return {"status": 201, "msg": "处理成功", "result": []}


def leakage_info(leakage_id):
    result = result_repository.get_leakage_info(leakage_id)
    return {"status": 200, "msg": "获取信息成功", "result": result}


def leakage_code(leakage_id):
    result = result_repository.get_leakage_code(leakage_id)
    return {"status": 200, "msg": "获取信息成功", "result": result}
