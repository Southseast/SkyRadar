# coding: utf-8
# @File        : service.py
# @Author      : NanMing
# @Date        : 2026/6/11 17:44
# @Description : Implements settings service logic.

import hashlib
import os
import signal
import time
from urllib.parse import urlparse

from api.settings import repository as setting_repository
from integrations import dingtalk as dingtalk_integration
from integrations import feishu as feishu_integration
from integrations import github as github_integration


WEBHOOK_PROVIDERS = {"dingtalk", "feishu"}


def public_webhook_setting(item):
    public_item = dict(item)
    webhook = public_item.get("webhook")
    provider = public_item.get("provider")
    if webhook:
        if provider == "feishu":
            public_item["webhook_url"] = feishu_integration.mask_feishu_webhook_url(webhook)
        else:
            public_item["webhook_url"] = dingtalk_integration.mask_dingtalk_webhook_url(webhook)
        public_item["webhook_hash"] = hashlib.md5(
            str(webhook).encode("utf-8")
        ).hexdigest()
    public_item["provider"] = provider
    public_item.pop("webhook", None)
    public_item["has_secret"] = bool(public_item.get("secret"))
    public_item.pop("secret", None)
    return public_item


def get_cron():
    result = setting_repository.get_task_setting({"_id": 0})
    if result:
        return {"status": 200, "msg": "获取信息成功", "result": result}
    return {"status": 400, "msg": "请配置查询页数和周期", "result": result}


def post_cron(page, minute):
    setting_repository.upsert_task_setting(page, minute)
    try:
        os.kill(setting_repository.get_task_setting().get("pid"), signal.SIGHUP)
    except ProcessLookupError:
        pass
    result = setting_repository.list_settings({"_id": 0})
    return {"status": 201, "msg": "设置成功", "result": result}


def get_github_accounts():
    result = setting_repository.list_github_accounts()
    return {"status": 200, "msg": "获取信息成功", "result": result}


def post_github_account(username, password):
    try:
        github = github_integration.create_client(username, password)
        rate = github_integration.search_rate_limit(github)
        setting_repository.save_github_account(
            {
                "_id": hashlib.md5(username.encode("utf-8")).hexdigest(),
                "username": username,
                "password": password,
                "mask_password": password.replace("".join(password[2:-2]), "****"),
                "addat": int(time.time()),
                "rate_limit": rate["limit"],
                "rate_remaining": rate["remaining"],
            }
        )
        result = setting_repository.list_github_accounts()
        return {"status": 201, "msg": "添加成功", "result": result}
    except github_integration.BadCredentialsException:
        return {"status": 401, "msg": "认证失败，请检查账号是否可用", "result": []}


def delete_github_account(username=None):
    setting_repository.delete_github_account(username)
    result = setting_repository.list_github_accounts()
    return {"status": 404, "msg": "删除成功", "result": result}


def get_query():
    result = setting_repository.list_queries()
    return {"status": 200, "msg": "获取信息成功", "result": result}


def post_query(keyword, tag, enabled=True):
    args = {"keyword": keyword, "tag": tag, "enabled": enabled}
    if setting_repository.query_exists(args.get("tag")):
        setting_repository.update_query(args.get("tag"), args)
        msg = "更新成功"
    else:
        new_query = dict(args)
        new_query["_id"] = hashlib.md5(
            "".join([str(value) for value in new_query.values()]).encode("utf-8")
        ).hexdigest()
        setting_repository.insert_query(new_query)
        msg = "添加成功"
    result = setting_repository.list_queries()
    return {"status": 200, "msg": msg, "result": result}


def delete_query(_id=None, tag=None):
    setting_repository.delete_query(_id)
    setting_repository.delete_results_by_tag(tag)
    result = setting_repository.list_queries()
    return {"status": 404, "msg": "删除成功", "result": result}


def get_blacklist():
    result = setting_repository.list_blacklist()
    return {"status": 200, "msg": "获取信息成功", "result": result}


def post_blacklist(text):
    normalized = text.strip().replace(" ", "")
    setting_repository.save_blacklist(
        {
            "_id": hashlib.md5(normalized.encode("utf-8")).hexdigest(),
            "text": normalized,
        }
    )
    result = setting_repository.list_blacklist()
    return {"status": 201, "msg": "添加成功", "result": result}


def delete_blacklist(text=None):
    setting_repository.delete_blacklist(text)
    result = setting_repository.list_blacklist()
    return {"status": 404, "msg": "删除成功", "result": result}


def get_notice():
    result = setting_repository.list_notices()
    return {"status": 200, "msg": "获取信息成功", "result": result}


