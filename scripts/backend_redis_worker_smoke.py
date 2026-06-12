#!/usr/bin/env python3
# coding: utf-8
# @File        : backend_redis_worker_smoke.py
# @Author      : NanMing
# @Date        : 2026/6/11 15:13
# @Description : Validate a real Redis broker and Huey background consumer.

"""Validate a real Redis broker and Huey background consumer."""

from loguru import logger
import argparse
import hashlib
import importlib
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path



def configure_logging():
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{message}")


DEFAULT_REDIS_HOST = "127.0.0.1"
DEFAULT_REDIS_PORT = 6379
DEFAULT_REDIS_DB = 15
MODULE_NAME = "skyradar_redis_worker_smoke_app"


class SmokeFailure(Exception):
    pass


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Start a real Huey consumer against Redis, enqueue a minimal add task, "
            "and verify the consumer stores result 42."
        )
    )
    parser.add_argument("--redis-host", default=os.environ.get("SKYRADAR_REDIS_HOST", DEFAULT_REDIS_HOST))
    parser.add_argument(
        "--redis-port",
        type=int,
        default=int(os.environ.get("SKYRADAR_REDIS_PORT", DEFAULT_REDIS_PORT)),
    )
    parser.add_argument(
        "--redis-db",
        type=int,
        default=int(os.environ.get("SKYRADAR_REDIS_DB", DEFAULT_REDIS_DB)),
        help="Redis database used only by this smoke; default: 15.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="Seconds to wait for the Huey result.",
    )
    parser.add_argument(
        "--connect-timeout",
        type=float,
        default=2.0,
        help="Seconds to wait for Redis connect/read checks.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate the temporary Huey module and consumer command without connecting to Redis.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output.")
    return parser.parse_args(argv)


def build_huey_name():
    return "skyradar-redis-worker-smoke-%s-%s" % (os.getpid(), int(time.time() * 1000))


def render_module_source(args, huey_name):
    return textwrap.dedent(
        """\
        from huey import RedisHuey


        huey = RedisHuey(
            {huey_name!r},
            host={host!r},
            port={port!r},
            db={db!r},
            results=True,
        )


        @huey.task()
        def add(left, right):
            return left + right
        """
    ).format(
        huey_name=huey_name,
        host=args.redis_host,
        port=args.redis_port,
        db=args.redis_db,
    )


def consumer_command(module_name):
    consumer_script = Path(sys.executable).with_name("huey_consumer.py")
    consumer_target = "%s.huey" % module_name
    options = [
        "-w",
        "1",
        "-k",
        "thread",
        "-n",
        "-d",
        "0.05",
        "-m",
        "0.2",
        "-b",
        "1.0",
        "-S",
        consumer_target,
    ]
    if consumer_script.exists():
        return [str(consumer_script), *options]
    return [sys.executable, "-m", "huey.bin.huey_consumer", *options]


def write_smoke_module(tmpdir, source):
    module_path = Path(tmpdir) / ("%s.py" % MODULE_NAME)
    module_path.write_text(source, encoding="utf-8")
    return module_path


def check_redis(args):
    try:
        from redis import Redis
    except Exception as error:
        raise SmokeFailure("Redis client import failed: %s" % error) from error

    client = Redis(
        host=args.redis_host,
        port=args.redis_port,
        db=args.redis_db,
        socket_connect_timeout=args.connect_timeout,
        socket_timeout=args.connect_timeout,
    )
    try:
        client.ping()
    except Exception as error:
        raise SmokeFailure(
            "Redis is not reachable at %s:%s db=%s: %s"
            % (args.redis_host, args.redis_port, args.redis_db, error)
        ) from error
    return client


def import_smoke_module(tmpdir):
    sys.path.insert(0, str(tmpdir))
    try:
        sys.modules.pop(MODULE_NAME, None)
        return importlib.import_module(MODULE_NAME)
    finally:
        try:
            sys.path.remove(str(tmpdir))
        except ValueError:
            pass


def terminate_consumer(process):
    if process.poll() is not None:
        return process.returncode
    process.terminate()
    try:
        return process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        return process.wait(timeout=5)


def read_log(log_path):
    try:
        return Path(log_path).read_text(encoding="utf-8", errors="replace")[-4000:]
    except OSError:
        return ""


