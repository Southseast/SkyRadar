# coding: utf-8
# @File        : schemas.py
# @Author      : NanMing
# @Date        : 2026/6/8 14:35
# @Description : Defines results API schemas.

from pydantic import BaseModel, Field


class LeakageListParams(BaseModel):
    status: str
    tag: str | None = None
    language: str | None = None
    limit: int = 10
    from_: int = Field(default=1, alias="from")

    model_config = {"populate_by_name": True}


class LeakagePatchPayload(BaseModel):
    id: str
    project: str
    security: int
    ignore: int
    desc: str = ""
