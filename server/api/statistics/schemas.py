# coding: utf-8
# @File        : schemas.py
# @Author      : NanMing
# @Date        : 2026/6/10 12:31
# @Description : Defines statistics API schemas.

from pydantic import BaseModel


class TrendParams(BaseModel):
    tag: str | None = None


class StatisticParams(BaseModel):
    by: str = "tag"
    tag: str = ""
