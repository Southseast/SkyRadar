# coding: utf-8
# @File        : schemas.py
# @Author      : NanMing
# @Date        : 2026/6/11 10:10
# @Description : Defines settings API schemas.

from pydantic import BaseModel, Field


class CronPayload(BaseModel):
    page: int = 1
    minute: int = 10


class GithubAccountPayload(BaseModel):
    username: str | None = None
    password: str | None = None


class QueryPayload(BaseModel):
    keyword: str | None = None
    tag: str | None = None
    enabled: bool = True


class MailPayload(BaseModel):
    from_: str | None = Field(default=None, alias="from")
    host: str | None = None
    port: int | None = None
    tls: bool = False
    username: str | None = None
    password: str | None = None
    domain: str | None = None
    enabled: bool = False
    test: bool = False

    model_config = {"populate_by_name": True}


class WebhookPayload(BaseModel):
    provider: str | None = None
    webhook_url: str | None = None
    secret: str | None = None
    domain: str | None = None
    enabled: bool = False
    test: bool = False
