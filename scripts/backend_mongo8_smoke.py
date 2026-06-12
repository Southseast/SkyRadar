#!/usr/bin/env python3
# coding: utf-8
# @File        : backend_mongo8_smoke.py
# @Author      : NanMing
# @Date        : 2026/6/11 12:07
# @Description : Run MongoDB 8.x integration smoke checks with PyMongo 4 APIs.

"""Run MongoDB 8.x integration smoke checks with PyMongo 4 APIs."""

from loguru import logger
import argparse
import json
import os
import sys
import time
from dataclasses import dataclass



def configure_logging():
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{message}")


DEFAULT_MONGO_URI = "mongodb://127.0.0.1:27017"
DEFAULT_DATABASE = "skyradar_smoke"
SMOKE_COLLECTION = "backend_mongo8_smoke"


class SmokeFailure(Exception):
    pass


@dataclass
class SmokeConfig:
    mongo_uri: str
    db_name: str
    allow_non_8: bool
    dry_run: bool
    json_output: bool


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Validate MongoDB 8.x compatibility for SkyRadar's PyMongo 4 paths. "
            "The script uses only a temporary smoke collection/database."
        )
    )
    parser.add_argument(
        "--mongo-uri",
        default=os.environ.get("MONGODB_URI", DEFAULT_MONGO_URI),
        help="MongoDB URI, default: MONGODB_URI or %(default)s",
    )
    parser.add_argument(
        "--database",
        default=DEFAULT_DATABASE,
        help="Smoke database name, default: %(default)s",
    )
    parser.add_argument(
        "--allow-non-8",
        action="store_true",
        help="Allow running the CRUD smoke against non-8.x MongoDB for local development.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate script wiring without connecting to MongoDB.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON output.",
    )
    args = parser.parse_args(argv)
    return SmokeConfig(
        mongo_uri=args.mongo_uri,
        db_name=args.database,
        allow_non_8=args.allow_non_8,
        dry_run=args.dry_run,
        json_output=args.json,
    )


def parse_major_version(version):
    if not version:
        raise SmokeFailure("MongoDB server version is empty")
    head = str(version).split(".", 1)[0]
    try:
        return int(head)
    except ValueError as error:
        raise SmokeFailure("Cannot parse MongoDB major version from %r" % version) from error


def classify_server_version(version, allow_non_8=False):
    major = parse_major_version(version)
    if major >= 8:
        return {
            "ok": True,
            "major": major,
            "message": "MongoDB %s smoke target accepted" % version,
        }
    if allow_non_8:
        return {
            "ok": True,
            "major": major,
            "message": "MongoDB %s accepted because --allow-non-8 is set" % version,
        }
    return {
        "ok": False,
        "major": major,
        "message": "非 8.x，不满足 MongoDB 8 smoke: MongoDB %s" % version,
    }


def make_check(name, ok=True, detail=None):
    return {"name": name, "ok": bool(ok), "detail": detail}


def require(condition, message):
    if not condition:
        raise SmokeFailure(message)


