# coding: utf-8
# @File        : schemas.py
# @Author      : NanMing
# @Date        : 2026/6/11 18:03
# @Description : Defines health check API response schemas.

from typing import Any

from pydantic import BaseModel


class HealthStatus(BaseModel):
    github: dict[str, Any]
    mongodb: dict[str, Any]
