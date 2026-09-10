# coding: utf-8
# @File        : test_ai_analysis_service.py
# @Author      : NanMing
# @Date        : 2026/7/2
# @Description : Tests AI leakage analysis service behavior.

import base64
import json

from api.ai_analysis import service


def test_analyze_leakage_updates_structured_success(monkeypatch):
    captured = {"updates": []}
    leakage = {
        "_id": "leak-1",
        "project": "org/repo",
        "filepath": "secret.py",
        "tag": "credential",
        "code": base64.b64encode(b"password = 'secret'").decode(),
        "affect": [{"type": "secret", "value": "secret"}],
    }

    monkeypatch.setattr(
        service,
        "effective_openai_setting",
        lambda: {
            **service.DEFAULT_OPENAI_SETTING,
            "enabled": True,
            "api_key": "sk-test",
            "concurrency": 1,
        },
    )
    monkeypatch.setattr(service.repository, "get_leakage_for_analysis", lambda leakage_id: leakage)
    monkeypatch.setattr(service.repository, "claim_analysis_slot", lambda concurrency: {"running_count": 1})
    monkeypatch.setattr(service.repository, "release_analysis_slot", lambda: None)
    monkeypatch.setattr(
        service.repository,
        "update_ai_analysis",
        lambda leakage_id, analysis: captured["updates"].append(analysis),
    )

    result = service.analyze_leakage_now(
        "leak-1",
        client_factory=lambda *args, **kwargs: object(),
        analyzer=lambda client, model, messages: {
            "risk_level": "high",
            "summary": "疑似凭据泄露",
            "evidence": ["包含 password 赋值"],
            "recommendation": "轮换凭据",
            "false_positive_reason": "测试样例",
            "is_useful": True,
            "usefulness_reason": "命中关注方向",
            "matched_interests": ["浏览器指纹"],
        },
    )

    assert result["status"] == "success"
    assert result["risk_level"] == "high"
    assert result["is_useful"] is True
    assert result["usefulness_reason"] == "命中关注方向"
    assert result["matched_interests"] == ["浏览器指纹"]
    assert result["model"] == "gpt-4o-mini"
    assert captured["updates"][0]["status"] == "running"
    assert captured["updates"][1]["status"] == "success"


def test_analyze_leakage_uses_editable_prompt_and_interests(monkeypatch):
    captured = {}

    monkeypatch.setattr(
        service,
        "effective_openai_setting",
        lambda: {
            **service.DEFAULT_OPENAI_SETTING,
            "enabled": True,
            "api_key": "sk-test",
            "concurrency": 1,
            "usefulness_prompt": "关注威胁情报分析",
            "interests": "浏览器指纹与自动化规避",
        },
    )
    monkeypatch.setattr(service.repository, "get_leakage_for_analysis", lambda leakage_id: {"_id": leakage_id, "project": "org/repo", "code": ""})
    monkeypatch.setattr(service.repository, "claim_analysis_slot", lambda concurrency: {"running_count": 1})
    monkeypatch.setattr(service.repository, "release_analysis_slot", lambda: None)
    monkeypatch.setattr(service.repository, "update_ai_analysis", lambda leakage_id, analysis: None)

    def analyzer(client, model, messages):
        captured["messages"] = messages
        return {
            "risk_level": "low",
            "summary": "项目有参考价值",
            "evidence": [],
            "recommendation": "跟踪 release",
            "false_positive_reason": "",
            "is_useful": True,
            "usefulness_reason": "符合浏览器自动化关注方向",
            "matched_interests": ["自动化规避"],
        }

    result = service.analyze_leakage_now(
        "leak-1",
        client_factory=lambda *args, **kwargs: object(),
        analyzer=analyzer,
    )

    system_message = captured["messages"][0]["content"]
    assert "关注威胁情报分析" in system_message
    assert "浏览器指纹与自动化规避" in system_message
    assert result["is_useful"] is True


def test_analyze_leakage_defers_when_concurrency_slot_is_unavailable(monkeypatch):
    monkeypatch.setattr(
        service,
        "effective_openai_setting",
        lambda: {
            **service.DEFAULT_OPENAI_SETTING,
            "enabled": True,
            "api_key": "sk-test",
            "concurrency": 1,
        },
    )
    monkeypatch.setattr(service.repository, "get_leakage_for_analysis", lambda leakage_id: {"_id": leakage_id})
    monkeypatch.setattr(service.repository, "claim_analysis_slot", lambda concurrency: None)

    result = service.analyze_leakage_now("leak-1")

    assert result == {"status": "deferred"}


def test_analyze_leakage_marks_invalid_json_as_failed(monkeypatch):
    captured = {"updates": []}

    monkeypatch.setattr(
        service,
        "effective_openai_setting",
        lambda: {
            **service.DEFAULT_OPENAI_SETTING,
            "enabled": True,
            "api_key": "sk-test",
            "concurrency": 1,
        },
    )
    monkeypatch.setattr(service.repository, "get_leakage_for_analysis", lambda leakage_id: {"_id": leakage_id, "code": ""})
    monkeypatch.setattr(service.repository, "claim_analysis_slot", lambda concurrency: {"running_count": 1})
    monkeypatch.setattr(service.repository, "release_analysis_slot", lambda: None)
    monkeypatch.setattr(
        service.repository,
        "update_ai_analysis",
        lambda leakage_id, analysis: captured["updates"].append(analysis),
    )

    result = service.analyze_leakage_now(
        "leak-1",
        client_factory=lambda *args, **kwargs: object(),
        analyzer=lambda client, model, messages: (_ for _ in ()).throw(json.JSONDecodeError("bad", "not-json", 0)),
    )

    assert result["status"] == "failed"
    assert result["error"] == "AI response was not valid JSON"
    assert captured["updates"][-1]["status"] == "failed"


def test_analyze_leakage_retries_transient_errors(monkeypatch):
    captured = {"updates": [], "attempts": 0}

    monkeypatch.setattr(
        service,
        "effective_openai_setting",
        lambda: {
            **service.DEFAULT_OPENAI_SETTING,
            "enabled": True,
            "api_key": "sk-test",
            "concurrency": 1,
            "max_retries": 1,
        },
    )
    monkeypatch.setattr(service.repository, "get_leakage_for_analysis", lambda leakage_id: {"_id": leakage_id, "code": ""})
    monkeypatch.setattr(service.repository, "claim_analysis_slot", lambda concurrency: {"running_count": 1})
    monkeypatch.setattr(service.repository, "release_analysis_slot", lambda: None)
    monkeypatch.setattr(
        service.repository,
        "update_ai_analysis",
        lambda leakage_id, analysis: captured["updates"].append(analysis),
    )

    def flaky_analyzer(client, model, messages):
        captured["attempts"] += 1
        if captured["attempts"] == 1:
            raise RuntimeError("temporary outage")
        return {
            "risk_level": "medium",
            "summary": "疑似敏感信息",
            "evidence": [],
            "recommendation": "复核",
            "false_positive_reason": "",
        }

    result = service.analyze_leakage_now(
        "leak-1",
        client_factory=lambda *args, **kwargs: object(),
        analyzer=flaky_analyzer,
    )

    assert captured["attempts"] == 2
    assert result["status"] == "success"
    assert result["risk_level"] == "medium"
    assert captured["updates"][-1]["status"] == "success"
