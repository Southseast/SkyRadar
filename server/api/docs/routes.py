# coding: utf-8
# @File        : routes.py
# @Author      : NanMing
# @Date        : 2026/6/9 10:36
# @Description : Defines API documentation routes.

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from api.docs import service as docs_service
from core.responses import json_response, rest_error_response


router = APIRouter()


@router.get("/api/v1/openapi.json")
def openapi_json():
    if not docs_service.api_docs_enabled():
        return rest_error_response("api_docs_disabled", "API docs disabled", status_code=404)
    return json_response(docs_service.load_openapi_schema())


@router.get("/api/v1/docs")
def swagger_docs():
    if not docs_service.api_docs_enabled():
        return rest_error_response("api_docs_disabled", "API docs disabled", status_code=404)
    return HTMLResponse(docs_service.SWAGGER_HTML)
