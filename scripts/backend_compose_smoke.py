#!/usr/bin/env python3
# coding: utf-8
# @File        : backend_compose_smoke.py
# @Author      : NanMing
# @Date        : 2026/6/11 15:41
# @Description : Run a standardized Docker Compose smoke check for the SkyRadar backend.

"""Run a standardized Docker Compose smoke check for the SkyRadar backend."""

from loguru import logger
import argparse
import base64
import json
import os
import re
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass



def configure_logging():
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{message}")


DEFAULT_HTTP_PORT = 18080
DEFAULT_TIMEOUT = 600.0
DEFAULT_SMOKE_BASIC_AUTH_USERNAME = "skyradar-smoke"
DEFAULT_SMOKE_BASIC_AUTH_PASSWORD = "skyradar-smoke-password"
MONGO_SMOKE_DATABASE = "skyradar_compose_smoke"
MONGO_SMOKE_COLLECTION = "backend_compose_smoke"
LOG_FAILURE_PATTERNS = (
    re.compile(r"\bTraceback\b"),
    re.compile(r"\bFATAL\b", re.IGNORECASE),
    re.compile(r"\bspawnerr\b", re.IGNORECASE),
    re.compile(r"\bexited\b", re.IGNORECASE),
)
SECRET_PATTERNS = (
    re.compile(r"github_pat_[A-Za-z0-9_]+"),
    re.compile(r"ghp_[A-Za-z0-9_]+"),
    re.compile(r"(?i)\b(password|passwd|token|secret|api[_-]?key)\s*[:=]\s*[^\\s'\",}]+"),
    re.compile(r"mongodb://[^\\s/@:]+:[^\\s/@]+@"),
)


class SmokeFailure(Exception):
    pass


@dataclass
class Services:
    mongo: str
    redis: str
    web: str
    nginx: str
    worker: str


def basic_auth_headers_from_env():
    enabled = os.environ.get("SKYRADAR_BASIC_AUTH_ENABLED", "true").strip().lower()
    if enabled in {"0", "false", "no", "off"}:
        return {}
    username = os.environ.get("SKYRADAR_BASIC_AUTH_USERNAME", "")
    password = os.environ.get("SKYRADAR_BASIC_AUTH_PASSWORD", "")
    if bool(username) != bool(password):
        raise SmokeFailure("SKYRADAR_BASIC_AUTH_USERNAME and SKYRADAR_BASIC_AUTH_PASSWORD must be set together")
    if not username:
        username = DEFAULT_SMOKE_BASIC_AUTH_USERNAME
        password = DEFAULT_SMOKE_BASIC_AUTH_PASSWORD
    token = base64.b64encode(("%s:%s" % (username, password)).encode("utf-8")).decode("ascii")
    return {"Authorization": "Basic %s" % token}


def smoke_request(url, headers, method="GET"):
    merged_headers = {
        "User-Agent": "skyradar-compose-smoke/1.0",
        **headers,
        **basic_auth_headers_from_env(),
    }
    return urllib.request.Request(url, headers=merged_headers, method=method)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Start Docker Compose and validate MongoDB, Redis, web health, "
            "nginx, and worker task consumption."
        )
    )
    parser.add_argument("--compose-file", default="compose.yml")
    parser.add_argument("--project-name", help="Optional docker compose project name.")
    parser.add_argument(
        "--http-port",
        type=int,
        default=int(os.environ.get("SKYRADAR_HTTP_PORT", DEFAULT_HTTP_PORT)),
    )
    parser.add_argument(
        "--platform",
        default=os.environ.get("SKYRADAR_PLATFORM"),
        help="Optional Docker platform override, for example linux/amd64 or linux/arm64.",
    )
    parser.add_argument("--mongo-service", default="mongo")
    parser.add_argument("--redis-service", default="redis")
    parser.add_argument("--web-service", default="skyradar")
    parser.add_argument("--nginx-service", default="nginx")
    parser.add_argument("--worker-service", default="worker")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--poll-interval", type=float, default=2.0)
    parser.add_argument("--min-mongo-major", type=int, default=8)
    parser.add_argument(
        "--fresh-volumes",
        action="store_true",
        help="Run docker compose down -v before startup. Use only for disposable smoke runs.",
    )
    parser.add_argument(
        "--no-build",
        action="store_true",
        help="Start compose without --build.",
    )
    parser.add_argument(
        "--keep-running",
        action="store_true",
        help="Leave compose services running after the smoke completes.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned commands and service mapping without running Docker.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output.")
    return parser.parse_args(argv)


