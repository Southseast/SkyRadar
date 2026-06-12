# coding: utf-8
# @File        : test_settings_contract.py
# @Author      : NanMing
# @Date        : 2026/6/10 13:48
# @Description : Tests settings persistence contract behavior.

import hashlib
import signal


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


def test_cron_get_contract_returns_configured_task_setting(client, monkeypatch):
    from api.settings import repository as setting

    captured = {}
    task_setting = {"key": "task", "page": 10, "minute": 30, "pid": 12345}

    class FakeSettingCollection:
        def find_one(self, filters, projection):
            captured["filters"] = filters
            captured["projection"] = projection
            return _project(task_setting, projection)

    monkeypatch.setattr(setting, "setting_col", FakeSettingCollection())

    response = client.get("/api/setting/cron")

    assert response.status_code == 200
    assert response.get_json() == {
        "status": 200,
        "msg": "获取信息成功",
        "result": {"key": "task", "page": 10, "minute": 30, "pid": 12345},
    }
    assert captured == {"filters": {"key": "task"}, "projection": {"_id": 0}}


def test_cron_get_contract_returns_business_400_when_missing(client, monkeypatch):
    from api.settings import repository as setting

    captured = {}

    class FakeSettingCollection:
        def find_one(self, filters, projection):
            captured["filters"] = filters
            captured["projection"] = projection
            return None

    monkeypatch.setattr(setting, "setting_col", FakeSettingCollection())

    response = client.get("/api/setting/cron")

    assert response.status_code == 200
    assert response.get_json() == {
        "status": 400,
        "msg": "请配置查询页数和周期",
        "result": None,
    }
    assert captured == {"filters": {"key": "task"}, "projection": {"_id": 0}}


def test_cron_post_contract_upserts_and_sends_sighup(client, monkeypatch):
    from api.settings import repository as setting
    from api.settings import service as settings_service

    captured = {}
    stored_documents = [{"key": "task", "pid": 12345}]

    class FakeSettingCollection:
        def update_many(self, filters, update, upsert=False):
            captured["update_filters"] = filters
            captured["update"] = update
            captured["upsert"] = upsert
            stored_documents[0].update(update["$set"])

        def find_one(self, filters, projection=None):
            captured.setdefault("find_one_filters", []).append(filters)
            return stored_documents[0]

        def find(self, filters, projection):
            captured["find_filters"] = filters
            captured["projection"] = projection
            return [_project(document, projection) for document in stored_documents]

    def fake_kill(pid, sig):
        captured["kill"] = (pid, sig)

    monkeypatch.setattr(setting, "setting_col", FakeSettingCollection())
    monkeypatch.setattr(settings_service.os, "kill", fake_kill)

    response = client.post("/api/setting/cron", json={"page": 20, "minute": 5})

    assert response.status_code == 200
    assert response.get_json() == {
        "status": 201,
        "msg": "设置成功",
        "result": [{"key": "task", "pid": 12345, "page": 20, "minute": 5}],
    }
    assert captured["update_filters"] == {"key": "task"}
    assert captured["update"] == {
        "$set": {"key": "task", "page": 20, "minute": 5}
    }
    assert captured["upsert"] is True
    assert captured["find_one_filters"] == [{"key": "task"}]
    assert captured["kill"] == (12345, signal.SIGHUP)
    assert captured["find_filters"] == {}
    assert captured["projection"] == {"_id": 0}


def test_query_get_contract_sorts_enabled_desc(client, monkeypatch):
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

    response = client.get("/api/setting/query")

    assert response.status_code == 200
    assert response.get_json() == {
        "status": 200,
        "msg": "获取信息成功",
        "result": [
            {"_id": "query-1", "keyword": "token", "tag": "token", "enabled": True},
            {"_id": "query-2", "keyword": "key", "tag": "key", "enabled": False},
        ],
    }
    assert captured["filters"] == {}
    assert cursor.calls == [("sort", "enabled", -1)]


def test_query_post_contract_inserts_new_rule_and_sorts_result(client, monkeypatch):
    from api.settings import repository as setting

    captured = {}
    stored_documents = []
    cursor = FakeCursor(stored_documents)

    class FakeQueryCollection:
        def count_documents(self, filters):
            captured["count_filters"] = filters
            return 0

        def insert_one(self, document):
            captured["inserted"] = dict(document)
            stored_documents.append(dict(document))

        def find(self, filters):
            captured["find_filters"] = filters
            return cursor

    fake_collection = FakeQueryCollection()
    monkeypatch.setattr(setting, "query_col", fake_collection)

    response = client.post(
        "/api/setting/query",
        json={"keyword": "github token", "tag": "github-token", "enabled": True},
    )

    body = response.get_json()
    assert response.status_code == 200
    assert body["status"] == 200
    assert body["msg"] == "添加成功"
    assert body["result"] == [captured["inserted"]]
    assert captured["count_filters"] == {"tag": "github-token"}
    assert captured["inserted"]["keyword"] == "github token"
    assert captured["inserted"]["tag"] == "github-token"
    assert captured["inserted"]["enabled"] is True
    assert "_id" in captured["inserted"]
    assert captured["find_filters"] == {}
    assert cursor.calls == [("sort", "enabled", -1)]


