# coding: utf-8
# @File        : routes.py
# @Author      : NanMing
# @Date        : 2026/6/9 10:36
# @Description : Defines API documentation routes.

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from api.docs import service as docs_service

from ..shared import response


router = APIRouter()


@router.get("/api/openapi.json")
def openapi_json():
    if not docs_service.api_docs_enabled():
        return response({"status": 404, "msg": "API docs disabled", "result": []}, status_code=404)
    return response(docs_service.load_openapi_schema())


@router.get("/api/docs")
def swagger_docs():
    if not docs_service.api_docs_enabled():
        return response({"status": 404, "msg": "API docs disabled", "result": []}, status_code=404)
    return HTMLResponse(docs_service.SWAGGER_HTML)