def compose_base(args):
    command = ["docker", "compose", "-f", args.compose_file]
    if args.project_name:
        command.extend(["-p", args.project_name])
    return command


def compose_command(args, *parts):
    return [*compose_base(args), *parts]


def compose_env(args):
    env = os.environ.copy()
    env["SKYRADAR_HTTP_PORT"] = str(args.http_port)
    enabled = env.get("SKYRADAR_BASIC_AUTH_ENABLED", "true").strip().lower()
    if enabled not in {"0", "false", "no", "off"}:
        env["SKYRADAR_BASIC_AUTH_ENABLED"] = "true"
        if not env.get("SKYRADAR_BASIC_AUTH_USERNAME"):
            env["SKYRADAR_BASIC_AUTH_USERNAME"] = DEFAULT_SMOKE_BASIC_AUTH_USERNAME
        if not env.get("SKYRADAR_BASIC_AUTH_PASSWORD"):
            env["SKYRADAR_BASIC_AUTH_PASSWORD"] = DEFAULT_SMOKE_BASIC_AUTH_PASSWORD
    if args.platform:
        env["SKYRADAR_PLATFORM"] = args.platform
    else:
        env.pop("SKYRADAR_PLATFORM", None)
    return env


def run_command(args, command, timeout=None, check=True):
    result = subprocess.run(
        command,
        cwd=os.getcwd(),
        env=compose_env(args),
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if check and result.returncode != 0:
        raise SmokeFailure(
            "command failed (%s):\nstdout:\n%s\nstderr:\n%s"
            % (shlex.join(command), result.stdout, result.stderr)
        )
    return result


def available_services(args):
    result = run_command(args, compose_command(args, "config", "--services"), timeout=30)
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def resolve_services(service_names, args):
    names = set(service_names)
    if args.mongo_service not in names:
        raise SmokeFailure(
            "compose service %r is required for MongoDB smoke; available services: %s"
            % (args.mongo_service, ", ".join(service_names))
        )

    web = args.web_service
    nginx = args.nginx_service
    redis = args.redis_service
    worker = args.worker_service

    missing = [
        label
        for label, service in (
            ("web", web),
            ("nginx", nginx),
            ("redis", redis),
            ("worker", worker),
        )
        if service not in names
    ]
    if missing:
        raise SmokeFailure(
            "compose services missing for %s checks; available services: %s"
            % (", ".join(missing), ", ".join(service_names))
        )

    return Services(
        mongo=args.mongo_service,
        redis=redis,
        web=web,
        nginx=nginx,
        worker=worker,
    )


def startup_commands(args):
    commands = []
    if args.fresh_volumes:
        commands.append(compose_command(args, "down", "-v", "--remove-orphans"))
    up = compose_command(args, "up", "-d")
    if not args.no_build:
        up.append("--build")
    commands.append(up)
    return commands


def shutdown_command(args, include_volumes=False):
    command = compose_command(args, "down")
    if include_volumes:
        command.append("-v")
    command.append("--remove-orphans")
    return command


def service_container_id(args, service):
    result = run_command(args, compose_command(args, "ps", "-q", service), timeout=30)
    container_id = result.stdout.strip()
    if not container_id:
        raise SmokeFailure("compose service %r has no running container" % service)
    return container_id


def inspect_container(container_id):
    result = subprocess.run(
        [
            "docker",
            "inspect",
            "--format",
            "{{json .State}}",
            container_id,
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise SmokeFailure("docker inspect failed for %s: %s" % (container_id, result.stderr))
    return json.loads(result.stdout)


def service_state(args, service):
    container_id = service_container_id(args, service)
    state = inspect_container(container_id)
    health = state.get("Health") or {}
    return {
        "service": service,
        "container_id": container_id,
        "running": bool(state.get("Running")),
        "status": state.get("Status"),
        "health": health.get("Status"),
    }


def is_service_ready(state):
    if not state["running"]:
        return False
    if state["health"] in (None, ""):
        return True
    return state["health"] == "healthy"


def wait_for_services(args, services):
    deadline = time.monotonic() + args.timeout
    names = [services.mongo, services.redis, services.web, services.nginx, services.worker]
    names = list(dict.fromkeys(names))
    last_states = []

    while time.monotonic() < deadline:
        last_states = [service_state(args, service) for service in names]
        if all(is_service_ready(state) for state in last_states):
            return last_states
        time.sleep(args.poll_interval)

    raise SmokeFailure("compose services did not become ready: %s" % last_states)


def compose_exec(args, service, command, timeout=30):
    return run_command(
        args,
        compose_command(args, "exec", "-T", service, "sh", "-lc", command),
        timeout=timeout,
    )


def parse_last_json_line(output):
    for line in reversed(output.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    raise SmokeFailure("no JSON payload found in command output: %r" % output[-1000:])


def check_mongo(args, services):
    script = r"""
const dbname = "skyradar_compose_smoke";
const collectionName = "backend_compose_smoke";
const marker = "compose-smoke-" + Date.now();
const smokeDb = db.getSiblingDB(dbname);
const collection = smokeDb.getCollection(collectionName);
collection.deleteMany({marker: marker});
collection.insertOne({marker: marker, category: "alpha", score: 1});
collection.updateOne({marker: marker, category: "beta"}, {$set: {score: 2}}, {upsert: true});
collection.insertMany([{marker: marker, category: "alpha", score: 3}, {marker: marker, category: "gamma", score: 4}]);
const count = collection.countDocuments({marker: marker});
const aggregate = collection.aggregate([
  {$match: {marker: marker}},
  {$group: {_id: "$category", count: {$sum: 1}}},
  {$sort: {_id: 1}}
]).toArray();
const deleted = collection.deleteMany({marker: marker}).deletedCount;
const payload = {
  version: db.version(),
  ping: db.adminCommand({ping: 1}).ok,
  count: count,
  aggregate: aggregate,
  deleted: deleted
};
console.log(JSON.stringify(payload));
"""
    command = "(mongosh --quiet --eval %s || mongo --quiet --eval %s)" % (
        shlex.quote(script),
        shlex.quote(script),
    )
    result = compose_exec(args, services.mongo, command, timeout=60)
    payload = parse_last_json_line(result.stdout)
    version = str(payload.get("version") or "")
    try:
        major = int(version.split(".", 1)[0])
    except ValueError as error:
        raise SmokeFailure("cannot parse MongoDB version from %r" % version) from error
    if major < args.min_mongo_major:
        raise SmokeFailure(
            "MongoDB version %s is below required major %s" % (version, args.min_mongo_major)
        )
    if payload.get("ping") not in (1, 1.0, True):
        raise SmokeFailure("MongoDB ping failed: %r" % payload)
    if payload.get("count") != 4 or payload.get("deleted") != 4:
        raise SmokeFailure("MongoDB CRUD smoke failed: %r" % payload)
    return payload


def check_redis(args, services):
    result = compose_exec(
        args,
        services.redis,
        "redis-cli ping && redis-cli INFO server",
        timeout=30,
    )
    output = result.stdout.strip().splitlines()
    if not output or output[0].strip() != "PONG":
        raise SmokeFailure("Redis ping failed: %r" % result.stdout)
    version = None
    for line in output[1:]:
        if line.startswith("redis_version:"):
            version = line.split(":", 1)[1].strip()
            break
    if not version:
        raise SmokeFailure("Redis version not found in INFO server output")
    return {"service": services.redis, "response": output[0].strip(), "version": version}


def check_api_service(args, services):
    supervisor = compose_exec(
        args,
        services.web,
        "command -v supervisorctl >/dev/null 2>&1 && supervisorctl status || true",
        timeout=30,
    ).stdout.strip()
    if "skyradar" not in supervisor or "RUNNING" not in supervisor:
        raise SmokeFailure("API service %r has no running skyradar program: %r" % (services.web, supervisor))

    unexpected_programs = []
    if services.nginx != services.web:
        for name in ("nginx", "huey", "redis"):
            if re.search(r"^%s\s+RUNNING" % re.escape(name), supervisor, re.MULTILINE):
                unexpected_programs.append(name)
    if unexpected_programs:
        raise SmokeFailure(
            "API service %r should only run Gunicorn/FastAPI, but also runs: %s"
            % (services.web, ", ".join(unexpected_programs))
        )
    return {"service": services.web, "status": supervisor}


def request_health(base_url, timeout):
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", "api/v1/health")
    request = smoke_request(
        url,
        {"Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.getcode()
            body = response.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as error:
        raise SmokeFailure("HTTP health request failed: %s" % error) from error

    if status != 200:
        raise SmokeFailure("HTTP health returned %s, expected 200" % status)
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as error:
        raise SmokeFailure("HTTP health response is not JSON: %s" % error) from error

    data = payload.get("data")
    if not isinstance(data, dict):
        raise SmokeFailure("HTTP health response is missing REST data envelope: %r" % payload)
    mongodb = data.get("mongodb")
    if not isinstance(mongodb, dict) or mongodb.get("ok") is not True:
        raise SmokeFailure("HTTP health MongoDB payload is not healthy: %r" % payload)
    return {"url": url, "status": status, "body": payload}


def request_static_index(base_url, timeout):
    url = base_url.rstrip("/") + "/"
    request = smoke_request(
        url,
        {"Accept": "text/html"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.getcode()
            content_type = response.headers.get("Content-Type", "")
            body = response.read(4096).decode("utf-8", errors="replace")
    except urllib.error.URLError as error:
        raise SmokeFailure("HTTP static index request failed: %s" % error) from error

    if status != 200:
        raise SmokeFailure("HTTP static index returned %s, expected 200" % status)
    if "<html" not in body.lower():
        raise SmokeFailure("HTTP static index did not look like HTML")
    return {"url": url, "status": status, "content_type": content_type}


def check_nginx(args, services):
    result = compose_exec(
        args,
        services.nginx,
        (
            "nginx -t >/tmp/skyradar-nginx-test.out 2>&1 && "
            "test -d /var/log/nginx && test -w /var/log/nginx && "
            "grep -q '/SkyRadar/client/dist' /etc/nginx/conf.d/SkyRadar.conf && "
            "awk '/proxy_pass http:/{print $2}' /etc/nginx/conf.d/SkyRadar.conf"
        ),
        timeout=30,
    )
    upstream = result.stdout.strip().rstrip(";")
    if not upstream:
        raise SmokeFailure("nginx proxy_pass upstream was not found")
    return {
        "service": services.nginx,
        "upstream": upstream,
        "log_dir": "/var/log/nginx",
        "static_root": "/SkyRadar/client/dist",
    }


def check_worker(args, services):
    supervisor = compose_exec(
        args,
        services.worker,
        "command -v supervisorctl >/dev/null 2>&1 && supervisorctl status huey || true",
        timeout=30,
    ).stdout.strip()
    if "RUNNING" in supervisor:
        status = {"service": services.worker, "method": "supervisorctl", "status": supervisor}
        status["consumption"] = check_worker_consumes_task(args, services)
        return status

    process = compose_exec(
        args,
        services.worker,
        "ps -eo pid,args | grep -E '[h]uey_consumer|[h]uey\\.bin\\.huey_consumer'",
        timeout=30,
    ).stdout.strip()
    if process:
        status = {"service": services.worker, "method": "process", "status": process}
        status["consumption"] = check_worker_consumes_task(args, services)
        return status

    raise SmokeFailure("worker service %r has no running Huey consumer" % services.worker)


def check_worker_consumes_task(args, services):
    script = r"""
import json
from loguru import logger
import sys
import time

from workers import huey, send_webhook_notice

logger.remove()
logger.add(sys.stdout, level="INFO", format="{message}")

queue_key = huey.storage.queue_key
before = huey.storage.queue_size()
result = send_webhook_notice("compose-smoke", [])
deadline = time.time() + 20
last = huey.storage.queue_size()

while time.time() < deadline:
    last = huey.storage.queue_size()
    if last <= before:
        logger.info(json.dumps({
            "task_id": str(result.id),
            "queue_key": queue_key,
            "before": before,
            "after": last,
            "consumed": True,
        }))
        break
    time.sleep(0.5)
else:
    logger.info(json.dumps({
        "task_id": str(result.id),
        "queue_key": queue_key,
        "before": before,
        "after": last,
        "consumed": False,
    }))
    raise SystemExit(2)
"""
    result = compose_exec(
        args,
        services.web,
        "python - <<'PY'\n%s\nPY" % script,
        timeout=30,
    )
    payload = parse_last_json_line(result.stdout)
    if payload.get("consumed") is not True:
        raise SmokeFailure("Huey task was not consumed: %r" % payload)
    return payload


def compose_logs(args):
    result = run_command(
        args,
        compose_command(args, "logs", "--no-color", "--tail", "300"),
        timeout=60,
    )
    return result.stdout


def matching_lines(text, patterns, limit=20):
    matches = []
    for line in text.splitlines():
        if any(pattern.search(line) for pattern in patterns):
            matches.append(line)
            if len(matches) >= limit:
                break
    return matches


def check_logs(args):
    logs = compose_logs(args)
    failure_matches = matching_lines(logs, LOG_FAILURE_PATTERNS)
    secret_matches = matching_lines(logs, SECRET_PATTERNS)
    if failure_matches or secret_matches:
        raise SmokeFailure(
            "compose logs scan failed: failures=%r secrets=%r"
            % (failure_matches, secret_matches)
        )
    return {
        "tail_lines": len(logs.splitlines()),
        "failure_patterns": 0,
        "secret_patterns": 0,
    }


def planned_payload(args):
    env = compose_env(args)
    service_names = []
    try:
        service_names = available_services(args)
        services = resolve_services(service_names, args)
        mapping = services.__dict__
    except Exception as error:
        mapping = {"error": str(error)}
    return {
        "ok": True,
        "dry_run": True,
        "commands": {
            "startup": [shlex.join(command) for command in startup_commands(args)],
            "shutdown": shlex.join(shutdown_command(args, include_volumes=args.fresh_volumes)),
        },
        "environment": {
            "SKYRADAR_HTTP_PORT": str(args.http_port),
            "SKYRADAR_PLATFORM": args.platform or "<native>",
            "SKYRADAR_BASIC_AUTH_ENABLED": env.get("SKYRADAR_BASIC_AUTH_ENABLED", "true"),
            "SKYRADAR_BASIC_AUTH_USERNAME": env.get("SKYRADAR_BASIC_AUTH_USERNAME", ""),
            "SKYRADAR_BASIC_AUTH_PASSWORD": "<redacted>"
            if env.get("SKYRADAR_BASIC_AUTH_PASSWORD")
            else "",
        },
        "services": service_names,
        "mapping": mapping,
    }


def run(args):
    if args.dry_run:
        return planned_payload(args)

    service_names = available_services(args)
    services = resolve_services(service_names, args)
    checks = []

    try:
        for command in startup_commands(args):
            run_command(args, command, timeout=args.timeout)
        checks.append({"name": "compose startup", "ok": True, "detail": service_names})

        states = wait_for_services(args, services)
        checks.append({"name": "compose services ready", "ok": True, "detail": states})

        mongo = check_mongo(args, services)
        checks.append({"name": "MongoDB ping/version/CRUD", "ok": True, "detail": mongo})

        redis = check_redis(args, services)
        checks.append({"name": "Redis ping", "ok": True, "detail": redis})

        api_service = check_api_service(args, services)
        checks.append({"name": "API service process boundary", "ok": True, "detail": api_service})

        health = request_health("http://127.0.0.1:%s" % args.http_port, timeout=20)
        checks.append({"name": "HTTP /api/v1/health 200", "ok": True, "detail": health})

        static_index = request_static_index("http://127.0.0.1:%s" % args.http_port, timeout=20)
        checks.append({"name": "HTTP static index 200", "ok": True, "detail": static_index})

        nginx = check_nginx(args, services)
        checks.append({"name": "nginx config and log path", "ok": True, "detail": nginx})

        worker = check_worker(args, services)
        checks.append({"name": "worker availability and task consumption", "ok": True, "detail": worker})

        logs = check_logs(args)
        checks.append({"name": "compose logs failure/secret scan", "ok": True, "detail": logs})

        return {
            "ok": True,
            "dry_run": False,
            "services": services.__dict__,
            "checks": checks,
        }
    except Exception as error:
        checks.append({"name": "compose smoke failed", "ok": False, "detail": str(error)})
        return {
            "ok": False,
            "dry_run": False,
            "services": services.__dict__,
            "checks": checks,
        }
    finally:
        if not args.keep_running:
            subprocess.run(
                shutdown_command(args, include_volumes=args.fresh_volumes),
                cwd=os.getcwd(),
                env=compose_env(args),
                check=False,
                capture_output=True,
                text=True,
                timeout=60,
            )


def print_human(payload):
    logger.info("SkyRadar compose smoke %s" % ("passed" if payload.get("ok") else "failed"))
    if payload.get("dry_run"):
        logger.info("mode: dry-run")
        logger.info("startup commands:")
        for command in payload["commands"]["startup"]:
            logger.info("- %s" % command)
        logger.info("shutdown command: %s" % payload["commands"]["shutdown"])
        logger.info("services: %s" % ", ".join(payload.get("services") or []))
        logger.info("mapping: %s" % payload.get("mapping"))
        return

    logger.info("services: %s" % payload.get("services"))
    for check in payload.get("checks", []):
        marker = "ok" if check.get("ok") else "failed"
        logger.info("- %s: %s" % (marker, check.get("name")))
        detail = check.get("detail")
        if detail is not None:
            logger.info("  detail: %s" % detail)


def main(argv=None):
    configure_logging()
    args = parse_args(argv)
    payload = run(args)
    if args.json:
        logger.info(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_human(payload)
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
