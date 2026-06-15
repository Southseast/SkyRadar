# coding: utf-8
# @File        : test_result_patch_contract.py
# @Author      : NanMing
# @Date        : 2026/6/11 10:11
# @Description : Tests result status patch API contract behavior.


class FakeUpdateResult:
    matched_count = 1


class FakeMissingUpdateResult:
    matched_count = 0


class FakeResultCollection:
    def __init__(self, update_result=None):
        self.update_result = update_result or FakeUpdateResult()
        self.update_one_calls = []
        self.update_many_calls = []

    def update_one(self, filters, update):
        self.update_one_calls.append((filters, update))
        return self.update_result

    def update_many(self, filters, update):
        self.update_many_calls.append((filters, update))


def test_leakage_result_patch_updates_single_result_and_risk_project_batch(
    client, monkeypatch
):
    from api.results import repository as result

    fake_result_col = FakeResultCollection()
    monkeypatch.setattr(result, "result_col", fake_result_col)

    response = client.patch(
        "/api/v1/leakages/leak-1",
        json={
            "project": "org/repo",
            "security": 0,
            "ignored": False,
            "desc": "confirmed risk",
        },
    )

    assert response.status_code == 200
    assert response.get_json() == {"data": {"id": "leak-1", "updated": True}}
    assert fake_result_col.update_one_calls == [
        (
            {"_id": "leak-1"},
            {
                "$set": {
                    "security": 0,
                    "ignore": 0,
                    "desc": "confirmed risk",
                }
            },
        )
    ]
    assert fake_result_col.update_many_calls == [
        (
            {"project": "org/repo"},
            {
                "$set": {
                    "security": 0,
                    "ignore": 0,
                    "desc": "confirmed risk",
                }
            },
        )
    ]


def test_leakage_result_patch_updates_single_result_and_safe_project_batch(
    client, monkeypatch
):
    from api.results import repository as result

    fake_result_col = FakeResultCollection()
    monkeypatch.setattr(result, "result_col", fake_result_col)

    response = client.patch(
        "/api/v1/leakages/leak-2",
        json={
            "project": "org/repo",
            "security": 1,
            "ignored": True,
            "desc": "false positive",
        },
    )

    assert response.status_code == 200
    assert response.get_json() == {"data": {"id": "leak-2", "updated": True}}
    assert fake_result_col.update_one_calls == [
        (
            {"_id": "leak-2"},
            {
                "$set": {
                    "security": 1,
                    "ignore": 1,
                    "desc": "false positive",
                }
            },
        )
    ]
    assert fake_result_col.update_many_calls == [
        (
            {"project": "org/repo"},
            {
                "$set": {
                    "security": 1,
                    "ignore": 1,
                    "desc": "false positive",
                }
            },
        )
    ]


def test_leakage_result_patch_rejects_legacy_ignore_body_alias(client, monkeypatch):
    from api.results import repository as result

    fake_result_col = FakeResultCollection()
    monkeypatch.setattr(result, "result_col", fake_result_col)

    response = client.patch(
        "/api/v1/leakages/leak-alias",
        json={
            "ignore": 0,
        },
    )

    assert response.status_code == 422
    assert response.get_json() == {
        "error": "invalid_result_patch",
        "message": "PATCH body must include at least one mutable field",
    }
    assert fake_result_col.update_one_calls == []
    assert fake_result_col.update_many_calls == []


def test_leakage_result_patch_rejects_empty_body(client, monkeypatch):
    from api.results import repository as result

    fake_result_col = FakeResultCollection()
    monkeypatch.setattr(result, "result_col", fake_result_col)

    response = client.patch("/api/v1/leakages/leak-empty", json={})

    assert response.status_code == 422
    assert response.get_json() == {
        "error": "invalid_result_patch",
        "message": "PATCH body must include at least one mutable field",
    }
    assert fake_result_col.update_one_calls == []
    assert fake_result_col.update_many_calls == []


def test_leakage_result_patch_returns_rest_404_for_missing_result(client, monkeypatch):
    from api.results import repository as result

    fake_result_col = FakeResultCollection(update_result=FakeMissingUpdateResult())
    monkeypatch.setattr(result, "result_col", fake_result_col)

    response = client.patch(
        "/api/v1/leakages/missing",
        json={"security": 1, "ignored": True},
    )

    assert response.status_code == 404
    assert response.get_json() == {
        "error": "leakage_result_not_found",
        "message": "Leakage result not found",
        "detail": {"id": "missing"},
    }
