# coding: utf-8
# @File        : test_mongo8_smoke.py
# @Author      : NanMing
# @Date        : 2026/6/8 18:43
# @Description : Tests MongoDB 8 smoke command behavior.

import json
import subprocess
import sys
from types import SimpleNamespace

from scripts import backend_mongo8_smoke

class FakeResult:
    def __init__(self, inserted_id=None, matched_count=0, upserted_id=None, deleted_count=0):
        self.inserted_id = inserted_id
        self.matched_count = matched_count
        self.upserted_id = upserted_id
        self.deleted_count = deleted_count

class FakeCursor:
    def __init__(self, documents):
        self.documents = list(documents)

    def sort(self, key, direction):
        reverse = direction < 0
        self.documents.sort(key=lambda item: item.get(key), reverse=reverse)
        return self

    def skip(self, count):
        self.documents = self.documents[count:]
        return self

    def limit(self, count):
        self.documents = self.documents[:count]
        return self

    def __iter__(self):
        return iter(self.documents)

class FakeCollection:
    def __init__(self):
        self.documents = []
        self.next_id = 1

    def delete_many(self, filters):
        before = len(self.documents)
        self.documents = [document for document in self.documents if not self._matches(document, filters)]
        return FakeResult(deleted_count=before - len(self.documents))

    def insert_one(self, document):
        stored = dict(document)
        stored["_id"] = self.next_id
        self.next_id += 1
        self.documents.append(stored)
        return FakeResult(inserted_id=stored["_id"])

    def insert_many(self, documents):
        inserted_ids = []
        for document in documents:
            inserted_ids.append(self.insert_one(document).inserted_id)
        return SimpleNamespace(inserted_ids=inserted_ids)

    def update_one(self, filters, update, upsert=False):
        for document in self.documents:
            if self._matches(document, filters):
                document.update(update.get("$set", {}))
                return FakeResult(matched_count=1)
        if not upsert:
            return FakeResult(matched_count=0)
        stored = dict(filters)
        stored.update(update.get("$set", {}))
        inserted_id = self.insert_one(stored).inserted_id
        return FakeResult(matched_count=0, upserted_id=inserted_id)

    def replace_one(self, filters, replacement):
        for index, document in enumerate(self.documents):
            if self._matches(document, filters):
                stored = dict(replacement)
                stored["_id"] = document["_id"]
                self.documents[index] = stored
                return FakeResult(matched_count=1)
        return FakeResult(matched_count=0)

    def count_documents(self, filters):
        return sum(1 for document in self.documents if self._matches(document, filters))

    def find(self, filters, projection=None):
        return FakeCursor(
            [self._project(document, projection) for document in self.documents if self._matches(document, filters)]
        )

    def aggregate(self, pipeline):
        documents = list(self.documents)
        for stage in pipeline:
            if "$match" in stage:
                documents = [
                    document for document in documents if self._matches(document, stage["$match"])
                ]
            elif "$group" in stage:
                group_key = stage["$group"]["_id"].lstrip("$")
                grouped = {}
                for document in documents:
                    key = document.get(group_key)
                    grouped[key] = grouped.get(key, 0) + 1
                documents = [{"_id": key, "count": count} for key, count in grouped.items()]
            elif "$sort" in stage:
                sort_key, direction = next(iter(stage["$sort"].items()))
                documents.sort(key=lambda document: document.get(sort_key), reverse=direction < 0)
        return documents

    def _matches(self, document, filters):
        return all(document.get(key) == value for key, value in filters.items())

    def _project(self, document, projection):
        if not projection:
            return dict(document)
        if any(value == 0 for value in projection.values()):
            return {key: value for key, value in document.items() if projection.get(key) != 0}
        return {key: value for key, value in document.items() if projection.get(key) == 1}

def test_parse_args_reads_mongodb_uri_env(monkeypatch):
    monkeypatch.setenv("MONGODB_URI", "mongodb://example.invalid:27018")

    smoke_config = backend_mongo8_smoke.parse_args(["--database", "custom_smoke", "--dry-run"])

    assert smoke_config.mongo_uri == "mongodb://example.invalid:27018"
    assert smoke_config.db_name == "custom_smoke"
    assert smoke_config.dry_run is True

def test_classify_server_version_requires_mongodb_8_by_default():
    result = backend_mongo8_smoke.classify_server_version("5.0.22")

    assert result["ok"] is False
    assert result["major"] == 5
    assert "非 8.x" in result["message"]

def test_classify_server_version_allows_non_8_for_local_development():
    result = backend_mongo8_smoke.classify_server_version("7.0.12", allow_non_8=True)

    assert result["ok"] is True
    assert result["major"] == 7
    assert "--allow-non-8" in result["message"]

def test_run_crud_checks_uses_pymongo4_style_operations():
    collection = FakeCollection()

    result = backend_mongo8_smoke.run_crud_checks(collection)

    assert result["count"] == 4
    assert result["paged_scores"] == [3, 4]
    assert result["aggregate_counts"] == {"alpha": 2, "beta": 1, "gamma": 1}
    assert result["deleted_count"] == 4
    assert collection.documents == []

def test_backend_mongo8_smoke_dry_run_does_not_require_mongodb():
    result = subprocess.run(
        [
            sys.executable,
            "scripts/backend_mongo8_smoke.py",
            "--dry-run",
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["dry_run"] is True
    assert {check["name"] for check in payload["checks"]} >= {
        "arguments parsed",
        "MongoDB 8 version classification",
        "dry run skipped MongoDB connection",
    }
