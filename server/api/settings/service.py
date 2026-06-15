# coding: utf-8
# @File        : service.py
# @Author      : NanMing
# @Date        : 2026/6/11 17:44
# @Description : Implements settings service logic.

import hashlib
import time
from urllib.parse import urlparse

from api.notifications import messages as notification_messages
from api.settings import repository as setting_repository
from integrations import dingtalk as dingtalk_integration
from integrations import feishu as feishu_integration
from integrations import github as github_integration


WEBHOOK_PROVIDERS = {"dingtalk", "feishu"}
TASK_SETTING_INTERNAL_FIELDS = {"next_due_at", "last_scheduled_at"}


class SettingsServiceError(Exception):
    def __init__(self, status_code, message):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def _require_text(value, field_name):
    if value is None or not str(value).strip():
        raise SettingsServiceError(400, f"{field_name} is required")
    return str(value)


def _normalized_text(value, field_name):
    return _require_text(value, field_name).strip().replace(" ", "")


def _mask_secret(value):
    value = str(value)
    if len(value) <= 4:
        return "****"
    return f"{value[:2]}****{value[-2:]}"


def public_webhook_setting(item):
    public_item = dict(item)
    webhook = public_item.get("webhook")
    provider = public_item.get("provider")
    if webhook:
        if provider == "feishu":
            public_item["webhook_url"] = feishu_integration.mask_feishu_webhook_url(webhook)
        else:
            public_item["webhook_url"] = dingtalk_integration.mask_dingtalk_webhook_url(webhook)
        public_item["webhook_id"] = hashlib.md5(str(webhook).encode("utf-8")).hexdigest()
    public_item["provider"] = provider
    public_item.pop("webhook", None)
    public_item["has_secret"] = bool(public_item.get("secret"))
    public_item.pop("secret", None)
    return public_item


def get_task_settings():
    result = setting_repository.get_task_setting({"_id": 0})
    if not result:
        raise SettingsServiceError(404, "task settings are not configured")
    for field in TASK_SETTING_INTERNAL_FIELDS:
        result.pop(field, None)
    return result


def put_task_settings(page, minute):
    setting_repository.upsert_task_setting(page, minute, int(time.time()))
    return get_task_settings()


def get_github_accounts():
    return setting_repository.list_github_accounts()


def create_github_account(username, password):
    username = _require_text(username, "username")
    password = _require_text(password, "password")
    try:
        github = github_integration.create_client(username, password)
        rate = github_integration.search_rate_limit(github)
    except github_integration.BadCredentialsException as error:
        raise SettingsServiceError(401, "GitHub credentials are invalid") from error

    document = {
        "_id": hashlib.md5(username.encode("utf-8")).hexdigest(),
        "username": username,
        "password": password,
        "mask_password": _mask_secret(password),
        "addat": int(time.time()),
        "rate_limit": rate["limit"],
        "rate_remaining": rate["remaining"],
    }
    setting_repository.save_github_account(document)
    public_document = dict(document)
    public_document.pop("_id", None)
    public_document.pop("password", None)
    return public_document


def delete_github_account(username):
    username = _require_text(username, "username")
    delete_result = setting_repository.delete_github_account(username)
    if getattr(delete_result, "deleted_count", 0) == 0:
        raise SettingsServiceError(404, "GitHub account was not found")
    return None


def get_search_rules():
    return setting_repository.list_queries()


def create_search_rule(keyword, tag, enabled=True):
    keyword = _require_text(keyword, "keyword")
    tag = _require_text(tag, "tag")
    if setting_repository.query_exists(tag):
        raise SettingsServiceError(409, "search rule tag already exists")
    document = {"keyword": keyword, "tag": tag, "enabled": enabled}
    document["_id"] = hashlib.md5("".join([str(value) for value in document.values()]).encode("utf-8")).hexdigest()
    setting_repository.insert_query(document)
    return document


def put_search_rule(tag, keyword, enabled=True):
    tag = _require_text(tag, "tag")
    keyword = _require_text(keyword, "keyword")
    if not setting_repository.query_exists(tag):
        raise SettingsServiceError(404, "search rule was not found")
    values = {"keyword": keyword, "tag": tag, "enabled": enabled}
    setting_repository.update_query(tag, values)
    return values


def delete_search_rule(tag):
    tag = _require_text(tag, "tag")
    delete_result = setting_repository.delete_query_by_tag(tag)
    if getattr(delete_result, "deleted_count", 0) == 0:
        raise SettingsServiceError(404, "search rule was not found")
    setting_repository.delete_results_by_tag(tag)
    return None


def get_blacklist_items():
    return setting_repository.list_blacklist()


