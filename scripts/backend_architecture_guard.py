#!/usr/bin/env python3
# coding: utf-8
# @File        : backend_architecture_guard.py
# @Author      : NanMing
# @Date        : 2026/6/11 13:07
# @Description : Guard backend architecture boundaries from unsupported layout regressions.

"""Guard backend architecture boundaries from unsupported layout regressions."""

from loguru import logger
import sys
import argparse
import ast
import json
from pathlib import Path



def configure_logging():
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{message}")


SERVER_ROOT = Path("server")

REMOVED_FILES = (
    "server/api.py",
    "server/task.py",
    "server/settings.py",
    "server/responses.py",
    "server/config/database.py",
    "server/core/security.py",
    "server/integrations/webhook.py",
    "server/utils/dingtalk_message.py",
    "server/utils/notice.py",
    "server/utils/webhook.py",
)
REMOVED_SOURCE_DIRS = (
    "server/controllers",
    "server/services",
    "server/repositories",
    "server/utils",
)
FORBIDDEN_FUNCTION_NAMES = {
    "server/api/github_search/service.py": {
        "dispatch_search_notifications",
        "initialize_schedule",
        "new_github",
        "schedule_checks",
        "search",
        "update_rate_remaining",
    },
    "server/api/notifications/service.py": {
        "send_mail",
    },
    "server/workers/schedule_tasks.py": {
        "check",
        "new_github",
        "update_rate_remain",
    },
    "server/workers/search_tasks.py": {
        "send_mail",
        "webhook_notice",
    },
}
FORBIDDEN_IMPORT_PREFIXES = (
    "flask",
    "flask_restful",
    "reqparse",
    "controllers",
    "services",
    "repositories",
    "server.controllers",
    "server.services",
    "server.repositories",
)
FORBIDDEN_REQUIREMENTS = {
    "flask",
    "flask-restful",
}
RUNTIME_SOURCE_ROOTS = (
    "server/api",
    "server/core",
    "server/integrations",
    "server/utils",
    "server/workers",
)


def _check(name, ok, detail):
    return {"name": name, "ok": bool(ok), "detail": detail}


def _source_files(root):
    if not root.exists():
        return []
    return [
        path
        for path in root.rglob("*.py")
        if "__pycache__" not in path.parts and "tests" not in path.parts
    ]


def check_removed_paths():
    findings = []
    for relative_path in REMOVED_FILES:
        path = Path(relative_path)
        if path.exists():
            findings.append(relative_path)
    for relative_path in REMOVED_SOURCE_DIRS:
        path = Path(relative_path)
        source_files = [
            source.as_posix()
            for source in _source_files(path)
        ]
        findings.extend(source_files)
    return _check(
        "unsupported backend source paths absent",
        not findings,
        "ok" if not findings else ", ".join(findings),
    )


def _imported_modules(tree):
    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.append(node.module)
    return modules


