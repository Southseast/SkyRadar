# coding: utf-8
# @File        : test_github_integration.py
# @Author      : NanMing
# @Date        : 2026/6/8 14:01
# @Description : Tests GitHub integration behavior.

from integrations import github as github_integration


class _SearchRate:
    limit = 30
    remaining = 29


class _DirectRateLimit:
    search = _SearchRate()


class _CurrentResources:
    search = _SearchRate()


class _CurrentRateLimit:
    resources = _CurrentResources()


class _Client:
    def __init__(self, rate_limit):
        self._rate_limit = rate_limit

    def get_rate_limit(self):
        return self._rate_limit


def test_search_rate_limit_supports_direct_pygithub_shape():
    assert github_integration.search_rate_limit(_Client(_DirectRateLimit())) == {
        "limit": 30,
        "remaining": 29,
    }


def test_search_rate_limit_supports_current_pygithub_resources_shape():
    assert github_integration.search_rate_limit(_Client(_CurrentRateLimit())) == {
        "limit": 30,
        "remaining": 29,
    }
