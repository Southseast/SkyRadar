#!/usr/bin/env python3
# coding: utf-8
# @File        : backend_worker_smoke.py
# @Author      : NanMing
# @Date        : 2026/6/11 13:14
# @Description : Run local Huey worker smoke checks without external services.

"""Run local Huey worker smoke checks without external services."""

from loguru import logger
import argparse
import importlib
import json
import sys
import types

output_logger = logger.bind(channel="output")


def configure_logging(json_output=False):
    logger.remove()
    if json_output:
        logger.add(
            sys.stderr,
            level="INFO",
            format="{message}",
            filter=lambda record: record["extra"].get("channel") != "output",
        )
        logger.add(
            sys.stdout,
            level="INFO",
            format="{message}",
            filter=lambda record: record["extra"].get("channel") == "output",
        )
        return
    logger.add(sys.stdout, level="INFO", format="{message}")


SERVER_ROOT = "server"
EXPECTED_TASKS = {
    "workers.search_tasks.search",
    "workers.search_tasks.send_webhook_notice",
    "workers.search_tasks.send_mail_notice",
    "workers.schedule_tasks.update_github_rate_remaining",
    "workers.schedule_tasks.schedule_github_search",
}
EXPECTED_PERIODIC_TASKS = {
    "workers.schedule_tasks.update_github_rate_remaining",
    "workers.schedule_tasks.schedule_github_search",
}


class SmokeFailure(Exception):
    pass


class FakeCollection:
    def __init__(self, documents=None):
        self.documents = [dict(document) for document in documents or []]
        self.updates = []

    def count_documents(self, filters=None):
        return sum(1 for document in self.documents if _matches(document, filters or {}))

    def find_one(self, filters=None, projection=None):
        for document in self.documents:
            if _matches(document, filters or {}):
                return _project(document, projection)
        return None

    def update_one(self, filters, update, upsert=False):
        self.updates.append({"filters": filters, "update": update, "upsert": upsert})
        document = self.find_one(filters)
        if document is None:
            if not upsert:
                return FakeUpdateResult(matched_count=0, modified_count=0, upserted_id=None)
            document = _base_document_from_filter(filters)
            self.documents.append(document)
            upserted_id = document.get("_id")
        else:
            for stored in self.documents:
                if _matches(stored, filters or {}):
                    document = stored
                    break
            upserted_id = None

        for key, value in update.get("$set", {}).items():
            document[key] = value
        return FakeUpdateResult(matched_count=1, modified_count=1, upserted_id=upserted_id)

    def find_one_and_update(self, filters, update, return_document=None):
        self.updates.append({"filters": filters, "update": update, "return_document": return_document})
        for document in self.documents:
            if _matches(document, filters or {}):
                for key, value in update.get("$set", {}).items():
                    document[key] = value
                return dict(document)
        return None

    def find(self, filters=None, projection=None):
        return [
            _project(document, projection)
            for document in self.documents
            if _matches(document, filters or {})
        ]

    def insert_one(self, document):
        self.documents.append(dict(document))
        return types.SimpleNamespace(inserted_id=document.get("_id"))


class FakeUpdateResult:
    def __init__(self, matched_count, modified_count, upserted_id):
        self.matched_count = matched_count
        self.modified_count = modified_count
        self.upserted_id = upserted_id


class FakeRedis:
    def get(self, key):
        return None

    def set(self, key, value, ex=None):
        return True


def _matches(document, filters):
    for key, expected in filters.items():
        if key == "$or":
            if not any(_matches(document, option) for option in expected):
                return False
            continue
        actual = document.get(key)
        if isinstance(expected, dict):
            if "$exists" in expected and (key in document) is not bool(expected["$exists"]):
                return False
            if "$gt" in expected and not (actual is not None and actual > expected["$gt"]):
                return False
            continue
        if actual != expected:
            return False
    return True


def _project(document, projection):
    if not projection:
        return dict(document)
    excluded = {key for key, value in projection.items() if value == 0}
    if excluded:
        return {key: value for key, value in document.items() if key not in excluded}
    included = {key for key, value in projection.items() if value == 1}
    return {key: value for key, value in document.items() if key in included}


def _base_document_from_filter(filters):
    return {
        key: value
        for key, value in (filters or {}).items()
        if not isinstance(value, dict)
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Validate that server/workers can be imported and that the SkyRadar "
            "Huey app can run a local immediate-mode task without Redis, MongoDB, "
            "GitHub, SMTP, or webhook access."
        )
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output.")
    return parser.parse_args(argv)


def install_fake_database():
    from pymongo import DESCENDING

    fake_database = types.ModuleType("core.database")
    fake_database.DESCENDING = DESCENDING
    fake_database.MONGODB_URI = "mongodb://127.0.0.1:27017"
    fake_database.MONGODB_DATABASE = "skyradar_smoke"
    fake_database.REDIS_HOST = "127.0.0.1"
    fake_database.REDIS_PORT = 6379
    fake_database.REDIS_RESULT_CACHE_DB = 1
    fake_database.result_cache = FakeRedis()
    fake_database.create_indexes = lambda: None
    fake_database.create_mongo_client = lambda *args, **kwargs: None

    collections = {
        "result_col": FakeCollection(),
        "query_col": FakeCollection(),
        "blacklist_col": FakeCollection(),
        "task_col": FakeCollection(),
        "notice_col": FakeCollection(),
        "github_col": FakeCollection(),
        "setting_col": FakeCollection(
            [{"key": "task", "minute": 10, "page": 3, "last": 0}]
        ),
    }
    for name, collection in collections.items():
        setattr(fake_database, name, collection)

    return fake_database