def _import_entries(tree):
    entries = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            entries.extend((alias.name, None) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            entries.extend((module, alias.name) for alias in node.names)
    return entries


def _imports_local_service(tree, domain):
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == f"api.{domain}" and any(alias.name == "service" for alias in node.names):
                return True
            if node.module == f"api.{domain}.service":
                return True
            if node.level == 1 and node.module is None and any(alias.name == "service" for alias in node.names):
                return True
            if node.level == 1 and node.module == "service":
                return True
    return False


def _is_forbidden_import(module):
    return any(module == prefix or module.startswith(prefix + ".") for prefix in FORBIDDEN_IMPORT_PREFIXES)


def check_forbidden_runtime_imports():
    findings = []
    for root in RUNTIME_SOURCE_ROOTS:
        for path in _source_files(Path(root)):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for module in _imported_modules(tree):
                if _is_forbidden_import(module):
                    findings.append(f"{path.as_posix()} imports {module}")
    return _check(
        "unsupported imports absent from runtime source",
        not findings,
        "ok" if not findings else "; ".join(findings),
    )


def check_forbidden_function_names():
    findings = []
    for relative_path, function_names in FORBIDDEN_FUNCTION_NAMES.items():
        path = Path(relative_path)
        if not path.exists():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in function_names:
                findings.append(f"{relative_path}:{node.lineno} defines {node.name}")
    return _check(
        "internal function names stay provider-specific",
        not findings,
        "ok" if not findings else "; ".join(findings),
    )


def check_requirements_do_not_restore_flask():
    findings = []
    for relative_path in ("deploy/pyenv/requirements.txt", "deploy/pyenv/requirements-dev.txt"):
        path = Path(relative_path)
        if not path.exists():
            continue
        for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            line = raw_line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            package_name = line.split(";", 1)[0].split("[", 1)[0].split("=", 1)[0].split("<", 1)[0].split(">", 1)[0].split("~", 1)[0].strip().lower()
            if package_name in FORBIDDEN_REQUIREMENTS:
                findings.append(f"{relative_path}:{line_number} contains {line}")
    return _check(
        "unsupported Flask dependencies absent",
        not findings,
        "ok" if not findings else "; ".join(findings),
    )


def check_routes_bind_domain_services():
    findings = []
    for route_path in sorted((SERVER_ROOT / "api").glob("*/routes.py")):
        domain = route_path.parent.name
        service_path = route_path.parent / "service.py"
        if not service_path.exists():
            continue
        tree = ast.parse(route_path.read_text(encoding="utf-8"), filename=str(route_path))
        if not _imports_local_service(tree, domain):
            findings.append(f"{route_path.as_posix()} does not import its local service")
    return _check(
        "domain routes import local services",
        not findings,
        "ok" if not findings else "; ".join(findings),
    )


def check_huey_entrypoint():
    path = Path("deploy/supervisor/huey.conf")
    if not path.exists():
        return _check("Huey supervisor entrypoint", False, "deploy/supervisor/huey.conf missing")
    text = path.read_text(encoding="utf-8")
    ok = "workers.huey" in text and "task.huey" not in text
    return _check(
        "Huey supervisor uses workers.huey",
        ok,
        "ok" if ok else "expected workers.huey and no task.huey",
    )


def check_supervisor_project_root_workdir():
    findings = []
    for relative_path in ("deploy/supervisor/skyradar.conf", "deploy/supervisor/huey.conf"):
        path = Path(relative_path)
        if not path.exists():
            findings.append(f"{relative_path} missing")
            continue
        text = path.read_text(encoding="utf-8")
        if "directory=/SkyRadar\n" not in text:
            findings.append(f"{relative_path} must use directory=/SkyRadar")
    return _check(
        "supervisor programs start from project root",
        not findings,
        "ok" if not findings else "; ".join(findings),
    )


def _api_domain_dirs():
    api_root = SERVER_ROOT / "api"
    if not api_root.exists():
        return []
    ignored = {"__pycache__", "tests"}
    return [
        path
        for path in sorted(api_root.iterdir())
        if path.is_dir() and path.name not in ignored and not path.name.startswith(".")
    ]


def _has_domain_tests(domain_path):
    tests_path = domain_path / "tests"
    return tests_path.is_dir() and any(tests_path.glob("test_*.py"))


def check_domain_directories_are_cohesive():
    findings = []
    for domain_path in _api_domain_dirs():
        runtime_files = {
            path.name
            for path in domain_path.glob("*.py")
            if path.name != "__init__.py"
        }
        if not runtime_files:
            continue
        domain = domain_path.name
        has_tests = _has_domain_tests(domain_path)
        if "routes.py" in runtime_files:
            for required in ("service.py", "schemas.py"):
                if required not in runtime_files:
                    findings.append(f"server/api/{domain}/routes.py requires {required}")
            if not has_tests:
                findings.append(f"server/api/{domain}/routes.py requires server/api/{domain}/tests/test_*.py")
        if "service.py" in runtime_files and not has_tests:
            findings.append(f"server/api/{domain}/service.py requires server/api/{domain}/tests/test_*.py")
        if "repository.py" in runtime_files and "service.py" not in runtime_files:
            findings.append(f"server/api/{domain}/repository.py requires service.py")
    return _check(
        "domain directories keep local implementation and tests",
        not findings,
        "ok" if not findings else "; ".join(findings),
    )


def _imports_boundary_bypass(tree):
    findings = []
    forbidden_exact = {
        "core.database",
        "pymongo",
        "redis",
        "requests",
        "smtplib",
    }
    for module, name in _import_entries(tree):
        imported = module if name is None else f"{module}.{name}" if module else name
        if module in forbidden_exact or imported in forbidden_exact:
            findings.append(imported)
            continue
        if module.startswith("integrations") or imported.startswith("integrations."):
            findings.append(imported)
            continue
        if imported.endswith(".repository") or imported.endswith(".repositories"):
            findings.append(imported)
    return findings


def check_routes_and_workers_use_service_boundary():
    findings = []
    for route_path in sorted((SERVER_ROOT / "api").glob("*/routes.py")):
        tree = ast.parse(route_path.read_text(encoding="utf-8"), filename=str(route_path))
        for imported in _imports_boundary_bypass(tree):
            findings.append(f"{route_path.as_posix()} imports {imported}")
    for worker_path in sorted((SERVER_ROOT / "workers").glob("*.py")):
        tree = ast.parse(worker_path.read_text(encoding="utf-8"), filename=str(worker_path))
        for imported in _imports_boundary_bypass(tree):
            if worker_path.name == "huey_app.py" and imported.startswith("core.database."):
                continue
            if imported.startswith("api.") and imported.endswith(".service"):
                continue
            findings.append(f"{worker_path.as_posix()} imports {imported}")
    return _check(
        "routes and workers stay behind service boundary",
        not findings,
        "ok" if not findings else "; ".join(findings),
    )


def _parent_map(tree):
    return {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}


def _is_service_call(node):
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id.endswith("_service")
    )


