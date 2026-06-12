# coding: utf-8
# @File        : database.py
# @Author      : NanMing
# @Date        : 2026/6/8 18:12
# @Description : Database boundary for MongoDB collections and Redis handles.

"""Database boundary for MongoDB collections and Redis handles."""

from pymongo import DESCENDING, MongoClient
from redis import Redis

from core.config import get_settings


settings = get_settings()

MONGODB_URI = settings.mongodb_uri
MONGODB_DATABASE = settings.mongodb_database
REDIS_HOST = settings.redis_host
REDIS_PORT = settings.redis_port
REDIS_RESULT_CACHE_DB = settings.redis_result_cache_db


def create_mongo_client(uri, **kwargs):
    client_options = dict(kwargs)
    if settings.mongodb_user and "username" not in client_options:
        client_options["username"] = settings.mongodb_user
        client_options["password"] = settings.mongodb_password
        client_options.setdefault("authSource", settings.mongodb_auth_source)
    return MongoClient(uri, **client_options)


client = create_mongo_client(MONGODB_URI, connect=False)
db = client.get_database(MONGODB_DATABASE)

result_col = db.get_collection("result")
query_col = db.get_collection("query")
blacklist_col = db.get_collection("blacklist")
task_col = db.get_collection("task")
notice_col = db.get_collection("notice")
github_col = db.get_collection("github")
setting_col = db.get_collection("setting")

result_cache = Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_RESULT_CACHE_DB,
    decode_responses=True,
)


def create_indexes():
    for field in ["language", "tag", "datetime", "security", "desc", "ignore", "timestamp"]:
        try:
            result_col.create_index(field, background=True)
        except Exception:
            pass

__all__ = [
    "DESCENDING",
    "MONGODB_DATABASE",
    "MONGODB_URI",
    "REDIS_HOST",
    "REDIS_PORT",
    "REDIS_RESULT_CACHE_DB",
    "blacklist_col",
    "client",
    "create_indexes",
    "create_mongo_client",
    "db",
    "github_col",
    "notice_col",
    "query_col",
    "result_cache",
    "result_col",
    "setting_col",
    "settings",
    "task_col",
]
