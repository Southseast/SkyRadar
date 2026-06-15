# coding: utf-8
# @File        : conftest.py
# @Author      : NanMing
# @Date        : 2026/6/11 16:23
# @Description : Provides shared pytest fixtures and import stubs.

import importlib.util
import sys
import types
import pytest

def _install_optional_import_stubs():
    if importlib.util.find_spec("github") is None:
        github_stub = types.ModuleType("github")

        class _Github:
            pass

        class _GithubException(Exception):
            pass

        class _BadCredentialsException(_GithubException):
            pass

        github_stub.Github = _Github
        github_stub.GithubException = _GithubException
        github_stub.BadCredentialsException = _BadCredentialsException
        sys.modules["github"] = github_stub

    if importlib.util.find_spec("psutil") is None:
        psutil_stub = types.ModuleType("psutil")
        psutil_stub.pid_exists = lambda pid: False
        sys.modules["psutil"] = psutil_stub

    if importlib.util.find_spec("redis") is None:
        redis_stub = types.ModuleType("redis")

        class _Redis:
            def __init__(self, *args, **kwargs):
                pass

        redis_stub.Redis = _Redis
        sys.modules["redis"] = redis_stub

@pytest.fixture
def app():
    _install_optional_import_stubs()
    from api import app as fastapi_app

    return fastapi_app

class ResponseAdapter:
    def __init__(self, response):
        self._response = response

    @property
    def status_code(self):
        return self._response.status_code

    @property
    def data(self):
        return self._response.content

    @property
    def mimetype(self):
        return self._response.headers.get("content-type", "").split(";", 1)[0]

    def get_json(self):
        return self._response.json()

    def __getattr__(self, name):
        return getattr(self._response, name)

class ClientAdapter:
    def __init__(self, client):
        self._client = client

    def get(self, url, **kwargs):
        return self._request("get", url, **kwargs)

    def post(self, url, **kwargs):
        return self._request("post", url, **kwargs)

    def patch(self, url, **kwargs):
        return self._request("patch", url, **kwargs)

    def put(self, url, **kwargs):
        return self._request("put", url, **kwargs)

    def delete(self, url, **kwargs):
        return self._request("delete", url, **kwargs)

    def _request(self, method, url, **kwargs):
        query_string = kwargs.pop("query_string", None)
        if query_string is not None:
            kwargs["params"] = query_string
        response = getattr(self._client, method)(url, **kwargs)
        return ResponseAdapter(response)

@pytest.fixture
def client(app):
    from fastapi.testclient import TestClient

    return ClientAdapter(TestClient(app))
