# coding: utf-8
# @File        : test_settings_contract.py
# @Author      : NanMing
# @Date        : 2026/6/10 13:48
# @Description : Tests settings persistence contract behavior.

import hashlib
import signal
from urllib.parse import parse_qs, urlparse


class FakeCursor:
    def __init__(self, documents):
        self.documents = documents
        self.calls = []

    def sort(self, field, direction):
        self.calls.append(("sort", field, direction))
        return self

    def __iter__(self):
        return iter(self.documents)


class FakeDeleteResult:
    def __init__(self, deleted_count):
        self.deleted_count = deleted_count


def _project(document, projection):
    projected = dict(document)
    for field, enabled in projection.items():
        if enabled == 0:
            projected.pop(field, None)
    return projected


def test_task_settings_get_returns_current_setting(client, monkeypatch):
    from api.settings import repository as setting

    captured = {}
    task_setting = {"key": "task", "page": 10, "minute": 30, "pid": 12345}

    class FakeSettingCollection:
        def find_one(self, filters, projection):
            captured["filters"] = filters
            captured["projection"] = projection
            return _project(task_setting, projection)

    monkeypatch.setattr(setting, "setting_col", FakeSettingCollection())

    response = client.get("/api/v1/task-schedules/current")

    assert response.status_code == 200
    assert response.get_json() == {
        "data": {"key": "task", "page": 10, "minute": 30, "pid": 12345}
    }
    assert captured == {"filters": {"key": "task"}, "projection": {"_id": 0}}


def test_task_settings_get_returns_404_when_missing(client, monkeypatch):
    from api.settings import repository as setting

    class FakeSettingCollection:
        def find_one(self, filters, projection):
            return None

    monkeypatch.setattr(setting, "setting_col", FakeSettingCollection())

    response = client.get("/api/v1/task-schedules/current")

    assert response.status_code == 404
    assert response.get_json() == {
        "error": "settings_error",
        "message": "task settings are not configured",
    }


def test_task_settings_put_upserts_and_sends_sighup(client, monkeypatch):
    from api.settings import repository as setting
    from api.settings import service as settings_service

    captured = {}
    stored_document = {"key": "task", "pid": 12345}

    class FakeSettingCollection:
        def update_many(self, filters, update, upsert=False):
            captured["update_filters"] = filters
            captured["update"] = update
            captured["upsert"] = upsert
            stored_document.update(update["$set"])

        def find_one(self, filters, projection=None):
            captured.setdefault("find_one_calls", []).append((filters, projection))
            if projection is None:
                return stored_document
            return _project(stored_document, projection)

    def fake_kill(pid, sig):
        captured["kill"] = (pid, sig)

    monkeypatch.setattr(setting, "setting_col", FakeSettingCollection())
    monkeypatch.setattr(settings_service.os, "kill", fake_kill)

    response = client.put("/api/v1/task-schedules/current", json={"page": 20, "minute": 5})

    assert response.status_code == 200
    assert response.get_json() == {
        "data": {"key": "task", "pid": 12345, "page": 20, "minute": 5}
    }
    assert captured["update_filters"] == {"key": "task"}
    assert captured["update"] == {"$set": {"key": "task", "page": 20, "minute": 5}}
    assert captured["upsert"] is True
    assert captured["kill"] == (12345, signal.SIGHUP)
    assert captured["find_one_calls"] == [
        ({"key": "task"}, None),
        ({"key": "task"}, {"_id": 0}),
    ]


def test_search_rules_get_sorts_enabled_desc(client, monkeypatch):
    from api.settings import repository as setting

    captured = {}
    cursor = FakeCursor(
        [
            {"_id": "query-1", "keyword": "token", "tag": "token", "enabled": True},
            {"_id": "query-2", "keyword": "key", "tag": "key", "enabled": False},
        ]
    )

    class FakeQueryCollection:
        def find(self, filters):
            captured["filters"] = filters
            return cursor

    monkeypatch.setattr(setting, "query_col", FakeQueryCollection())

    response = client.get("/api/v1/search-rules")

    assert response.status_code == 200
    assert response.get_json() == {
        "data": [
            {"_id": "query-1", "keyword": "token", "tag": "token", "enabled": True},
            {"_id": "query-2", "keyword": "key", "tag": "key", "enabled": False},
        ]
    }
    assert captured["filters"] == {}
    assert cursor.calls == [("sort", "enabled", -1)]