def run_crud_checks(collection):
    now = int(time.time())
    marker = "skyradar-mongo8-smoke-%s" % now

    collection.delete_many({"marker": marker})

    insert_result = collection.insert_one(
        {"marker": marker, "category": "alpha", "score": 1, "replace": False}
    )
    require(insert_result.inserted_id is not None, "insert_one did not return inserted_id")

    upsert_result = collection.update_one(
        {"marker": marker, "category": "beta"},
        {"$set": {"score": 2, "upserted": True}},
        upsert=True,
    )
    require(
        upsert_result.matched_count == 1 or upsert_result.upserted_id is not None,
        "update_one upsert did not match or insert a document",
    )

    replace_result = collection.replace_one(
        {"marker": marker, "category": "alpha"},
        {"marker": marker, "category": "alpha", "score": 3, "replace": True},
    )
    require(replace_result.matched_count == 1, "replace_one did not match inserted document")

    collection.insert_many(
        [
            {"marker": marker, "category": "alpha", "score": 4},
            {"marker": marker, "category": "gamma", "score": 5},
        ]
    )

    count = collection.count_documents({"marker": marker})
    require(count == 4, "count_documents returned %r, expected 4" % count)

    paged = list(
        collection.find({"marker": marker}, {"_id": 0, "category": 1, "score": 1})
        .sort("score", 1)
        .skip(1)
        .limit(2)
    )
    require(
        [doc["score"] for doc in paged] == [3, 4],
        "find sort/skip/limit returned %r, expected scores [3, 4]" % paged,
    )

    aggregate = list(
        collection.aggregate(
            [
                {"$match": {"marker": marker}},
                {"$group": {"_id": "$category", "count": {"$sum": 1}}},
                {"$sort": {"_id": 1}},
            ]
        )
    )
    aggregate_counts = {doc["_id"]: doc["count"] for doc in aggregate}
    require(
        aggregate_counts == {"alpha": 2, "beta": 1, "gamma": 1},
        "aggregate group returned %r" % aggregate_counts,
    )

    delete_result = collection.delete_many({"marker": marker})
    require(
        delete_result.deleted_count == 4,
        "delete_many removed %r, expected 4" % delete_result.deleted_count,
    )

    remaining = collection.count_documents({"marker": marker})
    require(remaining == 0, "cleanup left %r smoke documents" % remaining)

    return {
        "inserted_id": str(insert_result.inserted_id),
        "upserted": upsert_result.upserted_id is not None,
        "count": count,
        "paged_scores": [doc["score"] for doc in paged],
        "aggregate_counts": aggregate_counts,
        "deleted_count": delete_result.deleted_count,
    }


def run_dry_checks(smoke_config):
    version_result = classify_server_version("8.0.0", allow_non_8=smoke_config.allow_non_8)
    return [
        make_check("arguments parsed", True, {"database": smoke_config.db_name}),
        make_check("MongoDB 8 version classification", version_result["ok"], version_result),
        make_check("dry run skipped MongoDB connection", True, smoke_config.mongo_uri),
    ]


def run_real_checks(smoke_config):
    try:
        from pymongo import MongoClient
    except ImportError as error:
        raise SmokeFailure("PyMongo is not installed: %s" % error) from error

    client = MongoClient(smoke_config.mongo_uri, serverSelectionTimeoutMS=5000)
    checks = []
    database = client[smoke_config.db_name]
    collection = database[SMOKE_COLLECTION]

    try:
        ping = client.admin.command("ping")
        checks.append(make_check("ping", ping.get("ok") in (1, 1.0, True), ping))

        server_info = client.server_info()
        version = server_info.get("version")
        version_result = classify_server_version(version, allow_non_8=smoke_config.allow_non_8)
        checks.append(
            make_check(
                "MongoDB 8 server version",
                version_result["ok"],
                version_result["message"],
            )
        )
        if not version_result["ok"]:
            return checks

        crud_result = run_crud_checks(collection)
        checks.append(make_check("PyMongo 4 CRUD operations", True, crud_result))
    finally:
        try:
            collection.delete_many({})
            if smoke_config.db_name == DEFAULT_DATABASE:
                client.drop_database(smoke_config.db_name)
        finally:
            client.close()

    return checks


def run_checks(smoke_config):
    if smoke_config.dry_run:
        return run_dry_checks(smoke_config)
    return run_real_checks(smoke_config)


def print_human(smoke_config, checks):
    mode = "dry-run" if smoke_config.dry_run else "real"
    logger.info("SkyRadar MongoDB 8 smoke (%s)" % mode)
    logger.info("Mongo URI: %s" % smoke_config.mongo_uri)
    logger.info("Database: %s" % smoke_config.db_name)
    logger.info("")

    for check in checks:
        label = "PASS" if check["ok"] else "FAIL"
        logger.info("[%s] %s" % (label, check["name"]))
        if check["detail"] is not None:
            logger.info("  detail: %s" % check["detail"])
        logger.info("")


def main(argv=None):
    configure_logging()
    smoke_config = parse_args(argv)
    try:
        checks = run_checks(smoke_config)
    except Exception as error:
        checks = [make_check("MongoDB 8 smoke failed", False, str(error))]

    ok = all(check["ok"] for check in checks)
    payload = {
        "ok": ok,
        "mongo_uri": smoke_config.mongo_uri,
        "database": smoke_config.db_name,
        "dry_run": smoke_config.dry_run,
        "checks": checks,
    }

    if smoke_config.json_output:
        logger.info(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_human(smoke_config, checks)

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
