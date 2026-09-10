# coding: utf-8
# @File        : repository.py
# @Author      : NanMing
# @Date        : 2026/7/2
# @Description : Provides AI analysis repository operations.

from pymongo import ReturnDocument

from core.database import result_col, setting_col


OPENAI_SETTING_KEY = "openai"
OPENAI_RUNTIME_KEY = "openai_analysis_runtime"


def get_openai_setting():
    return setting_col.find_one({"key": OPENAI_SETTING_KEY})


def save_openai_setting(document):
    return setting_col.replace_one({"key": OPENAI_SETTING_KEY}, document, upsert=True)


def get_leakage_for_analysis(leakage_id):
    return result_col.find_one({"_id": leakage_id})


def update_ai_analysis(leakage_id, analysis):
    return result_col.update_one({"_id": leakage_id}, {"$set": {"ai_analysis": analysis}})


def mark_ai_analysis_pending(leakage_id, force=False):
    filters = {"_id": leakage_id}
    if not force:
        filters["$or"] = [
            {"ai_analysis.status": {"$exists": False}},
            {"ai_analysis.status": {"$in": ["failed", "skipped"]}},
        ]
    return result_col.update_one(filters, {"$set": {"ai_analysis": {"status": "pending"}}})


def ensure_analysis_runtime():
    return setting_col.update_one(
        {"key": OPENAI_RUNTIME_KEY},
        {"$setOnInsert": {"key": OPENAI_RUNTIME_KEY, "running_count": 0}},
        upsert=True,
    )


def claim_analysis_slot(concurrency):
    ensure_analysis_runtime()
    return setting_col.find_one_and_update(
        {"key": OPENAI_RUNTIME_KEY, "running_count": {"$lt": int(concurrency)}},
        {"$inc": {"running_count": 1}},
        return_document=ReturnDocument.AFTER,
    )


def release_analysis_slot():
    return setting_col.update_one(
        {"key": OPENAI_RUNTIME_KEY, "running_count": {"$gt": 0}},
        {"$inc": {"running_count": -1}},
    )
