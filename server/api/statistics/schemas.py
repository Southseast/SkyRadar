# coding: utf-8
# @File        : schemas.py
# @Author      : NanMing
# @Date        : 2026/6/10 12:31
# @Description : Defines statistics API schemas.

from pydantic import BaseModel, field_validator


ALLOWED_BREAKDOWN_FIELDS = {"tag", "language", "security", "ignore", "project"}


class TrendParams(BaseModel):
    tag: str | None = None


class StatisticParams(BaseModel):
    by: str = "tag"
    tag: str = ""

    @field_validator("by")
    @classmethod
    def validate_by(cls, value):
        if value not in ALLOWED_BREAKDOWN_FIELDS:
            raise ValueError("Unsupported breakdown field")
        return value
