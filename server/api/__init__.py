#!/usr/bin/env python3
# coding: utf-8
# @File        : __init__.py
# @Author      : NanMing
# @Date        : 2026/6/12 11:08
# @Description : Creates the FastAPI application and registers API routers.

from fastapi import FastAPI

from .docs.routes import router as docs_router
from .health.routes import router as health_router
from .results.routes import router as results_router
from .settings.routes import router as settings_router
from .shared import as_bool, as_int, request_params, response
from .statistics.routes import router as statistics_router


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

app.include_router(health_router)
app.include_router(docs_router)
app.include_router(results_router)
app.include_router(statistics_router)
app.include_router(settings_router)


__all__ = ["app", "as_bool", "as_int", "request_params", "response"]
