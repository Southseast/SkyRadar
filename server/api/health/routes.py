# coding: utf-8
# @File        : routes.py
# @Author      : NanMing
# @Date        : 2026/6/11 10:18
# @Description : Defines health check API routes.

from fastapi import APIRouter

from api.health import service as health_service

from ..shared import response


router = APIRouter()


@router.get("/api/health")
def health():
    return response(health_service.health_status())
