# coding: utf-8
# @File        : routes.py
# @Author      : NanMing
# @Date        : 2026/6/10 17:18
# @Description : Defines settings API routes.

from fastapi import APIRouter, Request, Response
from fastapi.concurrency import run_in_threadpool

from api.settings import service as settings_service
from core.responses import rest_error_response, rest_response

from ..shared import as_bool, as_int, request_params
from .schemas import MailPayload, QueryPayload, WebhookPayload


router = APIRouter()


def _handle_service_error(error):
    return rest_error_response("settings_error", error.message, status_code=error.status_code)


async def _run_service_response(func, *args, status_code=200, **kwargs):
    try:
        result = await run_in_threadpool(func, *args, **kwargs)
    except settings_service.SettingsServiceError as error:
        return _handle_service_error(error)
    return rest_response(result, status_code=status_code)


def _call_service_response(func, *args, status_code=200, **kwargs):
    try:
        result = func(*args, **kwargs)
    except settings_service.SettingsServiceError as error:
        return _handle_service_error(error)
    return rest_response(result, status_code=status_code)


@router.get("/api/v1/github-accounts")
def get_github_accounts():
    return _call_service_response(settings_service.get_github_accounts)


@router.post("/api/v1/github-accounts")
async def post_github_account(request: Request):
    params = await request_params(request)
    return await _run_service_response(
        settings_service.create_github_account,
        params.get("username"),
        params.get("password"),
        status_code=201,
    )


@router.delete("/api/v1/github-accounts/{username}")
async def delete_github_account(username: str):
    response = await _run_service_response(settings_service.delete_github_account, username)
    if response.status_code != 200:
        return response
    return Response(status_code=204)


@router.get("/api/v1/search-rules")
def get_search_rules():
    return _call_service_response(settings_service.get_search_rules)


@router.post("/api/v1/search-rules")
async def post_search_rule(request: Request):
    params = await request_params(request)
    payload = QueryPayload(
        keyword=params.get("keyword"),
        tag=params.get("tag"),
        enabled=as_bool(params, "enabled", True),
    )
    return await _run_service_response(
        settings_service.create_search_rule,
        payload.keyword,
        payload.tag,
        enabled=payload.enabled,
        status_code=201,
    )


@router.put("/api/v1/search-rules/{tag}")
async def put_search_rule(tag: str, request: Request):
    params = await request_params(request)
    payload = QueryPayload(
        keyword=params.get("keyword"),
        tag=tag,
        enabled=as_bool(params, "enabled", True),
    )
    return await _run_service_response(
        settings_service.put_search_rule,
        payload.tag,
        payload.keyword,
        enabled=payload.enabled,
    )


@router.delete("/api/v1/search-rules/{tag}")
async def delete_search_rule(tag: str):
    response = await _run_service_response(settings_service.delete_search_rule, tag)
    if response.status_code != 200:
        return response
    return Response(status_code=204)


@router.get("/api/v1/task-schedules/current")
def get_task_settings():
    return _call_service_response(settings_service.get_task_settings)


@router.put("/api/v1/task-schedules/current")
async def put_task_settings(request: Request):
    params = await request_params(request)
    return await _run_service_response(
        settings_service.put_task_settings,
        as_int(params, "page", 1),
        as_int(params, "minute", 10),
    )


@router.get("/api/v1/blacklist-items")
def get_blacklist_items():
    return _call_service_response(settings_service.get_blacklist_items)


@router.post("/api/v1/blacklist-items")
async def post_blacklist_item(request: Request):
    params = await request_params(request)
    return await _run_service_response(settings_service.create_blacklist_item, params.get("text"), status_code=201)


@router.delete("/api/v1/blacklist-items/{text:path}")
async def delete_blacklist_item(text: str):
    response = await _run_service_response(settings_service.delete_blacklist_item, text)
    if response.status_code != 200:
        return response
    return Response(status_code=204)


@router.get("/api/v1/notification-recipients")
def get_notification_recipients():
    return _call_service_response(settings_service.get_notification_recipients)


@router.post("/api/v1/notification-recipients")
async def post_notification_recipient(request: Request):
    params = await request_params(request)
    return await _run_service_response(
        settings_service.create_notification_recipient,
        params.get("mail"),
        status_code=201,
    )


@router.delete("/api/v1/notification-recipients/{mail}")
async def delete_notification_recipient(mail: str):
    response = await _run_service_response(settings_service.delete_notification_recipient, mail)
    if response.status_code != 200:
        return response
    return Response(status_code=204)


@router.get("/api/v1/mail-settings/current")
def get_mail_settings():
    return _call_service_response(settings_service.get_mail_settings)


@router.put("/api/v1/mail-settings/current")
async def put_mail_settings(request: Request):
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
    return await _run_service_response(
        settings_service.put_mail_settings,
        payload.model_dump(by_alias=True),
    )


@router.get("/api/v1/webhooks")
def get_webhook_settings():
    return _call_service_response(settings_service.get_webhook_settings)


@router.post("/api/v1/webhooks")
async def post_webhook_setting(request: Request):
    params = await request_params(request)
    payload = WebhookPayload(
        provider=params.get("provider"),
        webhook_url=params.get("webhook_url"),
        secret=params.get("secret"),
        domain=params.get("domain"),
        enabled=as_bool(params, "enabled", False),
    )
    return await _run_service_response(
        settings_service.create_webhook_setting,
        payload.model_dump(),
        status_code=201,
    )


@router.delete("/api/v1/webhooks/{webhook_id}")
async def delete_webhook_setting(webhook_id: str):
    response = await _run_service_response(settings_service.delete_webhook_setting, webhook_id)
    if response.status_code != 200:
        return response
    return Response(status_code=204)


@router.post("/api/v1/webhook-tests")
async def post_webhook_delivery_test(request: Request):
    params = await request_params(request)
    payload = WebhookPayload(
        provider=params.get("provider"),
        webhook_url=params.get("webhook_url"),
        secret=params.get("secret"),
        domain=params.get("domain"),
        enabled=as_bool(params, "enabled", False),
    )
    return await _run_service_response(
        settings_service.test_webhook_delivery,
        payload.model_dump(),
        status_code=201,
    )
