# coding: utf-8
# @File        : schemas.py
# @Author      : NanMing
# @Date        : 2026/6/8 14:35
# @Description : Defines results API schemas.

from pydantic import BaseModel, Field


class LeakageListParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    tag: str | None = None
    language: str | None = None
    security: int | None = Field(default=None, ge=0, le=1)
    ignored: bool | None = None
    reviewed: bool | None = None

    model_config = {"populate_by_name": True}


class LeakagePatchPayload(BaseModel):
    project: str | None = None
    security: int | None = Field(default=None, ge=0, le=1)
    ignored: bool | None = None
    desc: str | None = None
