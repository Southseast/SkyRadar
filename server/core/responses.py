# coding: utf-8
# @File        : responses.py
# @Author      : NanMing
# @Date        : 2026/6/8 12:18
# @Description : HTTP response helpers for the SkyRadar API payload shape.

"""HTTP response helpers for the SkyRadar API payload shape."""

DEFAULT_SUCCESS_MSG = "获取信息成功"


def jsonable(value):
    if isinstance(value, list):
        return [jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if value.__class__.__name__ == "ObjectId":
        return str(value)
    return value


def api_payload(result=None, *, status=200, msg=DEFAULT_SUCCESS_MSG, **extra):
    payload = {
        "status": status,
        "msg": msg,
        "result": jsonable(result),
    }
    payload.update({key: jsonable(value) for key, value in extra.items()})
    return payload


def fastapi_response(result=None, *, status=200, msg=DEFAULT_SUCCESS_MSG, http_status=200, **extra):
    from fastapi.responses import JSONResponse

    return JSONResponse(
        content=api_payload(result, status=status, msg=msg, **extra),
        status_code=http_status,
    )


def json_response(data, status_code=200):
    from fastapi.responses import JSONResponse

    return JSONResponse(content=jsonable(data), status_code=status_code)


def api_shape_response(status, msg, result, **extra):
    return api_payload(result, status=status, msg=msg, **extra)

__all__ = [
    "DEFAULT_SUCCESS_MSG",
    "api_shape_response",
    "api_payload",
    "fastapi_response",
    "jsonable",
    "json_response",
]