def post_notice(mail):
    normalized = mail.strip().replace(" ", "")
    setting_repository.insert_notice(
        {
            "_id": hashlib.md5(normalized.encode("utf-8")).hexdigest(),
            "mail": normalized,
        }
    )
    result = setting_repository.list_notices()
    return {"status": 201, "msg": "添加成功", "result": result}


def delete_notice(mail=None):
    setting_repository.delete_notice(mail)
    result = setting_repository.list_notices()
    return {"status": 404, "msg": "删除成功", "result": result}


def get_mail():
    result = setting_repository.get_mail_setting()
    return {"status": 200, "msg": "获取信息成功", "result": result}


def post_mail(setting):
    if not setting.get("password"):
        setting.pop("password", None)
    setting_repository.upsert_mail_setting(setting)
    result = setting_repository.get_mail_setting()
    return {"status": 201, "msg": "设置成功", "result": result}


def get_webhook():
    result = [public_webhook_setting(item) for item in setting_repository.list_webhook_settings()]
    return {"status": 200, "msg": "获取信息成功", "result": result}


def _validate_webhook(provider, webhook):
    if provider not in WEBHOOK_PROVIDERS:
        return "不支持的 webhook 类型"
    if not webhook:
        return "请输入 webhook 地址"
    parsed_webhook = urlparse(webhook)
    if parsed_webhook.scheme != "https":
        return "错误的 webhook 地址"
    if provider == "dingtalk" and not dingtalk_integration.is_dingtalk_webhook(webhook):
        return "错误的钉钉 webhook 地址"
    if provider == "feishu" and not feishu_integration.is_feishu_webhook(webhook):
        return "错误的飞书 webhook 地址"
    return None


def _build_webhook_test_payload(provider, domain, secret):
    if provider == "feishu":
        return feishu_integration.build_feishu_test_payload(domain, secret=secret)
    return dingtalk_integration.build_dingtalk_test_payload(domain)


def _post_webhook(provider, webhook, secret, content):
    if provider == "feishu":
        return feishu_integration.post_feishu_text(webhook, secret, content, timeout=10)
    return dingtalk_integration.post_dingtalk_markdown(webhook, secret, content, timeout=10)


def _webhook_test_succeeded(provider, response):
    if provider == "feishu":
        return response.ok and response.json().get("code") == 0
    return response.ok and response.json().get("errmsg") == "ok"


def _webhook_response_message(provider, response):
    try:
        payload = response.json()
    except ValueError:
        return response.text
    if provider == "feishu":
        return payload.get("msg") or payload.get("StatusMessage") or str(payload)
    return payload.get("errmsg") or str(payload)


def post_webhook(params):
    provider = params.get("provider")
    webhook = params.get("webhook_url")
    secret = (params.get("secret") or "").strip()
    validation_error = _validate_webhook(provider, webhook)
    if validation_error:
        return {"status": 400, "msg": validation_error, "result": []}
    if not secret:
        return {"status": 400, "msg": "webhook 必须配置加签 Secret", "result": []}

    args = {
        "provider": provider,
        "webhook": webhook,
        "secret": secret,
        "domain": params.get("domain"),
        "enabled": params.get("enabled", False),
        "test": params.get("test", False),
    }
    if args.get("test"):
        test_content = _build_webhook_test_payload(provider, args.get("domain"), secret)
        webhook_response = _post_webhook(provider, webhook, secret, test_content)
        if webhook_response.ok:
            if _webhook_test_succeeded(provider, webhook_response):
                return {"status": 201, "msg": "已发送，请前往目标群查看", "result": []}
            return {
                "status": 400,
                "msg": "发送失败，WebHook 响应: {}".format(_webhook_response_message(provider, webhook_response)),
                "result": [],
            }
        return {"status": 400, "msg": "发送失败，请检查服务器网络", "result": []}

    args.pop("test")
    setting_repository.upsert_webhook_setting(args.get("webhook"), args)
    result = setting_repository.count_webhook_setting(args.get("webhook"))
    if result > 0:
        return {"status": 201, "msg": "设置成功", "result": result}
    return {"status": 400, "msg": "设置失败", "result": result}


def delete_webhook(webhook_url=None, webhook_hash=None):
    webhook = webhook_url
    if webhook_hash and not webhook:
        webhook = setting_repository.find_webhook_url_by_hash(webhook_hash)
    delete_result = setting_repository.delete_webhook_setting(webhook)
    if delete_result.deleted_count == 1:
        return {"status": 200, "msg": "删除成功", "result": []}
    return {"status": 404, "msg": "删除失败", "result": []}