def test_search_rule_post_inserts_new_rule(client, monkeypatch):
    from api.settings import repository as setting

    captured = {}

    class FakeQueryCollection:
        def count_documents(self, filters):
            captured["count_filters"] = filters
            return 0

        def insert_one(self, document):
            captured["inserted"] = dict(document)

    monkeypatch.setattr(setting, "query_col", FakeQueryCollection())

    response = client.post(
        "/api/v1/search-rules",
        json={"keyword": "github token", "tag": "github-token", "enabled": True},
    )

    body = response.get_json()
    assert response.status_code == 201
    assert body["data"] == captured["inserted"]
    assert body["data"]["keyword"] == "github token"
    assert body["data"]["tag"] == "github-token"
    assert body["data"]["enabled"] is True
    assert "_id" in body["data"]
    assert captured["count_filters"] == {"tag": "github-token"}


def test_search_rule_post_accepts_form_urlencoded(client, monkeypatch):
    from api.settings import repository as setting

    captured = {}

    class FakeQueryCollection:
        def count_documents(self, filters):
            captured["count_filters"] = filters
            return 0

        def insert_one(self, document):
            captured["inserted"] = dict(document)

    monkeypatch.setattr(setting, "query_col", FakeQueryCollection())

    response = client.post(
        "/api/v1/search-rules",
        data={"keyword": "github token", "tag": "github-token-form", "enabled": "true"},
    )

    assert response.status_code == 201
    assert response.get_json()["data"]["tag"] == "github-token-form"
    assert response.get_json()["data"]["enabled"] is True
    assert captured["count_filters"] == {"tag": "github-token-form"}


def test_search_rule_post_returns_409_for_duplicate_tag(client, monkeypatch):
    from api.settings import repository as setting

    class FakeQueryCollection:
        def count_documents(self, filters):
            return 1

        def insert_one(self, document):
            raise AssertionError("duplicate tags must not be inserted")

    monkeypatch.setattr(setting, "query_col", FakeQueryCollection())

    response = client.post(
        "/api/v1/search-rules",
        json={"keyword": "github token", "tag": "github-token", "enabled": True},
    )

    assert response.status_code == 409
    assert response.get_json() == {
        "error": "settings_error",
        "message": "search rule tag already exists",
    }


def test_search_rule_put_updates_existing_rule(client, monkeypatch):
    from api.settings import repository as setting

    captured = {}

    class FakeQueryCollection:
        def count_documents(self, filters):
            captured["count_filters"] = filters
            return 1

        def update_one(self, filters, update):
            captured["update_filters"] = filters
            captured["update"] = update

    monkeypatch.setattr(setting, "query_col", FakeQueryCollection())

    response = client.put(
        "/api/v1/search-rules/github-token",
        json={"keyword": "changed token", "enabled": False},
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "data": {"keyword": "changed token", "tag": "github-token", "enabled": False}
    }
    assert captured["count_filters"] == {"tag": "github-token"}
    assert captured["update_filters"] == {"tag": "github-token"}
    assert captured["update"] == {
        "$set": {"keyword": "changed token", "tag": "github-token", "enabled": False}
    }


def test_search_rule_delete_removes_rule_and_matching_results(client, monkeypatch):
    from api.settings import repository as setting

    captured = {}

    class FakeQueryCollection:
        def delete_many(self, filters):
            captured["query_delete_filters"] = filters
            return FakeDeleteResult(1)

    class FakeResultCollection:
        def delete_many(self, filters):
            captured["result_delete_filters"] = filters

    monkeypatch.setattr(setting, "query_col", FakeQueryCollection())
    monkeypatch.setattr(setting, "result_col", FakeResultCollection())

    response = client.delete("/api/v1/search-rules/obsolete-token")

    assert response.status_code == 204
    assert response.data == b""
    assert captured == {
        "query_delete_filters": {"tag": "obsolete-token"},
        "result_delete_filters": {"tag": "obsolete-token"},
    }


def test_blacklist_post_strips_spaces_and_returns_created_item(client, monkeypatch):
    from api.settings import repository as setting

    captured = {}

    class FakeBlacklistCollection:
        def replace_one(self, filters, document, upsert=False):
            captured["replace_filters"] = filters
            captured["saved_document"] = document
            captured["upsert"] = upsert

    monkeypatch.setattr(setting, "blacklist_col", FakeBlacklistCollection())

    response = client.post("/api/v1/blacklist-items", json={"text": " blocked value "})

    assert response.status_code == 201
    assert response.get_json() == {"data": {"text": "blockedvalue"}}
    assert captured["replace_filters"] == {"_id": "42ec172949110ef0976d07c6009ecb0d"}
    assert captured["upsert"] is True
    assert captured["saved_document"]["text"] == "blockedvalue"


def test_blacklist_delete_uses_path_value(client, monkeypatch):
    from api.settings import repository as setting

    captured = {}

    class FakeBlacklistCollection:
        def delete_many(self, filters):
            captured["delete_filters"] = filters
            return FakeDeleteResult(1)

    monkeypatch.setattr(setting, "blacklist_col", FakeBlacklistCollection())

    response = client.delete("/api/v1/blacklist-items/obsolete-secret")

    assert response.status_code == 204
    assert captured == {"delete_filters": {"text": "obsolete-secret"}}


