# coding: utf-8
# @File        : repository.py
# @Author      : NanMing
# @Date        : 2026/6/9 18:44
# @Description : Provides results repository operations.

from core.database import DESCENDING, create_indexes, result_col


def ensure_indexes():
    create_indexes()


def list_leakages(filters, limit, from_):
    return list(
        result_col.find(filters, {"code": 0, "affect": 0})
        .sort("datetime", DESCENDING)
        .limit(limit)
        .skip(limit * (from_ - 1))
    )


def count_leakages(filters):
    return result_col.count_documents(filters or {})


def update_leakage(leakage_id, values):
    return result_col.update_one({"_id": leakage_id}, {"$set": values})


def update_project_leakages(project, values):
    return result_col.update_many({"project": project}, {"$set": values})


def get_leakage_info(leakage_id):
    return result_col.find_one({"_id": leakage_id}, {"_id": 0, "code": 0})


def get_leakage_code(leakage_id):
    return result_col.find_one({"_id": leakage_id}, {"_id": 0, "code": 1, "affect": 1})