def test_query_post_accepts_form_urlencoded_contract(client, monkeypatch):
    from api.settings import repository as setting

    captured = {}
    stored_documents = []
    cursor = FakeCursor(stored_documents)

    class FakeQueryCollection:
        def count_documents(self, filters):
            captured["count_filters"] = filters
            return 0

        def insert_one(self, document):
            captured["inserted"] = dict(document)
            stored_documents.append(dict(document))

        def find(self, filters):
            captured["find_filters"] = filters
            return cursor

    fake_collection = FakeQueryCollection()
    monkeypatch.setattr(setting, "query_col", fake_collection)

    response = client.post(
        "/api/setting/query",
        data={"keyword": "github token", "tag": "github-token-form", "enabled": "true"},
    )

    body = response.get_json()
    assert response.status_code == 200
    assert body["status"] == 200
    assert body["msg"] == "添加成功"
    assert captured["inserted"]["keyword"] == "github token"
    assert captured["inserted"]["tag"] == "github-token-form"
    assert captured["inserted"]["enabled"] is True
    assert captured["count_filters"] == {"tag": "github-token-form"}
    assert captured["find_filters"] == {}
    assert cursor.calls == [("sort", "enabled", -1)]


def test_query_post_contract_updates_existing_rule_and_sorts_result(client, monkeypatch):
    from api.settings import repository as setting

    captured = {}
    cursor = FakeCursor(
        [{"_id": "query-1", "keyword": "github token", "tag": "github-token", "enabled": False}]
    )

    class FakeQueryCollection:
        def count_documents(self, filters):
            captured["count_filters"] = filters
            return 1

        def update_one(self, filters, update):
            captured["update_filters"] = filters
            captured["update"] = update

        def find(self, filters):
            captured["find_filters"] = filters
            return cursor

    monkeypatch.setattr(setting, "query_col", FakeQueryCollection())

    response = client.post(
        "/api/setting/query",
        json={"keyword": "github token", "tag": "github-token", "enabled": False},
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "status": 200,
        "msg": "更新成功",
        "result": [
            {
                "_id": "query-1",
                "keyword": "github token",
                "tag": "github-token",
                "enabled": False,
            }
        ],
    }
    assert captured["count_filters"] == {"tag": "github-token"}
    assert captured["update_filters"] == {"tag": "github-token"}
    assert captured["update"] == {
        "$set": {"keyword": "github token", "tag": "github-token", "enabled": False}
    }
    assert captured["find_filters"] == {}
    assert cursor.calls == [("sort", "enabled", -1)]


def test_blacklist_post_contract_strips_spaces_and_returns_list(client, monkeypatch):
    from api.settings import repository as setting

    captured = {}
    stored_documents = []

    class FakeBlacklistCollection:
        def replace_one(self, filters, document, upsert=False):
            captured["replace_filters"] = filters
            captured["saved_document"] = document
            captured["upsert"] = upsert
            stored_documents.append(dict(document))

        def find(self, filters, projection):
            captured["find_filters"] = filters
            captured["projection"] = projection
            return [_project(document, projection) for document in stored_documents]

    fake_collection = FakeBlacklistCollection()
    monkeypatch.setattr(setting, "blacklist_col", fake_collection)

    response = client.post("/api/setting/blacklist", json={"text": " blocked value "})

    assert response.status_code == 200
    assert response.get_json() == {
        "status": 201,
        "msg": "添加成功",
        "result": [{"text": "blockedvalue"}],
    }
    assert captured["replace_filters"] == {"_id": "42ec172949110ef0976d07c6009ecb0d"}
    assert captured["upsert"] is True
    assert captured["saved_document"]["text"] == "blockedvalue"
    assert captured["find_filters"] == {}
    assert captured["projection"] == {"_id": 0}


def test_notice_get_contract_returns_recipient_list(client, monkeypatch):
    from api.settings import repository as setting

    captured = {}

    class FakeNoticeCollection:
        def find(self, filters, projection):
            captured["filters"] = filters
            captured["projection"] = projection
            return [{"mail": "security@example.com"}]

    monkeypatch.setattr(setting, "notice_col", FakeNoticeCollection())

    response = client.get("/api/setting/notice")

    assert response.status_code == 200
    assert response.get_json() == {
        "status": 200,
        "msg": "获取信息成功",
        "result": [{"mail": "security@example.com"}],
    }
    assert captured == {"filters": {}, "projection": {"_id": 0}}