def create_blacklist_item(text):
    normalized = _normalized_text(text, "text")
    document = {
        "_id": hashlib.md5(normalized.encode("utf-8")).hexdigest(),
        "text": normalized,
    }
    setting_repository.save_blacklist(document)
    return {"text": normalized}


def delete_blacklist_item(text):
    normalized = _normalized_text(text, "text")
    delete_result = setting_repository.delete_blacklist(normalized)
    if getattr(delete_result, "deleted_count", 0) == 0:
        raise SettingsServiceError(404, "blacklist item was not found")
    return None


def get_notification_recipients():
    return setting_repository.list_notices()


def create_notification_recipient(mail):
    normalized = _normalized_text(mail, "mail")
    document = {
        "_id": hashlib.md5(normalized.encode("utf-8")).hexdigest(),
        "mail": normalized,
    }
    setting_repository.insert_notice(document)
    return {"mail": normalized}


def delete_notification_recipient(mail):
    normalized = _normalized_text(mail, "mail")
    delete_result = setting_repository.delete_notice(normalized)
    if getattr(delete_result, "deleted_count", 0) == 0:
        raise SettingsServiceError(404, "notification recipient was not found")
    return None


def get_mail_settings():
    return setting_repository.get_mail_setting()


def put_mail_settings(setting):
    values = dict(setting)
    if not values.get("password"):
        values.pop("password", None)
    setting_repository.upsert_mail_setting(values)
    return setting_repository.get_mail_setting()


def get_webhook_settings():
    return [public_webhook_setting(item) for item in setting_repository.list_webhook_settings()]


def _validate_webhook(provider, webhook):
    if provider not in WEBHOOK_PROVIDERS:
        return "unsupported webhook provider"
    if not webhook:
        return "webhook_url is required"
    parsed_webhook = urlparse(webhook)
    if parsed_webhook.scheme != "https":
        return "webhook_url must be an https URL"
    if provider == "dingtalk" and not dingtalk_integration.is_dingtalk_webhook(webhook):
        return "invalid DingTalk webhook URL"
    if provider == "feishu" and not feishu_integration.is_feishu_webhook(webhook):
        return "invalid Feishu webhook URL"
    return None


def _validated_webhook_args(params):
    provider = params.get("provider")
    webhook = params.get("webhook_url")
    secret = (params.get("secret") or "").strip()
    validation_error = _validate_webhook(provider, webhook)
    if validation_error:
        raise SettingsServiceError(400, validation_error)
    if not secret:
        raise SettingsServiceError(400, "webhook secret is required")
    return {
        "provider": provider,
        "webhook": webhook,
        "secret": secret,
        "domain": params.get("domain"),
        "enabled": params.get("enabled", False),
    }


def _build_webhook_test_payload(provider, domain):
    if provider == "feishu":
        return notification_messages.build_feishu_test_payload(domain)
    return notification_messages.build_dingtalk_test_payload(domain)


def _post_webhook(provider, webhook, secret, content):
    if provider == "feishu":
        return feishu_integration.post_feishu_webhook(webhook, secret, content, timeout=10)
    return dingtalk_integration.post_dingtalk_webhook(webhook, secret, content, timeout=10)


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


def create_webhook_setting(params):
    args = _validated_webhook_args(params)
    setting_repository.upsert_webhook_setting(args.get("webhook"), args)
    if setting_repository.count_webhook_setting(args.get("webhook")) == 0:
        raise SettingsServiceError(400, "webhook setting could not be saved")
    return public_webhook_setting(args)


def test_webhook_delivery(params):
    args = _validated_webhook_args(params)
    test_content = _build_webhook_test_payload(args.get("provider"), args.get("domain"))
    webhook_response = _post_webhook(
        args.get("provider"),
        args.get("webhook"),
        args.get("secret"),
        test_content,
    )
    if not webhook_response.ok:
        raise SettingsServiceError(400, "webhook delivery failed; check server network access")
    if not _webhook_test_succeeded(args.get("provider"), webhook_response):
        detail = _webhook_response_message(args.get("provider"), webhook_response)
        raise SettingsServiceError(400, f"webhook delivery failed: {detail}")
    return {"delivered": True, "provider": args.get("provider")}


def delete_webhook_setting(webhook_id):
    webhook_id = _require_text(webhook_id, "webhook_id")
    webhook = setting_repository.find_webhook_url_by_id(webhook_id)
    if not webhook:
        raise SettingsServiceError(404, "webhook setting was not found")
    delete_result = setting_repository.delete_webhook_setting(webhook)
    if getattr(delete_result, "deleted_count", 0) == 0:
        raise SettingsServiceError(404, "webhook setting was not found")
    return None
