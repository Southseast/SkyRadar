# coding: utf-8
# @File        : openai_client.py
# @Author      : NanMing
# @Date        : 2026/7/2
# @Description : Wraps OpenAI SDK calls for leakage analysis.

import json


def create_client(api_key, base_url=None, timeout=None):
    from openai import OpenAI

    kwargs = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    if timeout:
        kwargs["timeout"] = float(timeout)
    return OpenAI(**kwargs)


def analyze(client, model, messages):
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content
    return json.loads(content)
