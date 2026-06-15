# coding: utf-8
# @File        : test_worker_service.py
# @Author      : NanMing
# @Date        : 2026/6/9 16:14
# @Description : Tests GitHub search worker service behavior.

from types import SimpleNamespace

import pytest

from api.github_search import service as worker_service


def _fake_repo(sha, *, remaining="10", project="org/repo", filename="secret.py"):
    fake_owner = SimpleNamespace(login="alice", avatar_url="https://example.com/avatar.png")
    fake_repository = SimpleNamespace(
        full_name=project,
        html_url="https://github.com/{}".format(project),
        language="Python",
        owner=fake_owner,
    )
    return SimpleNamespace(
        sha=sha,
        content="token",
        decoded_content="token",
        html_url="https://github.com/{}/blob/main/{}".format(project, filename),
        repository=fake_repository,
        path=filename,
        name=filename,
        raw_headers={"x-ratelimit-remaining": remaining},
        last_modified="Mon, 01 Jan 2024 00:00:00 GMT",
    )


class _ScheduleRepository:
    def __init__(self, *, now, setting=None, claim_success=True):
        self.now = now
        self.setting = {
            "key": "task",
            "page": 1,
            "minute": 5,
            "next_due_at": now,
            **(setting or {}),
        }
        self.claim_success = claim_success
        self.queries = [{"tag": "github-token", "keyword": "ghp_", "enabled": True}]
        self.account = {"username": "octocat", "password": "secret", "rate_remaining": 99}
        self.claims = []
        self.advanced_next_due_at = []
        self.touched_pids = []
        self.events = []

    def get_task_setting(self, *args, **kwargs):
        return dict(self.setting)

    get_task_schedule = get_task_setting
    find_task_setting = get_task_setting
    task_setting = get_task_setting

    def task_minute(self, default=10):
        return int(self.setting.get("minute", default))

    def task_page(self):
        return int(self.setting["page"])

    def task_next_due_at(self, default=None):
        return self.setting.get("next_due_at", default)

    def update_task_pid(self, pid):
        self.touched_pids.append(pid)

    def enabled_query_count(self):
        self.events.append("query_count")
        return len(self.queries)

    def has_github_capacity(self):
        return True

    def iter_enabled_queries(self):
        return list(self.queries)

    def choose_github_account(self):
        return dict(self.account)

    def is_task_schedule_due(self, *args, **kwargs):
        return int(self.setting.get("next_due_at", 0)) <= int(self.now)

    is_task_due = is_task_schedule_due

    def _claim_due_task(self, *args, **kwargs):
        self.events.append("claim")
        self.claims.append({"args": args, "kwargs": kwargs})
        if int(self.setting.get("next_due_at", 0)) > int(self.now):
            return None
        if not self.claim_success:
            return None

        minute = int(kwargs.get("minute", self.setting["minute"]))
        next_due_at = kwargs.get("next_due_at")
        next_due_at = kwargs.get("new_next_due_at", next_due_at)
        next_due_at = kwargs.get("due_at", next_due_at)
        for arg in args:
            if isinstance(arg, dict):
                minute = int(arg.get("minute", minute))
                next_due_at = arg.get("next_due_at", next_due_at)
                next_due_at = arg.get("new_next_due_at", next_due_at)
                next_due_at = arg.get("due_at", next_due_at)
            elif isinstance(arg, (int, float)) and int(arg) >= int(self.now) + minute * 60:
                next_due_at = int(arg)

        next_due_at = int(next_due_at if next_due_at is not None else int(self.now) + minute * 60)
        self.setting["next_due_at"] = next_due_at
        self.advanced_next_due_at.append(next_due_at)
        return dict(self.setting)

    claim_due_task = _claim_due_task
    claim_task_schedule = _claim_due_task
    claim_due_task_schedule = _claim_due_task
    claim_search_schedule = _claim_due_task
    claim_task_setting = _claim_due_task


def test_schedule_github_search_skips_when_next_due_at_is_in_future(monkeypatch):
    now = 1_700_000_000
    repo = _ScheduleRepository(now=now, setting={"minute": 5, "next_due_at": now + 120})
    scheduled = []

    monkeypatch.setattr(worker_service, "worker_repository", repo)
    monkeypatch.setattr(worker_service.time, "time", lambda: repo.now)
    monkeypatch.setattr(worker_service.os, "getpid", lambda: 4321)

    worker_service.schedule_github_search(
        lambda query, page, github_account, delay: scheduled.append((query, page, github_account, delay)),
        lambda: 0,
    )

    assert scheduled == []
    assert repo.advanced_next_due_at == []


