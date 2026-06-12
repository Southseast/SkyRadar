# coding: utf-8
# @File        : test_domain_cohesion.py
# @Author      : NanMing
# @Date        : 2026/6/9 10:07
# @Description : Tests API route and service domain cohesion.

def test_http_routes_import_domain_local_services():
    from api.docs import routes as docs_routes
    from api.docs import service as docs_service
    from api.health import routes as health_routes
    from api.health import service as health_service
    from api.results import routes as results_routes
    from api.results import service as results_service
    from api.settings import routes as settings_routes
    from api.settings import service as settings_service
    from api.statistics import routes as statistics_routes
    from api.statistics import service as statistics_service

    assert docs_routes.docs_service is docs_service
    assert health_routes.health_service is health_service
    assert results_routes.results_service is results_service
    assert settings_routes.settings_service is settings_service
    assert statistics_routes.statistics_service is statistics_service


def test_worker_tasks_import_domain_local_services():
    from api.github_search import service as github_search_service
    from api.notifications import service as notifications_service
    from workers import schedule_tasks, search_tasks

    assert schedule_tasks.worker_service is github_search_service
    assert search_tasks.worker_service is github_search_service
    assert search_tasks.notification_service is notifications_service
