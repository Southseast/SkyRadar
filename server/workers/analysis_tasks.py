# coding: utf-8
# @File        : analysis_tasks.py
# @Author      : NanMing
# @Date        : 2026/7/2
# @Description : Huey tasks for AI leakage analysis.

"""Huey tasks for AI leakage analysis."""

from api.ai_analysis import service as ai_analysis_service
from api.notifications import service as notification_service
from workers.huey_app import huey


@huey.task()
def analyze_leakage(leakage_id, force=False):
    if force:
        ai_analysis_service.mark_pending(leakage_id, force=True)
    result = ai_analysis_service.analyze_leakage_now(leakage_id)
    if result.get("status") == "deferred":
        analyze_leakage.schedule(args=(leakage_id, False), delay=10)
        return
    if ai_analysis_service.should_notify_webhook_for_analysis(result):
        notice = ai_analysis_service.useful_project_notice(leakage_id, result)
        notification_service.send_webhook_notice("AI 有用项目", [notice])


__all__ = ["analyze_leakage"]
