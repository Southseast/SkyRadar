# coding: utf-8
# @File        : routes.py
# @Author      : NanMing
# @Date        : 2026/6/11 14:14
# @Description : Defines results API routes.

from fastapi import APIRouter, Query

from api.results import service as results_service
from core.responses import rest_error_response, rest_response

from .schemas import LeakageListParams, LeakagePatchPayload


router = APIRouter()


def _not_found_response(leakage_id):
    return rest_error_response(
        "leakage_result_not_found",
        "Leakage result not found",
        status_code=404,
        detail={"id": leakage_id},
    )


@router.get("/api/v1/leakages")
def leakage_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tag: str | None = None,
    language: str | None = None,
    security: int | None = Query(None, ge=0, le=1),
    ignored: bool | None = None,
    reviewed: bool | None = None,
):
    params = LeakageListParams(
        page=page,
        page_size=page_size,
        tag=tag,
        language=language,
        security=security,
        ignored=ignored,
        reviewed=reviewed,
    )
    result = results_service.leakage_list(
        tag=params.tag,
        language=params.language,
        security=params.security,
        ignored=params.ignored,
        reviewed=params.reviewed,
        page=params.page,
        page_size=params.page_size,
    )
    return rest_response(
        result["items"],
        meta={
            "total": result["total"],
            "page": result["page"],
            "page_size": result["page_size"],
        },
    )


@router.get("/api/v1/leakages/{leakage_id}")
def leakage_info(leakage_id: str):
    try:
        return rest_response(results_service.leakage_info(leakage_id))
    except results_service.LeakageResultNotFound:
        return _not_found_response(leakage_id)


@router.get("/api/v1/leakages/{leakage_id}/code")
def leakage_code(leakage_id: str):
    try:
        return rest_response(results_service.leakage_code(leakage_id))
    except results_service.LeakageResultNotFound:
        return _not_found_response(leakage_id)


@router.patch("/api/v1/leakages/{leakage_id}")
def patch_leakage(leakage_id: str, payload: LeakagePatchPayload):
    try:
        result = results_service.patch_leakage(leakage_id, payload.model_dump(exclude_unset=True))
    except results_service.InvalidResultPatch as error:
        return rest_error_response("invalid_result_patch", str(error), status_code=422)
    except results_service.LeakageResultNotFound:
        return _not_found_response(leakage_id)
    return rest_response(result)
