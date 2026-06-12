# coding: utf-8
# @File        : search_tasks.py
# @Author      : NanMing
# @Date        : 2026/6/10 17:28
# @Description : Huey tasks for GitHub search and notification delivery.

"""Huey tasks for GitHub search and notification delivery."""

from api.github_search import service as worker_service
from api.notifications import service as notification_service
from workers.huey_app import huey


@huey.task()
def search(query, page, github_or_account, github_username=None):
    def retry(next_query, next_page, next_account):
        search.schedule(
            args=(next_query, next_page, next_account),
            delay=huey.pending_count() + huey.scheduled_count(),
        )

    notices = worker_service.search_github_code(
        query,
        page,
        github_or_account,
        github_username,
        retry=retry,
    )
    worker_service.dispatch_search_notices(query.get("tag"), notices, send_mail_notice, send_webhook_notice)


@huey.task()
def send_webhook_notice(tag, results):
    notification_service.send_webhook_notice(tag, results)


@huey.task()
def send_mail_notice(content):
    notification_service.send_mail_notice(content)


__all__ = ["search", "send_webhook_notice", "send_mail_notice"]
