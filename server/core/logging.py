# coding: utf-8
# @File        : logging.py
# @Author      : NanMing
# @Date        : 2026/6/11 14:36
# @Description : Logging boundary used by services and integrations.

"""Logging boundary used by services and integrations."""

from loguru import logger


FORMAT = "{time:YYYY-MM-DD HH:mm:ss.SSS} [{name}] [{level}] [{file.path}:{line} {function}] {message}"

logger.remove()
logger.add("SkyRadar.log", level="INFO", format=FORMAT)

__all__ = ["logger"]
