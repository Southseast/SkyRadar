# coding: utf-8
# @File        : service.py
# @Author      : NanMing
# @Date        : 2026/6/11 17:55
# @Description : Implements GitHub search service logic.

import datetime
import hashlib
import os
import time

from api.github_search import assets as asset_service
from api.github_search import repository as worker_repository
from core.logging import logger
from integrations import github as github_integration


SEARCH_TYPE_CODE = "code"
SEARCH_TYPE_REPOSITORIES = "repositories"


def initialize_search_schedule(pid):
    worker_repository.ensure_task_setting(pid, int(time.time()))
    return worker_repository.task_minute()


def create_github_client():
    if not worker_repository.has_github_capacity():
        logger.error("请配置github账号")
        return None
    github_account = worker_repository.choose_github_account()
    if not github_account:
        logger.error("请配置github账号")
        return None
    github_username = github_account.get("username")
    github_password = github_account.get("password")
    github_client = github_integration.create_client(github_username, github_password)
    return github_client, github_username


def _resolve_github(github_or_account, github_username=None):
    if github_username:
        return github_or_account, github_username
    if isinstance(github_or_account, dict):
        github_username = github_or_account.get("username")
        github_password = github_or_account.get("password")
        github_client = github_integration.create_client(github_username, github_password)
        return github_client, github_username
    return github_or_account, github_username


def _retry_with_next_account(query, page, retry):
    next_account = worker_repository.choose_github_account()
    if next_account:
        retry(query, page, next_account)


def _query_search_type(query):
    search_type = str(query.get("search_type") or SEARCH_TYPE_CODE).strip().lower()
    if search_type in {"repo", "repository"}:
        return SEARCH_TYPE_REPOSITORIES
    if search_type == SEARCH_TYPE_REPOSITORIES:
        return SEARCH_TYPE_REPOSITORIES
    return SEARCH_TYPE_CODE


def _search_github(github_client, query):
    if _query_search_type(query) == SEARCH_TYPE_REPOSITORIES:
        return github_integration.search_repositories(github_client, query.get("keyword"))
    return github_integration.search_code(github_client, query.get("keyword"))