def test_schedule_github_search_claims_due_task_before_enqueue_and_advances_next_due_at(monkeypatch):
    now = 1_700_000_000
    repo = _ScheduleRepository(now=now, setting={"minute": 5, "next_due_at": now})
    scheduled = []

    monkeypatch.setattr(worker_service, "worker_repository", repo)
    monkeypatch.setattr(worker_service.time, "time", lambda: repo.now)
    monkeypatch.setattr(worker_service.os, "getpid", lambda: 4321)

    worker_service.schedule_github_search(
        lambda query, page, github_account, delay: repo.events.append("enqueue")
        or scheduled.append({"query": query, "page": page, "account": github_account, "delay": delay}),
        lambda: 0,
    )

    assert scheduled == [{"query": repo.queries[0], "page": 0, "account": repo.account, "delay": 0}]
    assert len(repo.claims) == 1
    assert repo.advanced_next_due_at == [now + 5 * 60]
    assert repo.events.index("claim") < repo.events.index("enqueue")


def test_schedule_github_search_does_not_enqueue_when_due_claim_fails(monkeypatch):
    now = 1_700_000_000
    repo = _ScheduleRepository(now=now, setting={"minute": 5, "next_due_at": now}, claim_success=False)
    scheduled = []

    monkeypatch.setattr(worker_service, "worker_repository", repo)
    monkeypatch.setattr(worker_service.time, "time", lambda: repo.now)
    monkeypatch.setattr(worker_service.os, "getpid", lambda: 4321)

    worker_service.schedule_github_search(
        lambda query, page, github_account, delay: scheduled.append((query, page, github_account, delay)),
        lambda: 0,
    )

    assert scheduled == []
    assert len(repo.claims) == 1
    assert repo.advanced_next_due_at == []


def test_schedule_github_search_second_tick_does_not_duplicate_after_claim(monkeypatch):
    now = 1_700_000_000
    repo = _ScheduleRepository(now=now, setting={"minute": 5, "next_due_at": now})
    scheduled = []

    monkeypatch.setattr(worker_service, "worker_repository", repo)
    monkeypatch.setattr(worker_service.time, "time", lambda: repo.now)
    monkeypatch.setattr(worker_service.os, "getpid", lambda: 4321)

    def enqueue(query, page, github_account, delay):
        scheduled.append({"query": query, "page": page, "account": github_account, "delay": delay})

    worker_service.schedule_github_search(enqueue, lambda: 0)
    repo.now = now + 1
    worker_service.schedule_github_search(enqueue, lambda: 0)

    assert len(scheduled) == 1
    assert repo.advanced_next_due_at == [now + 5 * 60]


def test_schedule_github_search_passes_account_document_to_huey_boundary(monkeypatch):
    queries = [
        {"tag": "github-token", "keyword": "ghp_", "enabled": True},
        {"tag": "aws-key", "keyword": "AKIA", "enabled": True},
    ]
    account = {"username": "octocat", "password": "secret", "rate_remaining": 99}
    scheduled = []
    claimed = []

    monkeypatch.setattr(
        worker_service.worker_repository,
        "update_task_pid",
        lambda pid: None,
        raising=False,
    )
    monkeypatch.setattr(
        worker_service.worker_repository,
        "claim_due_task_schedule",
        lambda pid, now: claimed.append((pid, now)) or {"key": "task", "page": 2, "minute": 5},
        raising=False,
    )
    monkeypatch.setattr(worker_service.worker_repository, "enabled_query_count", lambda: len(queries))
    monkeypatch.setattr(worker_service.worker_repository, "has_github_capacity", lambda: True)
    monkeypatch.setattr(worker_service.worker_repository, "task_page", lambda: 2)
    monkeypatch.setattr(worker_service.worker_repository, "iter_enabled_queries", lambda: list(queries))
    monkeypatch.setattr(worker_service.worker_repository, "choose_github_account", lambda: dict(account))
    monkeypatch.setattr(worker_service.os, "getpid", lambda: 1234)

    worker_service.schedule_github_search(
        lambda query, page, github_account, delay: scheduled.append(
            {"query": query, "page": page, "account": github_account, "delay": delay}
        ),
        lambda: 7,
    )

    assert len(scheduled) == 4
    assert scheduled[0] == {"query": queries[0], "page": 0, "account": account, "delay": 7}
    assert scheduled[2] == {"query": queries[0], "page": 1, "account": account, "delay": 7}
    assert len(claimed) == 1
    assert claimed[0][0] == 1234