def test_notice_post_contract_adds_recipient_from_json_without_external_calls(
    client, monkeypatch
):
    from api.settings import repository as setting

    captured = {}
    stored_documents = []

    class FakeNoticeCollection:
        def insert_one(self, document):
            captured["inserted"] = dict(document)
            stored_documents.append(dict(document))

        def find(self, filters, projection):
            captured["find_filters"] = filters
            captured["projection"] = projection
            return [_project(document, projection) for document in stored_documents]

    monkeypatch.setattr(setting, "notice_col", FakeNoticeCollection())

    response = client.post(
        "/api/setting/notice", json={"mail": " security @ example.com "}
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "status": 201,
        "msg": "添加成功",
        "result": [{"mail": "security@example.com"}],
    }
    assert captured["inserted"]["mail"] == "security@example.com"
    assert captured["find_filters"] == {}
    assert captured["projection"] == {"_id": 0}


def test_notice_delete_contract_preserves_query_args_and_404_body_status(
    client, monkeypatch
):
    from api.settings import repository as setting

    captured = {}

    class FakeNoticeCollection:
        def delete_many(self, filters):
            captured["delete_filters"] = filters

        def find(self, filters, projection):
            captured["find_filters"] = filters
            captured["projection"] = projection
            return [{"mail": "remaining@example.com"}]

    monkeypatch.setattr(setting, "notice_col", FakeNoticeCollection())

    response = client.delete("/api/setting/notice?mail=previous@example.com")

    assert response.status_code == 200
    assert response.get_json() == {
        "status": 404,
        "msg": "删除成功",
        "result": [{"mail": "remaining@example.com"}],
    }
    assert captured == {
        "delete_filters": {"mail": "previous@example.com"},
        "find_filters": {},
        "projection": {"_id": 0},
    }


def test_webhook_get_contract_returns_provider_list(client, monkeypatch):
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

    response = client.get("/api/setting/webhook")

    assert response.status_code == 200
    assert response.get_json() == {
        "status": 200,
        "msg": "获取信息成功",
        "result": [
            {
                "provider": "dingtalk",
                "webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=***",
                "webhook_hash": hashlib.md5(
                    str(webhook_url).encode("utf-8")
                ).hexdigest(),
                "domain": "https://skyradar.example.com",
                "enabled": True,
                "has_secret": True,
            }
        ],
    }
    assert captured == {
        "filters": {"webhook": {"$exists": True}, "provider": {"$exists": True}},
        "projection": {"_id": 0},
    }


def test_webhook_post_contract_rejects_invalid_url(client, monkeypatch):
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
        "/api/setting/webhook",
        json={
            "webhook_url": "http://example.com/robot/send",
            "provider": "dingtalk",
            "domain": "https://skyradar.example.com",
            "enabled": True,
            "test": False,
        },
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "status": 400,
        "msg": "错误的 webhook 地址",
        "result": [],
    }
    assert captured["requests_post_calls"] == 0

    response = client.post(
        "/api/setting/webhook",
        json={
            "webhook_url": "https://example.com/robot/send",
            "provider": "dingtalk",
            "secret": "SEC-example",
            "domain": "https://skyradar.example.com",
            "enabled": True,
            "test": False,
        },
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "status": 400,
        "msg": "错误的钉钉 webhook 地址",
        "result": [],
    }
    assert captured["requests_post_calls"] == 0


def test_webhook_post_contract_rejects_unknown_provider(client, monkeypatch):
    from api.settings import repository as setting

    class FakeSettingCollection:
        def update_one(self, *args, **kwargs):
            raise AssertionError("invalid webhook provider must not be saved")

    monkeypatch.setattr(setting, "setting_col", FakeSettingCollection())

    response = client.post(
        "/api/setting/webhook",
        json={
            "provider": "slack",
            "webhook_url": "https://hooks.slack.example/services/example",
            "secret": "SEC-example",
            "domain": "https://skyradar.example.com",
            "enabled": True,
            "test": False,
        },
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "status": 400,
        "msg": "不支持的 webhook 类型",
        "result": [],
    }


