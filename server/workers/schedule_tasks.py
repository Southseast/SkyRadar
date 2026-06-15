# coding: utf-8
# @File        : schedule_tasks.py
# @Author      : NanMing
# @Date        : 2026/6/11 16:48
# @Description : Huey periodic tasks and scheduling entrypoints.

"""Huey periodic tasks and scheduling entrypoints."""

import os

from huey import crontab

from api.github_search import service as worker_service
from workers.huey_app import huey
from workers.search_tasks import search


_schedule_initialized = False


def initialize_schedule_once():
    global _schedule_initialized
    if _schedule_initialized:
        return
    worker_service.initialize_search_schedule(os.getpid())
    _schedule_initialized = True


@huey.periodic_task(crontab(minute="*/2"))
def update_github_rate_remaining():
    initialize_schedule_once()
    worker_service.update_github_rate_remaining()


def create_github_client():
    return worker_service.create_github_client()


@huey.periodic_task(crontab(minute="*"))
def schedule_github_search():
    initialize_schedule_once()
    worker_service.schedule_github_search(
        lambda query, page, github_account, delay: search.schedule(
            args=(query, page, github_account),
            delay=delay,
        ),
        lambda: huey.pending_count() + huey.scheduled_count(),
    )


__all__ = [
    "create_github_client",
    "initialize_schedule_once",
    "schedule_github_search",
    "update_github_rate_remaining",
]
