# coding: utf-8
# @File        : service.py
# @Author      : NanMing
# @Date        : 2026/6/12 11:05
# @Description : Implements health check service logic.

import requests

from core.config import load_settings
from core.database import create_mongo_client


def health_status():
    try:
        github_response = requests.get("https://api.github.com/", timeout=30)
        github = github_response.status_code < 500
    except Exception as error:
        github = str(error)

    try:
        settings = load_settings()
        client = create_mongo_client(
            settings.mongodb_uri,
            connect=False,
            socketTimeoutMS=50,
            serverSelectionTimeoutMS=500,
        )
        mongodb = client.get_database(settings.mongodb_database).command("ping")
    except Exception as error:
        mongodb = str(error)

    return {"github": github, "mongodb": mongodb}
