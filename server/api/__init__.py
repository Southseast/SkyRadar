#!/usr/bin/env python3
# coding: utf-8
# @File        : __init__.py
# @Author      : NanMing
# @Date        : 2026/6/12 11:08
# @Description : Creates the FastAPI application and registers API routers.

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.responses import rest_error_response
from .docs.routes import router as docs_router
from .health.routes import router as health_router
from .results.routes import router as results_router
from .settings.routes import router as settings_router
from .shared import as_bool, as_int, request_params
from .statistics.routes import router as statistics_router


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return rest_error_response(
        "validation_error",
        "Request validation failed",
        status_code=422,
        detail=exc.errors(),
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return rest_error_response(
        "http_error",
        str(exc.detail),
        status_code=exc.status_code,
    )


app.include_router(health_router)
app.include_router(docs_router)
app.include_router(results_router)
app.include_router(statistics_router)
app.include_router(settings_router)


__all__ = ["app", "as_bool", "as_int", "request_params"]
