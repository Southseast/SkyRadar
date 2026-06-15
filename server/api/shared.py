# coding: utf-8
# @File        : shared.py
# @Author      : NanMing
# @Date        : 2026/6/12 15:36
# @Description : Provides shared API response and query parsing helpers.

import json
from urllib.parse import parse_qs

from fastapi import Request

from core.responses import json_response


class InvalidQueryParameter(ValueError):
    def __init__(self, name, message):
        super().__init__(message)
        self.name = name
        self.message = message


def response(data, status_code=200):
    return json_response(data, status_code=status_code)


async def request_params(request: Request):
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type == "application/json":
        try:
            data = await request.json()
        except json.JSONDecodeError:
            data = {}
        return data if isinstance(data, dict) else {}

    body = await request.body()
    if not body:
        return {}
    parsed = parse_qs(body.decode("utf-8", errors="replace"), keep_blank_values=True)
    return {key: values[-1] if values else "" for key, values in parsed.items()}


def as_int(params, name, default=None):
    value = params.get(name, default)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise InvalidQueryParameter(name, f"{name} must be an integer") from error


def as_bool(params, name, default=False):
    value = params.get(name, default)
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}