def test_notification_recipients_get_returns_recipient_list(client, monkeypatch):
    from api.settings import repository as setting

    captured = {}

    class FakeNoticeCollection:
        def find(self, filters, projection):
            captured["filters"] = filters
            captured["projection"] = projection
            return [{"mail": "security@example.com"}]

    monkeypatch.setattr(setting, "notice_col", FakeNoticeCollection())

    response = client.get("/api/v1/notification-recipients")

    assert response.status_code == 200
    assert response.get_json() == {"data": [{"mail": "security@example.com"}]}
    assert captured == {"filters": {}, "projection": {"_id": 0}}


def test_notification_recipient_post_adds_normalized_mail(client, monkeypatch):
    from api.settings import repository as setting

    captured = {}

    class FakeNoticeCollection:
        def insert_one(self, document):
            captured["inserted"] = dict(document)

    monkeypatch.setattr(setting, "notice_col", FakeNoticeCollection())

    response = client.post(
        "/api/v1/notification-recipients",
        json={"mail": " security @ example.com "},
    )

    assert response.status_code == 201
    assert response.get_json() == {"data": {"mail": "security@example.com"}}
    assert captured["inserted"]["mail"] == "security@example.com"


def test_notification_recipient_delete_uses_path_mail(client, monkeypatch):
    from api.settings import repository as setting

    captured = {}

    class FakeNoticeCollection:
        def delete_many(self, filters):
            captured["delete_filters"] = filters
            return FakeDeleteResult(1)

    monkeypatch.setattr(setting, "notice_col", FakeNoticeCollection())

    response = client.delete("/api/v1/notification-recipients/previous@example.com")

    assert response.status_code == 204
    assert captured == {"delete_filters": {"mail": "previous@example.com"}}


def test_webhook_get_returns_masked_provider_list(client, monkeypatch):
    from api.settings import repository as setting

    captured = {}
    webhook_url = "https://oapi.dingtalk.com/robot/send?access_token=example"

    class FakeSettingCollection:
        def find(self, filters, projection):
            captured["filters"] = filters
            captured["projection"] = projection
            return [
                {
                    "provider": "dingtalk",
                    "webhook": webhook_url,
                    "secret": "SEC-example",
                    "domain": "https://skyradar.example.com",
                    "enabled": True,
                }
            ]

    monkeypatch.setattr(setting, "setting_col", FakeSettingCollection())

    response = client.get("/api/v1/webhooks")

    assert response.status_code == 200
    assert response.get_json() == {
        "data": [
            {
                "provider": "dingtalk",
                "webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=***",
                "webhook_id": hashlib.md5(str(webhook_url).encode("utf-8")).hexdigest(),
                "domain": "https://skyradar.example.com",
                "enabled": True,
                "has_secret": True,
            }
        ]
    }
    assert captured == {
        "filters": {"webhook": {"$exists": True}, "provider": {"$exists": True}},
        "projection": {"_id": 0},
    }


def test_webhook_post_rejects_invalid_url(client, monkeypatch):
    from api.settings import repository as setting
    from integrations import dingtalk as dingtalk_integration

    captured = {"requests_post_calls": 0}

    class FakeSettingCollection:
        def update_one(self, *args, **kwargs):
            raise AssertionError("invalid webhook URL must not be saved")

    def fake_requests_post(*args, **kwargs):
        captured["requests_post_calls"] += 1
        raise AssertionError("invalid webhook URL must not be tested")

    monkeypatch.setattr(setting, "setting_col", FakeSettingCollection())
    monkeypatch.setattr(dingtalk_integration.requests, "post", fake_requests_post)

    response = client.post(
        "/api/v1/webhooks",
        json={
            "webhook_url": "http://example.com/robot/send",
            "provider": "dingtalk",
            "secret": "SEC-example",
            "domain": "https://skyradar.example.com",
            "enabled": True,
        },
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "settings_error",
        "message": "webhook_url must be an https URL",
    }
    assert captured["requests_post_calls"] == 0


