# coding: utf-8
# @File        : config.py
# @Author      : NanMing
# @Date        : 2026/6/11 15:58
# @Description : Configuration boundary for backend runtime settings.

"""Configuration boundary for backend runtime settings."""

from dataclasses import dataclass
import os
from pathlib import Path


TRUE_VALUES = {"1", "true", "yes", "on"}
DEFAULT_OPENAPI_PATH = Path("docs/api/openapi.yaml")


def _env(name, default=None):
    value = os.environ.get(name)
    return default if value is None or value == "" else value


def _env_bool(name, default=False):
    value = _env(name)
    if value is None:
        return default
    return value.strip().lower() in TRUE_VALUES


def _env_int(name, default):
    value = _env(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer") from error


@dataclass(frozen=True)
class Settings:
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "skyradar"
    mongodb_user: str | None = None
    mongodb_password: str | None = None
    mongodb_auth_source: str = "skyradar"
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_result_cache_db: int = 1
    api_docs_enabled: bool = False
    openapi_path: Path = DEFAULT_OPENAPI_PATH

    @classmethod
    def from_env(cls):
        return cls(
            mongodb_uri=_env("MONGODB_URI", "mongodb://localhost:27017"),
            mongodb_database=_env("MONGODB_DATABASE", "skyradar"),
            mongodb_user=_env("MONGODB_USER"),
            mongodb_password=_env("MONGODB_PASSWORD"),
            mongodb_auth_source=_env("MONGODB_AUTH_SOURCE", "skyradar"),
            redis_host=_env("REDIS_HOST", "localhost"),
            redis_port=_env_int("REDIS_PORT", 6379),
            redis_result_cache_db=_env_int("REDIS_RESULT_CACHE_DB", 1),
            api_docs_enabled=_env_bool("SKYRADAR_API_DOCS_ENABLED", False),
            openapi_path=Path(
                _env("SKYRADAR_OPENAPI_PATH", str(DEFAULT_OPENAPI_PATH))
            ),
        )


def load_settings():
    return Settings.from_env()


def get_settings():
    return load_settings()

__all__ = [
    "DEFAULT_OPENAPI_PATH",
    "TRUE_VALUES",
    "Settings",
    "get_settings",
    "load_settings",
]
