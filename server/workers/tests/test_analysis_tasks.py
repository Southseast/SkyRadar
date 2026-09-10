# coding: utf-8
# @File        : test_analysis_tasks.py
# @Author      : NanMing
# @Date        : 2026/7/2
# @Description : Tests AI analysis worker notification behavior.

from workers import analysis_tasks


def test_analyze_leakage_sends_webhook_when_ai_marks_project_useful(monkeypatch):
    captured = {}
    analysis = {"status": "success", "is_useful": True, "usefulness_reason": "符合关注方向"}

    monkeypatch.setattr(analysis_tasks.ai_analysis_service, "analyze_leakage_now", lambda leakage_id: analysis)
    monkeypatch.setattr(analysis_tasks.ai_analysis_service, "should_notify_webhook_for_analysis", lambda result: True)
    monkeypatch.setattr(analysis_tasks.ai_analysis_service, "useful_project_notice", lambda leakage_id, result: "org/repo 符合关注方向")
    monkeypatch.setattr(
        analysis_tasks.notification_service,
        "send_webhook_notice",
        lambda tag, results: captured.update({"tag": tag, "results": results}),
    )

    analysis_tasks.analyze_leakage.call_local("leak-1", False)

    assert captured == {"tag": "AI 有用项目", "results": ["org/repo 符合关注方向"]}