def import_worker_module():
    if str(SERVER_ROOT) not in sys.path:
        sys.path.insert(0, str(SERVER_ROOT))

    for module_name in tuple(sys.modules):
        if module_name == "core.database" or module_name == "workers" or module_name.startswith("workers."):
            sys.modules.pop(module_name, None)
        elif module_name == "api.github_search" or module_name.startswith("api.github_search."):
            sys.modules.pop(module_name, None)
        elif module_name == "api.notifications" or module_name.startswith("api.notifications."):
            sys.modules.pop(module_name, None)

    fake_database = install_fake_database()
    sys.modules["core.database"] = fake_database
    worker_module = importlib.import_module("workers")
    return worker_module, fake_database


def task_registry_names(huey):
    registry = getattr(huey, "_registry", None)
    return set(getattr(registry, "_registry", {}).keys())


def periodic_task_names(huey):
    registry = getattr(huey, "_registry", None)
    task_to_string = getattr(registry, "task_to_string", None)
    periodic_tasks = getattr(registry, "_periodic_tasks", [])
    if task_to_string is None:
        return set()
    return {task_to_string(task_class) for task_class in periodic_tasks}


def run_immediate_task(worker_module):
    worker_module.huey.immediate = True

    def skyradar_worker_smoke_add(left, right):
        return left + right

    skyradar_worker_smoke_add.__name__ = "skyradar_worker_smoke_add"
    smoke_task = worker_module.huey.task()(skyradar_worker_smoke_add)
    queued_result = smoke_task(19, 23)
    immediate_result = queued_result()
    direct_result = smoke_task.call_local(20, 22)
    if immediate_result != 42:
        raise SmokeFailure("Huey immediate task returned %r, expected 42" % immediate_result)
    if direct_result != 42:
        raise SmokeFailure("Huey call_local returned %r, expected 42" % direct_result)


def run_checks():
    checks = []

    def record(name, fn):
        try:
            value = fn()
        except Exception as error:
            checks.append({"name": name, "ok": False, "detail": str(error)})
            return None
        checks.append({"name": name, "ok": True, "detail": value})
        return value

    try:
        worker_module, fake_database = import_worker_module()
    except Exception as error:
        checks.append(
            {
                "name": "import workers module with fake database",
                "ok": False,
                "detail": str(error),
            }
        )
        return checks
    checks.append(
        {
            "name": "import workers module with fake database",
            "ok": True,
            "detail": "workers imported",
        }
    )

    def check_huey_name():
        name = getattr(worker_module.huey, "name", None)
        if name != "skyradar":
            raise SmokeFailure("Huey name is %r, expected 'skyradar'" % name)
        return name

    def check_registered_tasks():
        names = task_registry_names(worker_module.huey)
        missing = sorted(EXPECTED_TASKS - names)
        if missing:
            raise SmokeFailure("missing registered Huey tasks: %s" % ", ".join(missing))
        return sorted(names)

    def check_periodic_tasks():
        names = periodic_task_names(worker_module.huey)
        missing = sorted(EXPECTED_PERIODIC_TASKS - names)
        if missing:
            raise SmokeFailure("missing periodic Huey tasks: %s" % ", ".join(missing))
        return sorted(names)

    def check_fake_database_used():
        worker_module.schedule_github_search.call_local()
        updates = fake_database.setting_col.updates
        if not updates:
            raise SmokeFailure("worker schedule did not touch fake setting_col")
        return {"setting_updates": len(updates), "redis_host": fake_database.REDIS_HOST}

    record("huey name is stable", check_huey_name)
    record("expected tasks are registered", check_registered_tasks)
    record("expected periodic tasks are registered", check_periodic_tasks)
    record("fake database handled import side effects", check_fake_database_used)
    record("huey immediate local task executes", lambda: run_immediate_task(worker_module) or "42")
    return checks


def print_human(checks):
    logger.info("SkyRadar Huey worker smoke")
    logger.info("")
    for check in checks:
        label = "PASS" if check["ok"] else "FAIL"
        logger.info("[%s] %s" % (label, check["name"]))
        if check["detail"] not in (None, ""):
            logger.info("  %s" % check["detail"])
        logger.info("")


def main(argv=None):
    args = parse_args(argv)
    configure_logging(json_output=args.json)
    checks = run_checks()
    configure_logging(json_output=args.json)
    ok = all(check["ok"] for check in checks)
    if args.json:
        output_logger.info(json.dumps({"ok": ok, "checks": checks}, ensure_ascii=False, indent=2))
    else:
        print_human(checks)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
