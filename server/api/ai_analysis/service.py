# coding: utf-8
# @File        : service.py
# @Author      : NanMing
# @Date        : 2026/7/2
# @Description : Implements OpenAI leakage analysis behavior.

import base64
import datetime
import json
import os
from pathlib import Path

from api.ai_analysis import repository
from integrations import openai_client


DEFAULT_PROMPT = "你是安全分析助手，请简要分析以下 GitHub 泄露发现，判断风险等级并给出处置建议。"
DEFAULT_USEFULNESS_PROMPT_PATH = "config/ai_analysis_prompt.txt"
DEFAULT_INTERESTS_PATH = "config/ai_interests.txt"
OUTPUT_CONSTRAINT = (
    "必须只返回 JSON 对象，不要 Markdown，不要额外说明。字段必须包含 "
    "risk_level、summary、evidence、recommendation、false_positive_reason、is_useful、usefulness_reason、matched_interests。"
)
TRUE_VALUES = {"1", "true", "yes", "on"}
DEFAULT_OPENAI_SETTING = {
    "enabled": False,
    "base_url": "https://api.openai.com/v1",
    "model": "gpt-4o-mini",
    "prompt": DEFAULT_PROMPT,
    "notify_webhook_on_useful": False,
    "max_context_lines": 120,
    "max_context_chars": 12000,
    "timeout_seconds": 30,
    "max_retries": 2,
    "concurrency": 2,
}


class OpenAISettingError(Exception):
    def __init__(self, status_code, message):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class LeakageAnalysisNotFound(Exception):
    pass


def _env(name, default=None):
    value = os.environ.get(name)
    return default if value is None or value == "" else value


def _env_bool(name, default=False):
    value = _env(name)
    if value is None:
        return default
    return str(value).strip().lower() in TRUE_VALUES


def _env_int(name, default):
    value = _env(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _clamp_int(value, default, minimum, maximum):
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(minimum, min(maximum, number))


def _mask_secret(value):
    value = str(value or "")
    if not value:
        return ""
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}****{value[-4:]}"


def _read_prompt_file(path, max_chars=30000):
    if not path:
        return ""
    prompt_path = Path(path)
    candidates = [prompt_path]
    if not prompt_path.is_absolute():
        candidates.append(Path(__file__).resolve().parents[3] / prompt_path)
    for candidate in candidates:
        try:
            return candidate.read_text(encoding="utf-8")[:max_chars]
        except OSError:
            continue
    return ""


def _stored_setting():
    return repository.get_openai_setting() or {}


def effective_openai_setting():
    stored = _stored_setting()
    setting = {
        **DEFAULT_OPENAI_SETTING,
        "enabled": _env_bool("OPENAI_ENABLED", DEFAULT_OPENAI_SETTING["enabled"]),
        "api_key": _env("OPENAI_API_KEY"),
        "base_url": _env("OPENAI_BASE_URL", DEFAULT_OPENAI_SETTING["base_url"]),
        "model": _env("OPENAI_MODEL", DEFAULT_OPENAI_SETTING["model"]),
        "timeout_seconds": _env_int("OPENAI_TIMEOUT_SECONDS", DEFAULT_OPENAI_SETTING["timeout_seconds"]),
    }
    for key, value in stored.items():
        if key not in {"_id", "key"} and value is not None:
            setting[key] = value
    setting["enabled"] = bool(setting.get("enabled", False))
    setting["max_context_lines"] = _clamp_int(setting.get("max_context_lines"), 120, 1, 1000)
    setting["max_context_chars"] = _clamp_int(setting.get("max_context_chars"), 12000, 100, 200000)
    setting["timeout_seconds"] = _clamp_int(setting.get("timeout_seconds"), 30, 1, 300)
    setting["max_retries"] = _clamp_int(setting.get("max_retries"), 2, 0, 10)
    setting["concurrency"] = _clamp_int(setting.get("concurrency"), 2, 1, 10)
    setting["notify_webhook_on_useful"] = bool(setting.get("notify_webhook_on_useful", False))
    setting["usefulness_prompt"] = str(setting.get("usefulness_prompt") or _read_prompt_file(DEFAULT_USEFULNESS_PROMPT_PATH)).strip()
    setting["interests"] = str(setting.get("interests") or _read_prompt_file(DEFAULT_INTERESTS_PATH)).strip()
    setting.pop("usefulness_prompt_path", None)
    setting.pop("interests_path", None)
    return setting