def test_webhook_post_contract_requires_secret(client, monkeypatch):
    from api.settings import repository as setting
    from integrations import dingtalk as dingtalk_integration

    captured = {"requests_post_calls": 0}

    class FakeSettingCollection:
        def update_one(self, *args, **kwargs):
            raise AssertionError("webhook URL without secret must not be saved")

    def fake_requests_post(*args, **kwargs):
        captured["requests_post_calls"] += 1
        raise AssertionError("webhook URL without secret must not be tested")

    monkeypatch.setattr(setting, "setting_col", FakeSettingCollection())
    monkeypatch.setattr(dingtalk_integration.requests, "post", fake_requests_post)

    response = client.post(
        "/api/setting/webhook",
        json={
            "provider": "dingtalk",
            "webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=example",
            "domain": "https://skyradar.example.com",
            "enabled": True,
            "test": False,
        },
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "status": 400,
        "msg": "webhook 必须配置加签 Secret",
        "result": [],
    }
    assert captured["requests_post_calls"] == 0


def test_webhook_post_contract_saves_valid_url_without_test_call(client, monkeypatch):
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
        raise AssertionError("saving with test=false must not call requests.post")

    fake_collection = FakeSettingCollection()
    monkeypatch.setattr(setting, "setting_col", fake_collection)
    monkeypatch.setattr(dingtalk_integration.requests, "post", fake_requests_post)

    webhook_url = "https://oapi.dingtalk.com/robot/send?access_token=example"
    response = client.post(
        "/api/setting/webhook",
        json={
            "provider": "dingtalk",
            "webhook_url": webhook_url,
            "secret": "SEC-example",
            "domain": "https://skyradar.example.com",
            "enabled": True,
            "test": False,
        },
    )

    assert response.status_code == 200
    assert response.get_json() == {"status": 201, "msg": "设置成功", "result": 1}
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


def test_webhook_post_contract_tests_feishu_provider(client, monkeypatch):
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
        "/api/setting/webhook",
        json={
            "provider": "feishu",
            "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/example",
            "secret": "SEC-example",
            "domain": "https://skyradar.example.com",
            "enabled": True,
            "test": True,
        },
    )

    assert response.status_code == 200
    assert response.get_json() == {"status": 201, "msg": "已发送，请前往目标群查看", "result": []}
    assert captured["url"] == "https://open.feishu.cn/open-apis/bot/v2/hook/example"
    assert captured["json"]["msg_type"] == "text"
    assert captured["json"]["timestamp"]
    assert captured["json"]["sign"]
    assert captured["timeout"] == 10


def test_webhook_delete_contract_returns_success_when_found(client, monkeypatch):
    from api.settings import repository as setting

    captured = {}
    webhook_url = "https://oapi.dingtalk.com/robot/send?access_token=example"

    class FakeSettingCollection:
        def delete_one(self, filters):
            captured["delete_filters"] = filters
            return FakeDeleteResult(1)

    monkeypatch.setattr(setting, "setting_col", FakeSettingCollection())

    response = client.delete(
        "/api/setting/webhook",
        query_string={"webhook_url": webhook_url},
    )

    assert response.status_code == 200
    assert response.get_json() == {"status": 200, "msg": "删除成功", "result": []}
    assert captured["delete_filters"] == {"webhook": webhook_url}


def test_webhook_delete_contract_accepts_webhook_hash(client, monkeypatch):
    from api.settings import repository as setting

    captured = {}
    webhook_url = "https://oapi.dingtalk.com/robot/send?access_token=example"

    class FakeSettingCollection:
        def find(self, filters, projection):
            captured["find_filters"] = filters
            captured["projection"] = projection
            return [{"provider": "dingtalk", "webhook": webhook_url, "secret": "SEC-example"}]

        def delete_one(self, filters):
            captured["delete_filters"] = filters
            return FakeDeleteResult(1)

    monkeypatch.setattr(setting, "setting_col", FakeSettingCollection())

    response = client.delete(
        "/api/setting/webhook",
        query_string={
            "webhook_hash": hashlib.md5(str(webhook_url).encode("utf-8")).hexdigest()
        },
    )

    assert response.status_code == 200
    assert response.get_json() == {"status": 200, "msg": "删除成功", "result": []}
    assert captured["find_filters"] == {"webhook": {"$exists": True}, "provider": {"$exists": True}}
    assert captured["projection"] == {"_id": 0}
    assert captured["delete_filters"] == {"webhook": webhook_url}


def test_webhook_delete_contract_returns_business_404_when_missing(
    client, monkeypatch
):
    from api.settings import repository as setting

    captured = {}
    webhook_url = "https://oapi.dingtalk.com/robot/send?access_token=missing"

    class FakeSettingCollection:
        def delete_one(self, filters):
            captured["delete_filters"] = filters
            return FakeDeleteResult(0)

    monkeypatch.setattr(setting, "setting_col", FakeSettingCollection())

    response = client.delete(
        "/api/setting/webhook",
        query_string={"webhook_url": webhook_url},
    )

    assert response.status_code == 200
    assert response.get_json() == {"status": 404, "msg": "删除失败", "result": []}
    assert captured["delete_filters"] == {"webhook": webhook_url}