def test_search_inserts_leakage_and_returns_notification_lists(monkeypatch):
    captured = {"rates": [], "inserted": [], "query_success": []}

    fake_owner = SimpleNamespace(login="alice", avatar_url="https://example.com/avatar.png")
    fake_repository = SimpleNamespace(
        full_name="org/repo",
        html_url="https://github.com/org/repo",
        language="Python",
        owner=fake_owner,
    )
    fake_repo = SimpleNamespace(
        sha="sha-1",
        content="token",
        decoded_content="token",
        html_url="https://github.com/org/repo/blob/main/secret.py",
        repository=fake_repository,
        path="secret.py",
        name="secret.py",
        raw_headers={"x-ratelimit-remaining": "10"},
        last_modified="Mon, 01 Jan 2024 00:00:00 GMT",
    )
    fake_repos = SimpleNamespace(totalCount=1, get_page=lambda page: [fake_repo])
    fake_client = object()
    fake_assets = SimpleNamespace(get_affect_assets=lambda code: [])

    monkeypatch.setattr(worker_service.worker_repository, "touch_task", lambda pid, now: None)
    monkeypatch.setattr(worker_service.github_integration, "create_client", lambda username, password: fake_client)
    monkeypatch.setattr(worker_service.github_integration, "search_code", lambda client, keyword: fake_repos)
    monkeypatch.setattr(worker_service.github_integration, "search_rate_limit", lambda client: {"remaining": 42, "limit": 100})
    monkeypatch.setattr(
        worker_service.worker_repository,
        "update_github_rate_remaining",
        lambda username, remaining: captured["rates"].append({"username": username, "remaining": remaining}),
    )
    monkeypatch.setattr(worker_service.worker_repository, "iter_blacklist", lambda: [])

    def result_exists(filters):
        if filters == {"tag": "github-token"}:
            return True
        return False

    monkeypatch.setattr(worker_service.worker_repository, "result_exists", result_exists)
    monkeypatch.setattr(
        worker_service.worker_repository,
        "insert_result",
        lambda document: captured["inserted"].append(document),
    )
    monkeypatch.setattr(
        worker_service.worker_repository,
        "update_query_success",
        lambda tag, page, api_total, now: captured["query_success"].append(
            {"tag": tag, "page": page, "api_total": api_total, "now": now}
        ),
    )

    notices = worker_service.search_github_code(
        {"tag": "github-token", "keyword": "ghp_"},
        0,
        {"username": "octocat", "password": "secret"},
        asset_extractor=fake_assets,
        retry=lambda *args: None,
    )

    assert captured["rates"] == [{"username": "octocat", "remaining": 42}]
    assert captured["inserted"][0]["_id"] == "sha-1"
    assert captured["inserted"][0]["tag"] == "github-token"
    assert captured["query_success"][0]["api_total"] == 1
    assert notices["mail"]
    assert notices["webhook"][0].startswith("[org/repo/secret.py]")


def test_search_paged_results_insert_multiple_repos_and_mark_query_success(monkeypatch):
    captured = {"pages": [], "rates": [], "inserted": [], "query_success": []}
    fake_repos = SimpleNamespace(
        totalCount=7,
        get_page=lambda page: captured["pages"].append(page)
        or [
            _fake_repo("sha-1", filename="one.py"),
            _fake_repo("sha-2", filename="two.py"),
        ],
    )
    fake_assets = SimpleNamespace(get_affect_assets=lambda code: ["example.com"])

    monkeypatch.setattr(worker_service.worker_repository, "touch_task", lambda pid, now: None)
    monkeypatch.setattr(worker_service.github_integration, "create_client", lambda username, password: object())
    monkeypatch.setattr(worker_service.github_integration, "search_code", lambda client, keyword: fake_repos)
    monkeypatch.setattr(worker_service.github_integration, "search_rate_limit", lambda client: {"remaining": 42, "limit": 100})
    monkeypatch.setattr(
        worker_service.worker_repository,
        "update_github_rate_remaining",
        lambda username, remaining: captured["rates"].append({"username": username, "remaining": remaining}),
    )
    monkeypatch.setattr(worker_service.worker_repository, "iter_blacklist", lambda: [])
    monkeypatch.setattr(worker_service.worker_repository, "result_exists", lambda filters: False)
    monkeypatch.setattr(
        worker_service.worker_repository,
        "insert_result",
        lambda document: captured["inserted"].append(document),
    )
    monkeypatch.setattr(
        worker_service.worker_repository,
        "update_query_success",
        lambda tag, page, api_total, now: captured["query_success"].append(
            {"tag": tag, "page": page, "api_total": api_total}
        ),
    )

    notices = worker_service.search_github_code(
        {"tag": "github-token", "keyword": "ghp_"},
        1,
        {"username": "octocat", "password": "secret"},
        asset_extractor=fake_assets,
        retry=lambda *args: None,
    )

    assert captured["pages"] == [1]
    assert captured["rates"] == [{"username": "octocat", "remaining": 42}]
    assert [document["_id"] for document in captured["inserted"]] == ["sha-1", "sha-2"]
    assert captured["inserted"][0]["affect"] == ["example.com"]
    assert captured["query_success"] == [{"tag": "github-token", "page": 1, "api_total": 7}]
    assert len(notices["mail"]) == 2
    assert notices["webhook"][1].startswith("[org/repo/two.py]")


