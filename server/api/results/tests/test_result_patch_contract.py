# coding: utf-8
# @File        : test_result_patch_contract.py
# @Author      : NanMing
# @Date        : 2026/6/11 10:11
# @Description : Tests result status patch API contract behavior.

class FakeResultCollection:
    def __init__(self):
        self.update_one_calls = []
        self.update_many_calls = []

    def update_one(self, filters, update):
        self.update_one_calls.append((filters, update))

    def update_many(self, filters, update):
        self.update_many_calls.append((filters, update))


def test_leakage_patch_contract_updates_single_result_and_risk_project_batch(
    client, monkeypatch
):
    from api.results import repository as result

    fake_result_col = FakeResultCollection()
    monkeypatch.setattr(result, "result_col", fake_result_col)

    response = client.patch(
        "/api/leakage",
        json={
            "id": "leak-1",
            "project": "org/repo",
            "security": 0,
            "ignore": 0,
            "desc": "confirmed risk",
        },
    )

    assert response.status_code == 200
    assert response.get_json() == {"status": 201, "msg": "处理成功", "result": []}
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


def test_leakage_patch_contract_updates_single_result_and_safe_project_batch(
    client, monkeypatch
):
    from api.results import repository as result

    fake_result_col = FakeResultCollection()
    monkeypatch.setattr(result, "result_col", fake_result_col)

    response = client.patch(
        "/api/leakage",
        json={
            "id": "leak-2",
            "project": "org/repo",
            "security": 1,
            "ignore": 1,
            "desc": "false positive",
        },
    )

    assert response.status_code == 200
    assert response.get_json() == {"status": 201, "msg": "处理成功", "result": []}
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


def test_leakage_patch_accepts_form_urlencoded_contract(client, monkeypatch):
    from api.results import repository as result

    fake_result_col = FakeResultCollection()
    monkeypatch.setattr(result, "result_col", fake_result_col)

    response = client.patch(
        "/api/leakage",
        data={
            "id": "leak-form",
            "project": "org/repo",
            "security": "0",
            "ignore": "0",
            "desc": "confirmed from form",
        },
    )

    assert response.status_code == 200
    assert response.get_json() == {"status": 201, "msg": "处理成功", "result": []}
    assert fake_result_col.update_one_calls == [
        (
            {"_id": "leak-form"},
            {
                "$set": {
                    "security": 0,
                    "ignore": 0,
                    "desc": "confirmed from form",
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
                    "desc": "confirmed from form",
                }
            },
        )
    ]
