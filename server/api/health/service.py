# coding: utf-8
# @File        : service.py
# @Author      : NanMing
# @Date        : 2026/6/12 11:05
# @Description : Implements health check service logic.

from redis import Redis

from core.config import load_settings
from core.database import create_mongo_client


def _healthy(message="ok"):
    return {"ok": True, "message": message}


def _unhealthy(error):
    return {"ok": False, "message": str(error)}


def health_status():
    status = {"api": _healthy("ok")}

    try:
        settings = load_settings()
        client = create_mongo_client(
            settings.mongodb_uri,
            connect=False,
            socketTimeoutMS=50,
            serverSelectionTimeoutMS=500,
        )
        ping = client.get_database(settings.mongodb_database).command("ping")
        status["mongodb"] = {
            "ok": ping.get("ok") in (1, 1.0, True),
            "message": "ping ok",
        }
    except Exception as error:
        status["mongodb"] = _unhealthy(error)

    try:
        redis = Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_result_cache_db,
            decode_responses=True,
        )
        status["redis"] = {
            "ok": bool(redis.ping()),
            "message": "ping ok",
        }
    except Exception as error:
        status["redis"] = _unhealthy(error)

    return status