def public_openai_setting():
    setting = effective_openai_setting()
    api_key = setting.get("api_key")
    public = {key: value for key, value in setting.items() if key != "api_key"}
    public["has_api_key"] = bool(api_key)
    public["mask_api_key"] = _mask_secret(api_key)
    return public


def save_openai_setting(payload):
    current = _stored_setting()
    document = {
        "key": "openai",
        "enabled": bool(payload.get("enabled", current.get("enabled", False))),
        "base_url": str(payload.get("base_url") or current.get("base_url") or DEFAULT_OPENAI_SETTING["base_url"]).strip(),
        "model": str(payload.get("model") or current.get("model") or DEFAULT_OPENAI_SETTING["model"]).strip(),
        "prompt": str(payload.get("prompt") or current.get("prompt") or DEFAULT_PROMPT).strip(),
        "notify_webhook_on_useful": bool(payload.get("notify_webhook_on_useful", current.get("notify_webhook_on_useful", False))),
        "usefulness_prompt": str(
            payload.get("usefulness_prompt") or current.get("usefulness_prompt") or _read_prompt_file(DEFAULT_USEFULNESS_PROMPT_PATH)
        ).strip(),
        "interests": str(payload.get("interests") or current.get("interests") or _read_prompt_file(DEFAULT_INTERESTS_PATH)).strip(),
        "max_context_lines": _clamp_int(payload.get("max_context_lines", current.get("max_context_lines")), 120, 1, 1000),
        "max_context_chars": _clamp_int(payload.get("max_context_chars", current.get("max_context_chars")), 12000, 100, 200000),
        "timeout_seconds": _clamp_int(payload.get("timeout_seconds", current.get("timeout_seconds")), 30, 1, 300),
        "max_retries": _clamp_int(payload.get("max_retries", current.get("max_retries")), 2, 0, 10),
        "concurrency": _clamp_int(payload.get("concurrency", current.get("concurrency")), 2, 1, 10),
    }
    api_key = str(payload.get("api_key") or "").strip()
    if api_key:
        document["api_key"] = api_key
    elif current.get("api_key"):
        document["api_key"] = current.get("api_key")
    if not document["model"]:
        raise OpenAISettingError(400, "model is required")
    repository.save_openai_setting(document)
    return public_openai_setting()


def mark_pending(leakage_id, force=False):
    update_result = repository.mark_ai_analysis_pending(leakage_id, force=force)
    if getattr(update_result, "matched_count", 1) == 0:
        return False
    return True


def skipped_analysis(reason):
    return {
        "status": "skipped",
        "risk_level": "unknown",
        "summary": "",
        "evidence": [],
        "recommendation": "",
        "false_positive_reason": "",
        "error": reason,
    }


def running_analysis(model):
    return {"status": "running", "risk_level": "unknown", "model": model}


def failed_analysis(message, model=None):
    result = {
        "status": "failed",
        "risk_level": "unknown",
        "summary": "",
        "evidence": [],
        "recommendation": "",
        "false_positive_reason": "",
        "error": str(message)[:500],
    }
    if model:
        result["model"] = model
    return result


def _decode_code(value):
    if not value:
        return ""
    try:
        return base64.b64decode(str(value), validate=False).decode("utf-8", "replace")
    except Exception:
        return str(value)


def _code_window(code, max_lines, max_chars):
    lines = code.splitlines()
    text = "\n".join(lines[:max_lines])
    return text[:max_chars]


def _analysis_input(leakage, setting):
    code = _decode_code(leakage.get("code"))
    return {
        "project": leakage.get("project"),
        "filepath": leakage.get("filepath"),
        "filename": leakage.get("filename"),
        "tag": leakage.get("tag"),
        "link": leakage.get("link"),
        "language": leakage.get("language"),
        "search_type": leakage.get("search_type"),
        "description": leakage.get("description"),
        "stars": leakage.get("stargazers_count"),
        "forks": leakage.get("forks_count"),
        "updated_at": str(leakage.get("datetime") or ""),
        "affected_assets": leakage.get("affect") or [],
        "code": _code_window(code, setting["max_context_lines"], setting["max_context_chars"]),
    }


