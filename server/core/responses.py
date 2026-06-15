# coding: utf-8
# @File        : responses.py
# @Author      : NanMing
# @Date        : 2026/6/8 12:18
# @Description : HTTP response helpers for the SkyRadar API payload shape.

"""HTTP response helpers for the SkyRadar API payload shape."""

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


def json_response(data, status_code=200):
    from fastapi.responses import JSONResponse

    return JSONResponse(content=jsonable(data), status_code=status_code)


def rest_payload(data=None, *, meta=None, links=None):
    payload = {"data": jsonable(data)}
    if meta is not None:
        payload["meta"] = jsonable(meta)
    if links is not None:
        payload["links"] = jsonable(links)
    return payload


def rest_response(data=None, *, status_code=200, meta=None, links=None):
    from fastapi.responses import JSONResponse

    return JSONResponse(
        content=rest_payload(data, meta=meta, links=links),
        status_code=status_code,
    )


def rest_error_response(error, message, *, status_code=400, detail=None, request_id=None):
    from fastapi.responses import JSONResponse

    payload = {
        "error": error,
        "message": message,
    }
    if detail is not None:
        payload["detail"] = jsonable(detail)
    if request_id is not None:
        payload["request_id"] = request_id
    return JSONResponse(content=payload, status_code=status_code)


__all__ = [
    "jsonable",
    "json_response",
    "rest_error_response",
    "rest_payload",
    "rest_response",
]
