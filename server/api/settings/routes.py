# coding: utf-8
# @File        : routes.py
# @Author      : NanMing
# @Date        : 2026/6/10 17:18
# @Description : Defines settings API routes.

from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool

from api.settings import service as settings_service

from ..shared import as_bool, as_int, request_params, response
from .schemas import MailPayload, QueryPayload, WebhookPayload


router = APIRouter()


@router.get("/api/setting/cron")
def get_cron():
    return response(settings_service.get_cron())


@router.post("/api/setting/cron")
async def post_cron(request: Request):
    params = await request_params(request)
    result = await run_in_threadpool(
        settings_service.post_cron,
        as_int(params, "page", 1),
        as_int(params, "minute", 10),
    )
    return response(result)


@router.get("/api/setting/github")
def get_github_accounts():
    return response(settings_service.get_github_accounts())


@router.post("/api/setting/github")
async def post_github_account(request: Request):
    params = await request_params(request)
    result = await run_in_threadpool(
        settings_service.post_github_account,
        params.get("username"),
        params.get("password"),
    )
    return response(result)


@router.delete("/api/setting/github")
def delete_github_account(username: str | None = None):
    return response(settings_service.delete_github_account(username=username))


@router.get("/api/setting/query")
def get_query():
    return response(settings_service.get_query())


@router.post("/api/setting/query")
async def post_query(request: Request):
    params = await request_params(request)
    payload = QueryPayload(keyword=params.get("keyword"), tag=params.get("tag"), enabled=as_bool(params, "enabled", True))
    result = await run_in_threadpool(
        settings_service.post_query,
        payload.keyword,
        payload.tag,
        enabled=payload.enabled,
    )
    return response(result)


@router.delete("/api/setting/query")
def delete_query(_id: str | None = None, tag: str | None = None):
    return response(settings_service.delete_query(_id=_id, tag=tag))


@router.get("/api/setting/blacklist")
def get_blacklist():
    return response(settings_service.get_blacklist())


@router.post("/api/setting/blacklist")
async def post_blacklist(request: Request):
    params = await request_params(request)
    result = await run_in_threadpool(settings_service.post_blacklist, params.get("text"))
    return response(result)


@router.delete("/api/setting/blacklist")
def delete_blacklist(text: str | None = None):
    return response(settings_service.delete_blacklist(text=text))


@router.get("/api/setting/notice")
def get_notice():
    return response(settings_service.get_notice())


@router.post("/api/setting/notice")
async def post_notice(request: Request):
    params = await request_params(request)
    result = await run_in_threadpool(settings_service.post_notice, params.get("mail"))
    return response(result)


@router.delete("/api/setting/notice")
def delete_notice(mail: str | None = None):
    return response(settings_service.delete_notice(mail=mail))


@router.get("/api/setting/mail")
def get_mail():
    return response(settings_service.get_mail())


@router.post("/api/setting/mail")
async def post_mail(request: Request):
    params = await request_params(request)
    payload = MailPayload(
        from_=params.get("from"),
        host=params.get("host"),
        port=as_int(params, "port"),
        tls=as_bool(params, "tls", False),
        username=params.get("username"),
        password=params.get("password"),
        domain=params.get("domain"),
        enabled=as_bool(params, "enabled", False),
        test=as_bool(params, "test", False),
    )
    result = await run_in_threadpool(settings_service.post_mail, payload.model_dump(by_alias=True))
    return response(result)


@router.get("/api/setting/webhook")
def get_webhook():
    return response(settings_service.get_webhook())


@router.post("/api/setting/webhook")
async def post_webhook(request: Request):
    params = await request_params(request)
    payload = WebhookPayload(
        provider=params.get("provider"),
        webhook_url=params.get("webhook_url"),
        secret=params.get("secret"),
        domain=params.get("domain"),
        enabled=as_bool(params, "enabled", False),
        test=as_bool(params, "test", False),
    )
    result = await run_in_threadpool(settings_service.post_webhook, payload.model_dump())
    return response(result)


@router.delete("/api/setting/webhook")
def delete_webhook(webhook_url: str | None = None, webhook_hash: str | None = None):
    return response(settings_service.delete_webhook(webhook_url=webhook_url, webhook_hash=webhook_hash))
