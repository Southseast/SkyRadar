# coding: utf-8
# @File        : schemas.py
# @Author      : NanMing
# @Date        : 2026/6/10 16:17
# @Description : Defines API documentation response schemas.

from pydantic import BaseModel


class ApiDocsDisabledResponse(BaseModel):
    status: int = 404
    msg: str = "API docs disabled"
    result: list = []