def _as_datetime(value):
    if isinstance(value, datetime.datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            pass
    return datetime.datetime.utcnow()


def _repository_leakage(query, repo):
    owner = getattr(repo, "owner", None)
    full_name = getattr(repo, "full_name", None) or getattr(repo, "name", "")
    repo_id = getattr(repo, "id", None) or full_name
    detected_at = _as_datetime(
        getattr(repo, "updated_at", None)
        or getattr(repo, "pushed_at", None)
        or getattr(repo, "created_at", None)
    )
    return {
        "_id": hashlib.md5("{}:repositories:{}".format(query.get("tag"), repo_id).encode("utf-8")).hexdigest(),
        "link": getattr(repo, "html_url", ""),
        "project": full_name,
        "project_url": getattr(repo, "html_url", ""),
        "language": getattr(repo, "language", None),
        "username": getattr(owner, "login", ""),
        "avatar_url": getattr(owner, "avatar_url", ""),
        "filepath": full_name,
        "filename": getattr(repo, "name", full_name),
        "security": 0,
        "ignore": 0,
        "tag": query.get("tag"),
        "search_type": SEARCH_TYPE_REPOSITORIES,
        "code": "",
        "affect": [],
        "datetime": detected_at,
        "timestamp": detected_at.timestamp(),
    }


def _is_blacklisted(link):
    link = str(link or "")
    for blacklist in worker_repository.iter_blacklist():
        blacklist_text = str(blacklist.get("text") or "")
        if blacklist_text and blacklist_text.lower() in link.lower():
            logger.warning("{} 包含白名单中的 {}".format(link, blacklist.get("text")))
            return True
    return False


def _append_repository_notices(leakage, mail_notice_list, webhook_notice_list):
    if worker_repository.result_exists({"project": leakage.get("project"), "ignore": 1}):
        return False
    if not worker_repository.result_exists({"project": leakage.get("project"), "security": 0}):
        mail_notice_list.append(
            "更新时间:{} 地址: <a href={}>{}</a>".format(
                leakage.get("datetime"), leakage.get("link"), leakage.get("project")
            )
        )
        webhook_notice_list.append(
            "[{}]({}) 更新于 {}".format(
                leakage.get("project"),
                leakage.get("link"),
                leakage.get("datetime"),
            )
        )
    return True


def search_github_code(query, page, github_or_account, github_username=None, *, asset_extractor=None, retry):
    asset_extractor = asset_extractor or asset_service.default_extractor()
    mail_notice_list = []
    webhook_notice_list = []
    search_type = _query_search_type(query)
    logger.info(
        "开始抓取: tag is {} keyword is {}, type is {}, page is {}".format(
            query.get("tag"), query.get("keyword"), search_type, page + 1
        )
    )
    try:
        github_client, github_username = _resolve_github(github_or_account, github_username)
        repos = _search_github(github_client, query)
        rate = github_integration.search_rate_limit(github_client)
        worker_repository.update_github_rate_remaining(github_username, rate["remaining"])
    except Exception as error:
        logger.critical(error)
        logger.critical("触发限制啦")
        if "Not Found" not in str(getattr(error, "data", error)):
            _retry_with_next_account(query, page, retry)
        return {"mail": [], "webhook": []}

    try:
        for repo in repos.get_page(page):
            worker_repository.touch_task(os.getpid(), int(time.time()))
            if search_type == SEARCH_TYPE_REPOSITORIES:
                leakage = _repository_leakage(query, repo)
                if worker_repository.result_exists({"_id": leakage.get("_id")}):
                    continue
                if _is_blacklisted(leakage.get("link", "")):
                    continue
                if not _append_repository_notices(leakage, mail_notice_list, webhook_notice_list):
                    continue
                try:
                    worker_repository.insert_result(leakage)
                    logger.info(leakage.get("project"))
                except worker_repository.DuplicateKeyError:
                    logger.info("已存在")
                logger.info("抓取仓库：{} {}".format(query.get("tag"), leakage.get("link")))
                continue

            if worker_repository.result_exists({"_id": repo.sha}):
                continue
            try:
                code = str(repo.content).replace("\n", "")
            except Exception:
                code = ""
            leakage = {
                "link": repo.html_url,
                "project": repo.repository.full_name,
                "project_url": repo.repository.html_url,
                "_id": repo.sha,
                "language": repo.repository.language,
                "username": repo.repository.owner.login,
                "avatar_url": repo.repository.owner.avatar_url,
                "filepath": repo.path,
                "filename": repo.name,
                "security": 0,
                "ignore": 0,
                "tag": query.get("tag"),
                "search_type": SEARCH_TYPE_CODE,
                "code": code,
            }
            try:
                leakage["affect"] = asset_extractor.get_affect_assets(repo.decoded_content)
            except Exception as error:
                logger.critical("{} {}".format(error, leakage.get("link")))
                leakage["affect"] = []
            if int(repo.raw_headers.get("x-ratelimit-remaining")) == 0:
                logger.critical("剩余使用次数: {}".format(repo.raw_headers.get("x-ratelimit-remaining")))
                return {"mail": mail_notice_list, "webhook": webhook_notice_list}
            last_modified = datetime.datetime.strptime(repo.last_modified, "%a, %d %b %Y %H:%M:%S %Z")
            leakage["datetime"] = last_modified
            leakage["timestamp"] = last_modified.timestamp()
            if _is_blacklisted(leakage.get("link")):
                continue
            if worker_repository.result_exists({"project": leakage.get("project"), "ignore": 1}):
                continue
            if not worker_repository.result_exists({"project": leakage.get("project"), "filepath": leakage.get("filepath"), "security": 0}):
                mail_notice_list.append(
                    "上传时间:{} 地址: <a href={}>{}/{}</a>".format(
                        leakage.get("datetime"), leakage.get("link"), leakage.get("project"), leakage.get("filename")
                    )
                )
                webhook_notice_list.append(
                    "[{}/{}]({}) 上传于 {}".format(
                        leakage.get("project").split(".")[-1],
                        leakage.get("filename"),
                        leakage.get("link"),
                        leakage.get("datetime"),
                    )
                )
            try:
                worker_repository.insert_result(leakage)
                logger.info(leakage.get("project"))
            except worker_repository.DuplicateKeyError:
                logger.info("已存在")
            logger.info("抓取关键字：{} {}".format(query.get("tag"), leakage.get("link")))
    except Exception as error:
        if "Not Found" not in str(getattr(error, "data", error)):
            _retry_with_next_account(query, page, retry)
        logger.critical(error)
        logger.error("抓取: tag is {} keyword is {}, page is {} 失败".format(query.get("tag"), query.get("keyword"), page + 1))
        return {"mail": [], "webhook": []}

    logger.info(
        "抓取: tag is {} keyword is {}, type is {}, page is {} 成功".format(
            query.get("tag"), query.get("keyword"), search_type, page + 1
        )
    )
    worker_repository.update_query_success(query.get("tag"), page, repos.totalCount, time.time())
    return {"mail": mail_notice_list, "webhook": webhook_notice_list}


def dispatch_search_notices(tag, notices, send_mail_notice_task, send_webhook_notice_task):
    if notices["mail"]:
        main_content = "<h2>规则名称: {}</h2><br>{}".format(tag, "<br>".join(notices["mail"]))
        send_mail_notice_task(main_content)
    send_webhook_notice_task(tag, notices["webhook"])


def update_github_rate_remaining():
    for account in worker_repository.iter_github_accounts():
        github_username = account.get("username")
        github_password = account.get("password")
        try:
            github_client = github_integration.create_client(github_username, github_password)
            rate = github_integration.search_rate_limit(github_client)
            worker_repository.update_github_rate_limit(github_username, rate["remaining"], rate["limit"])
        except Exception as error:
            logger.error(error)


def schedule_github_search(schedule_search, pending_delay):
    query_count = worker_repository.enabled_query_count()
    logger.info("需要处理的关键词总数: {}".format(query_count))
    if query_count:
        logger.info("需要处理的关键词总数: {}".format(query_count))
    else:
        logger.warning("请添加关键词")
        return
    if not worker_repository.has_github_capacity():
        logger.error("请配置github账号")
        return

    task_setting = worker_repository.claim_due_task_schedule(os.getpid(), int(time.time()))
    if not task_setting:
        return

    page = task_setting.get("page")
    if page is None:
        logger.error("请在页面上配置任务参数")
        return
    page = int(page)
    for page_number in range(0, page):
        for query in worker_repository.iter_enabled_queries():
            github_account = worker_repository.choose_github_account()
            if not github_account:
                logger.error("请配置github账号")
                return
            github_username = github_account.get("username")
            rate_remaining = github_account.get("rate_remaining")
            logger.info(github_username)
            logger.info(rate_remaining)
            schedule_search(query, page_number, github_account, pending_delay())
