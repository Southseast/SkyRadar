# coding: utf-8
# @File        : routes.py
# @Author      : NanMing
# @Date        : 2026/6/9 14:44
# @Description : Defines statistics API routes.

from fastapi import APIRouter
from pydantic import ValidationError

from api.statistics import service as statistics_service
from core.responses import rest_error_response, rest_response

from .schemas import StatisticParams, TrendParams


router = APIRouter()


def _validation_detail(error):
    return [
        {
            "loc": item.get("loc", ()),
            "msg": item.get("msg", ""),
            "type": item.get("type", ""),
        }
        for item in error.errors()
    ]


@router.get("/api/v1/trends")
def trends(tag: str | None = None):
    params = TrendParams(tag=tag)
    return rest_response(statistics_service.summary(tag=params.tag))


@router.get("/api/v1/statistics")
def statistics(by: str = "tag", tag: str = ""):
    try:
        params = StatisticParams(by=by, tag=tag)
    except ValidationError as error:
        return rest_error_response(
            "invalid_breakdown",
            "Unsupported breakdown field",
            status_code=422,
            detail=_validation_detail(error),
        )
    return rest_response(statistics_service.breakdowns(by=params.by, tag=params.tag))
