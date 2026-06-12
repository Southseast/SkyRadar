# coding: utf-8
# @File        : routes.py
# @Author      : NanMing
# @Date        : 2026/6/9 14:44
# @Description : Defines statistics API routes.

from fastapi import APIRouter

from api.statistics import service as statistics_service

from ..shared import response
from .schemas import StatisticParams, TrendParams


router = APIRouter()


@router.get("/api/trend")
def trend(tag: str | None = None):
    params = TrendParams(tag=tag)
    return response(statistics_service.trend(tag=params.tag))


@router.get("/api/statistic")
def statistic(by: str = "tag", tag: str = ""):
    params = StatisticParams(by=by, tag=tag)
    return response(statistics_service.statistic(by=params.by, tag=params.tag))