def test_webhook_post_saves_valid_url_without_test_call(client, monkeypatch):
    from api.settings import repository as setting
    from integrations import dingtalk as dingtalk_integration

    captured = {"requests_post_calls": 0}

    class FakeSettingCollection:
        def update_one(self, filters, update, upsert=False):
            captured["update_filters"] = filters
            captured["update"] = update
            captured["upsert"] = upsert

        def count_documents(self, filters):
            captured["count_filters"] = filters
            return 1

    def fake_requests_post(*args, **kwargs):
        captured["requests_post_calls"] += 1
        raise AssertionError("saving webhook settings must not call requests.post")

    monkeypatch.setattr(setting, "setting_col", FakeSettingCollection())
    monkeypatch.setattr(dingtalk_integration.requests, "post", fake_requests_post)

    webhook_url = "https://oapi.dingtalk.com/robot/send?access_token=example"
    response = client.post(
        "/api/v1/webhooks",
        json={
            "provider": "dingtalk",
            "webhook_url": webhook_url,
            "secret": "SEC-example",
            "domain": "https://skyradar.example.com",
            "enabled": True,
        },
    )

    assert response.status_code == 201
    assert response.get_json() == {
        "data": {
            "provider": "dingtalk",
            "webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=***",
            "webhook_id": hashlib.md5(str(webhook_url).encode("utf-8")).hexdigest(),
            "domain": "https://skyradar.example.com",
            "enabled": True,
            "has_secret": True,
        }
    }
    assert captured["update_filters"] == {"webhook": webhook_url}
    assert captured["update"] == {
        "$set": {
            "provider": "dingtalk",
            "webhook": webhook_url,
            "secret": "SEC-example",
            "domain": "https://skyradar.example.com",
            "enabled": True,
        }
    }
    assert captured["upsert"] is True
    assert captured["count_filters"] == {"webhook": webhook_url}
    assert captured["requests_post_calls"] == 0


def test_webhook_delivery_test_posts_dingtalk_provider(client, monkeypatch):
    from integrations import dingtalk as dingtalk_integration

    captured = {}
    webhook_url = "https://oapi.dingtalk.com/robot/send?access_token=example"

    class FakeResponse:
        ok = True

        def json(self):
            return {"errmsg": "ok"}

    def fake_requests_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(dingtalk_integration.requests, "post", fake_requests_post)

    response = client.post(
        "/api/v1/webhook-tests",
        json={
            "provider": "dingtalk",
            "webhook_url": webhook_url,
            "secret": "SEC-example",
            "domain": "https://skyradar.example.com",
            "enabled": True,
        },
    )

    parsed_url = urlparse(captured["url"])
    query = parse_qs(parsed_url.query)

    assert response.status_code == 201
    assert response.get_json() == {"data": {"delivered": True, "provider": "dingtalk"}}
    assert parsed_url.scheme == "https"
    assert parsed_url.netloc == "oapi.dingtalk.com"
    assert parsed_url.path == "/robot/send"
    assert query["access_token"] == ["example"]
    assert query["timestamp"]
    assert query["sign"]
    assert captured["json"]["msgtype"] == "markdown"
    assert captured["json"]["markdown"]["title"] == "SkyRadar 通知测试"
    assert "钉钉 webhook" in captured["json"]["markdown"]["text"]
    assert captured["timeout"] == 10


def test_webhook_delivery_test_posts_feishu_provider(client, monkeypatch):
    from integrations import feishu as feishu_integration

    captured = {}

    class FakeResponse:
        ok = True

        def json(self):
            return {"code": 0, "msg": "success"}

    def fake_requests_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(feishu_integration.requests, "post", fake_requests_post)

    response = client.post(
        "/api/v1/webhook-tests",
        json={
            "provider": "feishu",
            "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/example",
            "secret": "SEC-example",
            "domain": "https://skyradar.example.com",
            "enabled": True,
        },
    )

    assert response.status_code == 201
    assert response.get_json() == {"data": {"delivered": True, "provider": "feishu"}}
    assert captured["url"] == "https://open.feishu.cn/open-apis/bot/v2/hook/example"
    assert captured["json"]["msg_type"] == "text"
    assert captured["json"]["timestamp"]
    assert captured["json"]["sign"]
    assert captured["timeout"] == 10


def test_webhook_delete_accepts_webhook_id(client, monkeypatch):
    from api.settings import repository as setting

    captured = {}
    webhook_url = "https://oapi.dingtalk.com/robot/send?access_token=example"
    webhook_id = hashlib.md5(str(webhook_url).encode("utf-8")).hexdigest()

    class FakeSettingCollection:
        def find(self, filters, projection):
            captured["find_filters"] = filters
            captured["projection"] = projection
            return [{"provider": "dingtalk", "webhook": webhook_url, "secret": "SEC-example"}]

        def delete_one(self, filters):
            captured["delete_filters"] = filters
            return FakeDeleteResult(1)

    monkeypatch.setattr(setting, "setting_col", FakeSettingCollection())

    response = client.delete(f"/api/v1/webhooks/{webhook_id}")

    assert response.status_code == 204
    assert response.data == b""
    assert captured["find_filters"] == {"webhook": {"$exists": True}, "provider": {"$exists": True}}
    assert captured["projection"] == {"_id": 0}
    assert captured["delete_filters"] == {"webhook": webhook_url}