def _messages(leakage, setting):
    usefulness_prompt = str(setting.get("usefulness_prompt") or "")
    interests = str(setting.get("interests") or "")
    system_parts = [
        setting["prompt"],
        "请额外判断该 GitHub 项目或命中结果是否符合我的关注方向，适合推送到 webhook。",
    ]
    if usefulness_prompt:
        system_parts.extend(["以下是参考分析提示词：", usefulness_prompt])
    if interests:
        system_parts.extend(["以下是我的关注兴趣和标题质量要求：", interests])
    system_parts.extend(
        [
            "判断 is_useful 时必须保守：只有与关注方向有明确技术、防御、研究、工具或预警价值时才返回 true。",
            "matched_interests 返回命中的关注方向关键词数组；usefulness_reason 用一句话说明为什么值得或不值得推送。",
            OUTPUT_CONSTRAINT,
        ]
    )
    return [
        {"role": "system", "content": "\n\n".join(system_parts)},
        {"role": "user", "content": json.dumps(_analysis_input(leakage, setting), ensure_ascii=False)},
    ]


def _normalize_result(raw, model):
    if not isinstance(raw, dict):
        raise ValueError("AI response was not valid JSON")
    risk_level = str(raw.get("risk_level") or "unknown").lower()
    if risk_level not in {"low", "medium", "high", "unknown"}:
        risk_level = "unknown"
    evidence = raw.get("evidence")
    if not isinstance(evidence, list):
        evidence = []
    matched_interests = raw.get("matched_interests")
    if not isinstance(matched_interests, list):
        matched_interests = []
    return {
        "status": "success",
        "risk_level": risk_level,
        "summary": str(raw.get("summary") or ""),
        "evidence": [str(item) for item in evidence[:10]],
        "recommendation": str(raw.get("recommendation") or ""),
        "false_positive_reason": str(raw.get("false_positive_reason") or ""),
        "is_useful": bool(raw.get("is_useful", False)),
        "usefulness_reason": str(raw.get("usefulness_reason") or ""),
        "matched_interests": [str(item) for item in matched_interests[:10]],
        "model": model,
        "analyzed_at": datetime.datetime.now(datetime.UTC),
    }


def notify_webhook_on_useful_enabled():
    setting = effective_openai_setting()
    return bool(setting.get("notify_webhook_on_useful"))


def should_notify_webhook_for_analysis(analysis):
    return bool(
        notify_webhook_on_useful_enabled()
        and analysis
        and analysis.get("status") == "success"
        and analysis.get("is_useful")
    )


def useful_project_notice(leakage_id, analysis):
    leakage = repository.get_leakage_for_analysis(leakage_id)
    if not leakage:
        raise LeakageAnalysisNotFound(leakage_id)
    title = leakage.get("project") or leakage.get("filename") or leakage_id
    url = leakage.get("project_url") or leakage.get("link") or ""
    reason = analysis.get("usefulness_reason") or analysis.get("summary") or "AI 判断该项目值得关注"
    if url:
        return "[{}]({}) {}".format(title, url, reason)
    return "{} {}".format(title, reason)


def analyze_leakage_now(leakage_id, client_factory=openai_client.create_client, analyzer=openai_client.analyze):
    setting = effective_openai_setting()
    leakage = repository.get_leakage_for_analysis(leakage_id)
    if not leakage:
        raise LeakageAnalysisNotFound(leakage_id)
    if not setting.get("enabled"):
        analysis = skipped_analysis("OpenAI analysis is disabled")
        repository.update_ai_analysis(leakage_id, analysis)
        return analysis
    if not setting.get("api_key"):
        analysis = skipped_analysis("OpenAI API key is not configured")
        repository.update_ai_analysis(leakage_id, analysis)
        return analysis
    if repository.claim_analysis_slot(setting["concurrency"]) is None:
        return {"status": "deferred"}

    try:
        repository.update_ai_analysis(leakage_id, running_analysis(setting["model"]))
        messages = _messages(leakage, setting)
        raw = None
        last_error = None
        for _attempt in range(setting["max_retries"] + 1):
            try:
                client = client_factory(setting["api_key"], base_url=setting.get("base_url"), timeout=setting.get("timeout_seconds"))
                raw = analyzer(client, setting["model"], messages)
                last_error = None
                break
            except json.JSONDecodeError:
                raise
            except Exception as error:
                last_error = error
        if last_error is not None:
            raise last_error
        analysis = _normalize_result(raw, setting["model"])
        repository.update_ai_analysis(leakage_id, analysis)
        return analysis
    except json.JSONDecodeError as error:
        analysis = failed_analysis("AI response was not valid JSON", model=setting.get("model"))
        repository.update_ai_analysis(leakage_id, analysis)
        return analysis
    except Exception as error:
        analysis = failed_analysis(error, model=setting.get("model"))
        repository.update_ai_analysis(leakage_id, analysis)
        return analysis
    finally:
        repository.release_analysis_slot()
