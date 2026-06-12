# coding: utf-8
# @File        : github.py
# @Author      : NanMing
# @Date        : 2026/6/9 10:12
# @Description : Wraps GitHub search and rate limit integration behavior.

from github import BadCredentialsException, Github


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.81 Safari/537.36"
)
DEFAULT_USER_AGENT = USER_AGENT


def create_client(username, password, user_agent=USER_AGENT):
    return Github(username, password, user_agent=user_agent)


def search_code(client, keyword):
    return client.search_code(query=keyword, sort="indexed", order="desc")


def search_rate_limit(client):
    rate_limit = client.get_rate_limit()
    search = getattr(rate_limit, "search", None) or rate_limit.resources.search
    return {"limit": int(search.limit), "remaining": int(search.remaining)}
