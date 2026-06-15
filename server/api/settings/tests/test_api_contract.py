# coding: utf-8
# @File        : test_api_contract.py
# @Author      : NanMing
# @Date        : 2026/6/9 14:37
# @Description : Tests settings REST API contract behavior.


class FakeDeleteResult:
    def __init__(self, deleted_count):
        self.deleted_count = deleted_count


def _project(document, projection):
    projected = dict(document)
    for field, enabled in projection.items():
        if enabled == 0:
            projected.pop(field, None)
    return projected


def test_legacy_setting_routes_are_not_registered(client):
    response = client.get("/api/setting/github")

    assert response.status_code == 404


def test_github_account_get_excludes_password(client, monkeypatch):
    from api.settings import repository as setting

    captured = {}

    class FakeGithubCollection:
        def find(self, filters, projection):
            captured["filters"] = filters
            captured["projection"] = projection
            return [_project(
                {
                    "username": "octocat",
                    "mask_password": "gh****en",
                    "password": "ghp_example_token",
                    "rate_limit": 30,
                    "rate_remaining": 29,
                },
                projection,
            )]

    monkeypatch.setattr(setting, "github_col", FakeGithubCollection())

    response = client.get("/api/v1/github-accounts")

    assert response.status_code == 200
    assert response.get_json() == {
        "data": [
                {
                    "username": "octocat",
                    "mask_password": "gh****en",
                    "rate_limit": 30,
                    "rate_remaining": 29,
                }
        ]
    }
    assert captured == {"filters": {}, "projection": {"_id": 0, "password": 0}}


def test_github_account_post_returns_created_public_account(client, monkeypatch):
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

    monkeypatch.setattr(github_integration, "create_client", FakeGithub)
    monkeypatch.setattr(
        github_integration,
        "search_rate_limit",
        lambda github: {"limit": 30, "remaining": 28},
    )
    monkeypatch.setattr(setting, "github_col", FakeGithubCollection())
    monkeypatch.setattr(settings_service.time, "time", lambda: 1780644000)

    response = client.post(
        "/api/v1/github-accounts",
        json={"username": "octocat", "password": "ghp_example_token"},
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body == {
        "data": {
            "username": "octocat",
            "mask_password": "gh****en",
            "addat": 1780644000,
            "rate_limit": 30,
            "rate_remaining": 28,
        }
    }
    assert "password" not in body["data"]
    assert captured["github_credentials"] == ("octocat", "ghp_example_token")
    assert captured["replace_filters"] == {"_id": "554660db8666bd658d309ec6351872e9"}
    assert captured["upsert"] is True
    assert captured["saved_document"]["password"] == "ghp_example_token"


def test_github_account_delete_returns_204(client, monkeypatch):
    from api.settings import repository as setting

    captured = {}

    class FakeGithubCollection:
        def delete_many(self, filters):
            captured["delete_filters"] = filters
            return FakeDeleteResult(1)

    monkeypatch.setattr(setting, "github_col", FakeGithubCollection())

    response = client.delete("/api/v1/github-accounts/octocat")

    assert response.status_code == 204
    assert response.data == b""
    assert captured == {"delete_filters": {"username": "octocat"}}


def test_github_account_delete_returns_404_when_missing(client, monkeypatch):
    from api.settings import repository as setting

    class FakeGithubCollection:
        def delete_many(self, filters):
            return FakeDeleteResult(0)

    monkeypatch.setattr(setting, "github_col", FakeGithubCollection())

    response = client.delete("/api/v1/github-accounts/missing")

    assert response.status_code == 404
    assert response.get_json() == {
        "error": "settings_error",
        "message": "GitHub account was not found",
    }
