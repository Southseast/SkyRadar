# coding: utf-8
# @File        : test_mail_contract.py
# @Author      : NanMing
# @Date        : 2026/6/8 12:09
# @Description : Tests settings mail contract behavior.

def _project(document, projection):
    projected = dict(document)
    for field, enabled in projection.items():
        if enabled == 0:
            projected.pop(field, None)
    return projected


def test_mail_setting_get_contract_excludes_password(client, monkeypatch):
    from api.settings import repository as setting

    captured = {}
    stored_document = {
        "_id": "mail",
        "key": "mail",
        "from": "skyradar@example.com",
        "host": "smtp.example.com",
        "port": 587,
        "tls": True,
        "username": "skyradar@example.com",
        "password": "smtp-secret",
        "domain": "https://skyradar.example.com",
        "enabled": True,
        "test": False,
    }

    class FakeSettingCollection:
        def find_one(self, filters, projection):
            captured["filters"] = filters
            captured["projection"] = projection
            return _project(stored_document, projection)

    monkeypatch.setattr(setting, "setting_col", FakeSettingCollection())

    response = client.get("/api/setting/mail")

    assert response.status_code == 200
    body = response.get_json()
    assert body == {
        "status": 200,
        "msg": "获取信息成功",
        "result": {
            "key": "mail",
            "from": "skyradar@example.com",
            "host": "smtp.example.com",
            "port": 587,
            "tls": True,
            "username": "skyradar@example.com",
            "domain": "https://skyradar.example.com",
            "enabled": True,
            "test": False,
        },
    }
    assert "password" not in body["result"]
    assert captured == {
        "filters": {"key": "mail"},
        "projection": {"_id": 0, "password": 0},
    }


def test_mail_setting_post_contract_saves_password_but_excludes_it_from_response(
    client, monkeypatch
):
    from api.settings import repository as setting

    captured = {}
    stored_document = {}

    class FakeSettingCollection:
        def update_many(self, filters, update, upsert=False):
            captured["update_filters"] = filters
            captured["update"] = update
            captured["upsert"] = upsert
            stored_document.clear()
            stored_document.update(update["$set"])

        def find_one(self, filters, projection):
            captured["find_filters"] = filters
            captured["projection"] = projection
            return _project(stored_document, projection)

    monkeypatch.setattr(setting, "setting_col", FakeSettingCollection())

    response = client.post(
        "/api/setting/mail",
        json={
            "from": "skyradar@example.com",
            "host": "smtp.example.com",
            "port": 587,
            "tls": True,
            "username": "skyradar@example.com",
            "password": "smtp-secret",
            "domain": "https://skyradar.example.com",
            "enabled": True,
            "test": False,
        },
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body == {
        "status": 201,
        "msg": "设置成功",
        "result": {
            "key": "mail",
            "from": "skyradar@example.com",
            "host": "smtp.example.com",
            "port": 587,
            "tls": True,
            "username": "skyradar@example.com",
            "domain": "https://skyradar.example.com",
            "enabled": True,
            "test": False,
        },
    }
    assert "password" not in body["result"]
    assert captured["update_filters"] == {"key": "mail"}
    assert captured["update"]["$set"]["key"] == "mail"
    assert captured["update"]["$set"]["password"] == "smtp-secret"
    assert captured["upsert"] is True
    assert captured["find_filters"] == {"key": "mail"}
    assert captured["projection"] == {"_id": 0, "password": 0}


def test_mail_setting_post_without_password_does_not_overwrite_existing_password(
    client, monkeypatch
):
    from api.settings import repository as setting

    captured = {}
    stored_document = {
        "key": "mail",
        "from": "previous@example.com",
        "host": "smtp.previous.example.com",
        "port": 587,
        "tls": False,
        "username": "previous@example.com",
        "password": "existing-secret",
        "domain": "https://previous.example.com",
        "enabled": False,
        "test": False,
    }

    class FakeSettingCollection:
        def update_many(self, filters, update, upsert=False):
            captured["update_filters"] = filters
            captured["update"] = update
            captured["upsert"] = upsert
            stored_document.update(update["$set"])

        def find_one(self, filters, projection):
            captured["find_filters"] = filters
            captured["projection"] = projection
            return _project(stored_document, projection)

    monkeypatch.setattr(setting, "setting_col", FakeSettingCollection())

    response = client.post(
        "/api/setting/mail",
        json={
            "from": "skyradar@example.com",
            "host": "smtp.changed.example.com",
            "port": 465,
            "tls": True,
            "username": "skyradar@example.com",
            "domain": "http://127.0.0.1:18080",
            "enabled": True,
            "test": False,
        },
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body == {
        "status": 201,
        "msg": "设置成功",
        "result": {
            "key": "mail",
            "from": "skyradar@example.com",
            "host": "smtp.changed.example.com",
            "port": 465,
            "tls": True,
            "username": "skyradar@example.com",
            "domain": "http://127.0.0.1:18080",
            "enabled": True,
            "test": False,
        },
    }
    assert "password" not in captured["update"]["$set"]
    assert stored_document["password"] == "existing-secret"
    assert "password" not in body["result"]