def test_search_stops_on_repo_rate_limit_zero_and_keeps_existing_notices(monkeypatch):
    captured = {"inserted": [], "query_success": []}
    fake_repos = SimpleNamespace(
        totalCount=3,
        get_page=lambda page: [
            _fake_repo("sha-1", remaining="3", filename="one.py"),
            _fake_repo("sha-2", remaining="0", filename="two.py"),
            _fake_repo("sha-3", remaining="3", filename="three.py"),
        ],
    )
    fake_assets = SimpleNamespace(get_affect_assets=lambda code: [])

    monkeypatch.setattr(worker_service.worker_repository, "touch_task", lambda pid, now: None)
    monkeypatch.setattr(worker_service.github_integration, "create_client", lambda username, password: object())
    monkeypatch.setattr(worker_service.github_integration, "search_code", lambda client, keyword: fake_repos)
    monkeypatch.setattr(worker_service.github_integration, "search_rate_limit", lambda client: {"remaining": 1, "limit": 100})
    monkeypatch.setattr(worker_service.worker_repository, "update_github_rate_remaining", lambda username, remaining: None)
    monkeypatch.setattr(worker_service.worker_repository, "iter_blacklist", lambda: [])
    monkeypatch.setattr(worker_service.worker_repository, "result_exists", lambda filters: False)
    monkeypatch.setattr(
        worker_service.worker_repository,
        "insert_result",
        lambda document: captured["inserted"].append(document),
    )
    monkeypatch.setattr(
        worker_service.worker_repository,
        "update_query_success",
        lambda tag, page, api_total, now: captured["query_success"].append((tag, page, api_total)),
    )

    notices = worker_service.search_github_code(
        {"tag": "github-token", "keyword": "ghp_"},
        0,
        {"username": "octocat", "password": "secret"},
        asset_extractor=fake_assets,
        retry=lambda *args: None,
    )

    assert [document["_id"] for document in captured["inserted"]] == ["sha-1"]
    assert len(notices["mail"]) == 1
    assert notices["webhook"] == [
        "[org/repo/one.py](https://github.com/org/repo/blob/main/one.py) 上传于 2024-01-01 00:00:00"
    ]
    assert captured["query_success"] == []


@pytest.mark.parametrize("failure_stage", ["search_code", "get_page"])
def test_search_retries_with_next_account_when_github_fixture_fails(monkeypatch, failure_stage):
    next_account = {"username": "next", "password": "secret"}
    retried = []

    if failure_stage == "search_code":
        def search_code(client, keyword):
            raise RuntimeError("rate limited")

    else:
        fake_repos = SimpleNamespace(
            totalCount=0,
            get_page=lambda page: (_ for _ in ()).throw(RuntimeError("page failed")),
        )

        def search_code(client, keyword):
            return fake_repos

    monkeypatch.setattr(worker_service.github_integration, "create_client", lambda username, password: object())
    monkeypatch.setattr(worker_service.github_integration, "search_code", search_code)
    monkeypatch.setattr(
        worker_service.github_integration,
        "search_rate_limit",
        lambda client: {"remaining": 42, "limit": 100},
    )
    monkeypatch.setattr(worker_service.worker_repository, "update_github_rate_remaining", lambda username, remaining: None)
    monkeypatch.setattr(worker_service.worker_repository, "choose_github_account", lambda: dict(next_account))

    notices = worker_service.search_github_code(
        {"tag": "github-token", "keyword": "ghp_"},
        2,
        {"username": "octocat", "password": "secret"},
        asset_extractor=SimpleNamespace(get_affect_assets=lambda code: []),
        retry=lambda query, page, account: retried.append(
            {"query": query, "page": page, "account": account}
        ),
    )

    assert notices == {"mail": [], "webhook": []}
    assert retried == [
        {
            "query": {"tag": "github-token", "keyword": "ghp_"},
            "page": 2,
            "account": next_account,
        }
    ]
