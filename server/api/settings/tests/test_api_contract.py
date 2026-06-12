# coding: utf-8
# @File        : test_api_contract.py
# @Author      : NanMing
# @Date        : 2026/6/9 14:37
# @Description : Tests settings API contract behavior.

class FakeCursor:
    def __init__(self, documents):
        self.documents = documents
        self.calls = []

    def sort(self, field, direction):
        self.calls.append(("sort", field, direction))
        return self

    def limit(self, value):
        self.calls.append(("limit", value))
        return self

    def skip(self, value):
        self.calls.append(("skip", value))
        return self

    def __iter__(self):
        return iter(self.documents)


def test_github_account_get_contract_excludes_password(client, monkeypatch):
    from api.settings import repository as setting

    captured = {}

    class FakeGithubCollection:
        def find(self, filters, projection):
            captured["filters"] = filters
            captured["projection"] = projection
            return [
                {
                    "username": "octocat",
                    "mask_password": "gh****ken",
                    "rate_limit": 30,
                    "rate_remaining": 29,
                }
            ]

    monkeypatch.setattr(setting, "github_col", FakeGithubCollection())

    response = client.get("/api/setting/github")

    assert response.status_code == 200
    assert response.get_json() == {
        "status": 200,
        "msg": "获取信息成功",
        "result": [
            {
                "username": "octocat",
                "mask_password": "gh****ken",
                "rate_limit": 30,
                "rate_remaining": 29,
            }
        ],
    }
    assert captured == {"filters": {}, "projection": {"_id": 0, "password": 0}}


def test_github_account_post_contract_does_not_return_password(client, monkeypatch):
    from integrations import github as github_integration
    from api.settings import repository as setting
    from api.settings import service as settings_service

    captured = {}

    class FakeGithub:
        def __init__(self, username, password):
            captured["github_credentials"] = (username, password)

    class FakeGithubCollection:
        def replace_one(self, filters, document, upsert=False):
            captured["replace_filters"] = filters
            captured["saved_document"] = document
            captured["upsert"] = upsert

        def find(self, filters, projection):
            captured["find_filters"] = filters
            captured["projection"] = projection
            return [
                {
                    "username": "octocat",
                    "mask_password": "gh****en",
                    "rate_limit": 30,
                    "rate_remaining": 28,
                }
            ]

    fake_collection = FakeGithubCollection()
    monkeypatch.setattr(github_integration, "create_client", FakeGithub)
    monkeypatch.setattr(
        github_integration,
        "search_rate_limit",
        lambda github: {"limit": 30, "remaining": 28},
    )
    monkeypatch.setattr(setting, "github_col", fake_collection)
    monkeypatch.setattr(settings_service.time, "time", lambda: 1780644000)

    response = client.post(
        "/api/setting/github",
        json={"username": "octocat", "password": "ghp_example_token"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body == {
        "status": 201,
        "msg": "添加成功",
        "result": [
            {
                "username": "octocat",
                "mask_password": "gh****en",
                "rate_limit": 30,
                "rate_remaining": 28,
            }
        ],
    }
    assert "password" not in body["result"][0]
    assert captured["github_credentials"] == ("octocat", "ghp_example_token")
    assert captured["replace_filters"] == {"_id": "554660db8666bd658d309ec6351872e9"}
    assert captured["upsert"] is True
    assert captured["saved_document"]["username"] == "octocat"
    assert captured["saved_document"]["password"] == "ghp_example_token"
    assert captured["saved_document"]["addat"] == 1780644000
    assert captured["projection"] == {"_id": 0, "password": 0}


def test_github_account_delete_contract_preserves_404_body_status_and_excludes_password(
    client, monkeypatch
):
    from api.settings import repository as setting

    captured = {}

    class FakeGithubCollection:
        def delete_many(self, filters):
            captured["delete_filters"] = filters

        def find(self, filters, projection):
            captured["find_filters"] = filters
            captured["projection"] = projection
            return [
                {
                    "username": "remaining",
                    "mask_password": "gh****ng",
                    "rate_limit": 30,
                    "rate_remaining": 20,
                }
            ]

    monkeypatch.setattr(setting, "github_col", FakeGithubCollection())

    response = client.delete("/api/setting/github?username=octocat")

    assert response.status_code == 200
    body = response.get_json()
    assert body == {
        "status": 404,
        "msg": "删除成功",
        "result": [
            {
                "username": "remaining",
                "mask_password": "gh****ng",
                "rate_limit": 30,
                "rate_remaining": 20,
            }
        ],
    }
    assert "password" not in body["result"][0]
    assert captured == {
        "delete_filters": {"username": "octocat"},
        "find_filters": {},
        "projection": {"_id": 0, "password": 0},
    }


def test_blacklist_delete_contract_preserves_404_body_status(client, monkeypatch):
    from api.settings import repository as setting

    captured = {}

    class FakeBlacklistCollection:
        def delete_many(self, filters):
            captured["delete_filters"] = filters

        def find(self, filters, projection):
            captured["find_filters"] = filters
            captured["projection"] = projection
            return [{"text": "remaining-secret"}]

    monkeypatch.setattr(setting, "blacklist_col", FakeBlacklistCollection())

    response = client.delete("/api/setting/blacklist?text=obsolete-secret")

    assert response.status_code == 200
    assert response.get_json() == {
        "status": 404,
        "msg": "删除成功",
        "result": [{"text": "remaining-secret"}],
    }
    assert captured == {
        "delete_filters": {"text": "obsolete-secret"},
        "find_filters": {},
        "projection": {"_id": 0},
    }


def test_notice_delete_contract_reads_query_args_and_preserves_404_body_status(
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


def test_query_delete_contract_preserves_404_body_status_and_result_cleanup(client, monkeypatch):
    from api.settings import repository as setting

    captured = {}
    query_cursor = FakeCursor(
        [
            {
                "_id": "query-2",
                "keyword": "github token",
                "tag": "github-token",
                "enabled": True,
            }
        ]
    )

    class FakeQueryCollection:
        def delete_many(self, filters):
            captured["query_delete_filters"] = filters

        def find(self, filters):
            captured["query_find_filters"] = filters
            return query_cursor

    class FakeResultCollection:
        def delete_many(self, filters):
            captured["result_delete_filters"] = filters

    monkeypatch.setattr(setting, "query_col", FakeQueryCollection())
    monkeypatch.setattr(setting, "result_col", FakeResultCollection())

    response = client.delete(
        "/api/setting/query",
        query_string={"_id": "query-1", "tag": "obsolete-token"},
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "status": 404,
        "msg": "删除成功",
        "result": [
            {
                "_id": "query-2",
                "keyword": "github token",
                "tag": "github-token",
                "enabled": True,
            }
        ],
    }
    assert captured == {
        "query_delete_filters": {"_id": "query-1"},
        "result_delete_filters": {"tag": "obsolete-token"},
        "query_find_filters": {},
    }
    assert query_cursor.calls == [("sort", "enabled", -1)]