def _is_inside_run_in_threadpool(node, parents):
    current = parents.get(node)
    while current is not None:
        if isinstance(current, ast.Call) and isinstance(current.func, ast.Name) and current.func.id == "run_in_threadpool":
            return True
        current = parents.get(current)
    return False


def check_async_routes_threadpool_sync_services():
    findings = []
    for route_path in sorted((SERVER_ROOT / "api").glob("*/routes.py")):
        tree = ast.parse(route_path.read_text(encoding="utf-8"), filename=str(route_path))
        parents = _parent_map(tree)
        for function in [node for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef)]:
            for node in ast.walk(function):
                if _is_service_call(node) and not _is_inside_run_in_threadpool(node, parents):
                    findings.append(
                        f"{route_path.as_posix()}:{function.name} calls "
                        f"{node.func.value.id}.{node.func.attr} outside run_in_threadpool"
                    )
    return _check(
        "async routes isolate sync services with threadpool",
        not findings,
        "ok" if not findings else "; ".join(findings),
    )


def run_checks():
    checks = [
        check_removed_paths(),
        check_forbidden_runtime_imports(),
        check_forbidden_function_names(),
        check_requirements_do_not_restore_flask(),
        check_routes_bind_domain_services(),
        check_domain_directories_are_cohesive(),
        check_routes_and_workers_use_service_boundary(),
        check_async_routes_threadpool_sync_services(),
        check_huey_entrypoint(),
        check_supervisor_project_root_workdir(),
    ]
    return {"ok": all(check["ok"] for check in checks), "checks": checks}


def print_result(payload, as_json):
    if as_json:
        logger.info(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return
    logger.info(f"backend-architecture-guard: {'ok' if payload['ok'] else 'failed'}")
    for check in payload["checks"]:
        marker = "ok" if check["ok"] else "failed"
        logger.info(f"- {marker}: {check['name']} - {check['detail']}")


def main(argv=None):
    configure_logging()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args(argv)
    payload = run_checks()
    print_result(payload, args.json)
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
