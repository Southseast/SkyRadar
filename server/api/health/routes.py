# coding: utf-8
# @File        : routes.py
# @Author      : NanMing
# @Date        : 2026/6/11 10:18
# @Description : Defines health check API routes.

from fastapi import APIRouter

from api.health import service as health_service
from core.responses import rest_response


router = APIRouter()


@router.get("/api/v1/health")
def health():
    return rest_response(health_service.health_status())
