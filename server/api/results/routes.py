# coding: utf-8
# @File        : routes.py
# @Author      : NanMing
# @Date        : 2026/6/11 14:14
# @Description : Defines results API routes.

from fastapi import APIRouter, Query, Request
from fastapi.concurrency import run_in_threadpool

from api.results import service as results_service

from ..shared import request_params, response
from .schemas import LeakageListParams


router = APIRouter()


@router.get("/api/leakage")
def leakage_list(
    status: str,
    tag: str | None = None,
    language: str | None = None,
    limit: int = 10,
    from_: int = Query(1, alias="from"),
):
    params = LeakageListParams(status=status, tag=tag, language=language, limit=limit, from_=from_)
    return response(
        results_service.leakage_list(
            params.status,
            tag=params.tag,
            language=params.language,
            limit=params.limit,
            from_=params.from_,
        )
    )


@router.patch("/api/leakage")
async def patch_leakage(request: Request):
    params = await request_params(request)
    result = await run_in_threadpool(results_service.patch_leakage, params)
    return response(result)


@router.get("/api/leakage/info")
def leakage_info(id: str):
    return response(results_service.leakage_info(id))


@router.get("/api/leakage/code")
def leakage_code(id: str):
    return response(results_service.leakage_code(id))
