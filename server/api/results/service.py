# coding: utf-8
# @File        : service.py
# @Author      : NanMing
# @Date        : 2026/6/9 15:12
# @Description : Implements results service logic.

from api.results import repository as result_repository


class InvalidResultPatch(Exception):
    pass


class LeakageResultNotFound(Exception):
    pass


def leakage_list(tag=None, language=None, security=None, ignored=None, reviewed=None, page=1, page_size=20):
    filters = {}
    result_repository.ensure_indexes()
    if tag:
        filters["tag"] = tag
    if language:
        filters["language"] = language
    if security is not None:
        filters["security"] = int(security)
    if ignored is not None:
        filters["ignore"] = 1 if ignored else 0
    if reviewed is not None:
        filters["desc"] = {"$exists": bool(reviewed)}
    results = result_repository.list_leakages(filters, page_size, page)
    total = result_repository.count_leakages(filters)
    return {
        "items": results,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def patch_leakage(leakage_id, params):
    values = {}
    if params.get("security") is not None:
        values["security"] = int(params.get("security"))
    if params.get("ignored") is not None:
        values["ignore"] = 1 if params.get("ignored") else 0
    if params.get("desc") is not None:
        values["desc"] = params.get("desc") or ""
    if not values:
        raise InvalidResultPatch("PATCH body must include at least one mutable field")

    update_result = result_repository.update_leakage(leakage_id, values)
    if getattr(update_result, "matched_count", 1) == 0:
        raise LeakageResultNotFound(leakage_id)

    project = params.get("project")
    security = values.get("security")
    ignore = values.get("ignore")
    desc = values.get("desc", "")
    if project and security == 0 and ignore == 0:
        result_repository.update_project_leakages(project, {"security": 0, "ignore": 0, "desc": desc})
    if project and security == 1 and ignore == 1:
        result_repository.update_project_leakages(project, {"security": 1, "ignore": 1, "desc": desc})
    return {"id": leakage_id, "updated": True}


def leakage_info(leakage_id):
    result = result_repository.get_leakage_info(leakage_id)
    if result is None:
        raise LeakageResultNotFound(leakage_id)
    return result


def leakage_code(leakage_id):
    result = result_repository.get_leakage_code(leakage_id)
    if result is None:
        raise LeakageResultNotFound(leakage_id)
    return result