def run_real_smoke(args, tmpdir, module_path, command):
    check_redis(args)
    smoke_module = import_smoke_module(tmpdir)
    smoke_module.huey.flush()

    env = os.environ.copy()
    env["PYTHONPATH"] = str(tmpdir) + os.pathsep + env.get("PYTHONPATH", "")
    log_path = Path(tmpdir) / "huey-consumer.log"
    process = None

    with log_path.open("w", encoding="utf-8") as log_file:
        try:
            process = subprocess.Popen(
                command,
                cwd=tmpdir,
                env=env,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True,
            )
            time.sleep(0.4)
            if process.poll() is not None:
                raise SmokeFailure(
                    "Huey consumer exited before task enqueue with code %s. Log:\n%s"
                    % (process.returncode, read_log(log_path))
                )

            result = smoke_module.huey.enqueue(smoke_module.add.s(19, 23))
            try:
                value = result.get(blocking=True, timeout=args.timeout)
            except Exception as error:
                raise SmokeFailure(
                    "Timed out or failed waiting for Huey result from background consumer: %s. Log:\n%s"
                    % (error, read_log(log_path))
                ) from error

            if value != 42:
                raise SmokeFailure("Huey result was %r, expected 42" % value)
            return {
                "consumer_pid": process.pid,
                "module_path": str(module_path),
                "result": value,
                "log_tail": read_log(log_path),
            }
        finally:
            if process is not None:
                terminate_consumer(process)
            try:
                smoke_module.huey.flush()
            except Exception:
                pass


def run(args):
    huey_name = build_huey_name()
    source = render_module_source(args, huey_name)
    source_sha256 = hashlib.sha256(source.encode("utf-8")).hexdigest()

    with tempfile.TemporaryDirectory(prefix="skyradar-redis-worker-smoke-") as tmpdir:
        module_path = write_smoke_module(tmpdir, source)
        command = consumer_command(MODULE_NAME)
        checks = [
            {
                "name": "temporary Huey module generated",
                "ok": module_path.exists(),
                "detail": str(module_path),
            },
            {
                "name": "consumer command constructed",
                "ok": command[-1] == "%s.huey" % MODULE_NAME,
                "detail": command,
            },
            {
                "name": "smoke task source generated",
                "ok": "def add(left, right)" in source and "RedisHuey" in source,
                "detail": source_sha256,
            },
        ]
        if not all(check["ok"] for check in checks):
            raise SmokeFailure("dry-run checks failed: %s" % checks)

        payload = {
            "ok": True,
            "mode": "dry-run" if args.dry_run else "real",
            "redis": {
                "host": args.redis_host,
                "port": args.redis_port,
                "db": args.redis_db,
            },
            "huey_name": huey_name,
            "module": {
                "name": MODULE_NAME,
                "path": str(module_path),
                "source_sha256": source_sha256,
            },
            "consumer_command": command,
            "checks": checks,
        }
        if args.dry_run:
            return payload

        result = run_real_smoke(args, tmpdir, module_path, command)
        payload["result"] = result
        payload["checks"].append(
            {
                "name": "background consumer executed queued add task",
                "ok": result["result"] == 42,
                "detail": result["result"],
            }
        )
        return payload


def print_human(payload):
    logger.info("Redis/Huey worker smoke %s" % ("passed" if payload["ok"] else "failed"))
    logger.info("mode: %s" % payload.get("mode"))
    redis = payload.get("redis", {})
    logger.info("redis: {host}:{port} db={db}".format(**redis))
    logger.info("consumer command: %s" % " ".join(payload.get("consumer_command", [])))
    for check in payload.get("checks", []):
        marker = "ok" if check.get("ok") else "failed"
        logger.info("- %s: %s" % (marker, check.get("name")))
    if "result" in payload:
        logger.info("result: %s" % payload["result"].get("result"))


def main(argv=None):
    configure_logging()
    args = parse_args(argv)
    try:
        payload = run(args)
    except SmokeFailure as error:
        payload = {"ok": False, "error": str(error)}
        if args.json:
            logger.info(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            logger.error("Redis/Huey worker smoke failed: %s" % error)
        return 1
    except Exception as error:
        payload = {"ok": False, "error": "unexpected failure: %s" % error}
        if args.json:
            logger.info(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            logger.error("Redis/Huey worker smoke failed unexpectedly: %s" % error)
        return 1

    if args.json:
        logger.info(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_human(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
