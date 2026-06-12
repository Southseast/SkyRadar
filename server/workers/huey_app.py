# coding: utf-8
# @File        : huey_app.py
# @Author      : NanMing
# @Date        : 2026/6/12 15:05
# @Description : Huey application factory boundary.

"""Huey application factory boundary."""

from huey import RedisHuey

from core.database import REDIS_HOST, REDIS_PORT


huey = RedisHuey("skyradar", host=REDIS_HOST, port=int(REDIS_PORT))

__all__ = ["huey"]

