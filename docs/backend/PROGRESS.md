# 后端 Harness 进度

职责：本文只记录当前有效状态、已完成事项、下一步、阻塞项、待补验证和最近真实验证。

职责边界：

- 后续路线写入 `PLAN.md`，本文只引用下一步，不展开路线设计。
- 架构、domain 边界和 API 契约语义写入 `DESIGN.md`，本文不复制规范全文。
- 命令模板、配置、CI 和部署规则写入 `IMPLEMENTATION_GUIDE.md`，本文只记录已经运行的命令结果。
- 测试策略和门禁分别写入 `TESTING.md` 与 `CHECKLIST.md`，本文只记录验证状态。
- 未运行事项必须写为“待补”或“未运行”，不能写成通过。

## 当前状态

- HTTP 入口为 FastAPI/ASGI，`api:app` 由 `server/api/__init__.py` 暴露。
- 部署入口为 Gunicorn 26 + Uvicorn worker，API service 监听 `0.0.0.0:8888`。
- 运行时目标为 Python 3.13；主要依赖为 PyMongo 4、Redis client 8、Huey 2、PyGithub 2、Requests 2。
- compose 默认拓扑为 `skyradar`、`nginx`、`worker`、`redis` 和 `mongo`。
- compose 默认通过 named volume 持久化 nginx/all-in-one Basic Auth 自动生成凭据，重新 build 或重建容器后登录凭据保持不变。
- 泄露结果新增 SkyRadar 发现时间字段 `discovered_at`/`discovered_timestamp`；列表排序和今日统计使用发现时间，`datetime` 仅表示 GitHub 侧更新时间。
- OpenAPI 契约源为 `docs/api/openapi.yaml`；契约已收敛到最终 `/api/v1/*` RESTful 形态；`GET /api/v1/openapi.json` 和 `GET /api/v1/docs` 默认关闭，`SKYRADAR_API_DOCS_ENABLED=true` 时启用。
- 业务代码已按 domain/core/integrations/workers 边界组织，测试目录已按 domain/core/workers/harness 边界内聚。
- 任务调度 minute 语义已在后端文档中收敛为 Huey 固定 tick + MongoDB `minute/next_due_at` 控制实际周期；`PUT /api/v1/task-schedules/current` 后新周期不依赖 SIGHUP 动态改 crontab。
- 查询规则支持 `code` 和 `repositories` 两类 GitHub 检索，旧规则缺省按 `code` 兼容。
- 资产提取规则支持通过设置 API 自定义；未配置时使用预置 domain、email 和 ip 正则规则，删除预置规则后会持久隐藏并退出扫描。
- OpenAI 泄露简析已落地：全局设置支持 DB 保存和环境变量兜底，查询规则可独立开启自动分析，扫描保存结果后异步投递 Huey 任务，分析结果只写入 `ai_analysis` 附加状态；可开启 `有用才推送 webhook`，由 AI 判断项目有用后再推送 webhook。

## 已完成

- FastAPI/ASGI 主入口、domain 分层、统一 response helper、统一配置边界和 PyMongo 4 兼容已落地。
- GitHub、SMTP、DingTalk webhook 和 Feishu webhook 调用已放入 provider 命名的 integration 边界，设置接口敏感字段脱敏已落地。
- Webhook 设置最终契约为 `/api/v1/webhooks`、`/api/v1/webhooks/{webhook_id}` 和 `/api/v1/webhook-tests`；响应使用脱敏 URL、稳定 ID 和 `has_secret`。
- `server/utils` 泛工具桶已清空；日志、MongoDB、通知和哈希逻辑分别收敛到 `core`、`integrations` 或直接标准库调用。
- nginx Basic Auth 已作为默认启用的部署层访问保护落地。
- Web、Worker、nginx、Redis、MongoDB 已在 compose 中拆分。
- OpenAPI check、route coverage、secret scan、architecture guard、HTTP smoke、worker smoke、Schemathesis smoke、MongoDB smoke、Redis/Huey smoke、compose smoke 和 GitHub/PAT smoke 脚本已落地。
- GitHub Actions `backend` workflow 已接入本地同等验证命令。
- 后端设计、实现指南、测试策略、门禁和风险登记已记录任务调度 minute 修复的文档语义：固定 tick、PUT 后尽快生效、原子 claim、防重复 enqueue 和 `next_due_at` 推进。
- OpenAI 分析 service、settings API、results 重新分析接口、worker 任务和 OpenAPI 契约已补测试；OpenAI API Key GET 响应只暴露 `has_api_key` 和 `mask_api_key`；AI 有用性判断使用可编辑的 prompt/interest 文本并输出 `is_useful`、`usefulness_reason` 和 `matched_interests`。

## 下一步

- 回填最新远端 GitHub Actions `backend` 运行结果。
- 按 `PLAN.md` 继续推进 GitHub Code Search 加固和 baseline/误报治理。
- 继续维护 domain 边界和 architecture guard。
- 如需要更强访问控制，再单独设计应用层用户、审计和权限。

## 阻塞项

- 当前无文档设计阻塞。

## 已知待补验证

- 最新未提交变更推送后，需要回填远端 GitHub Actions 结果。
- Compose 已为 MongoDB 和 Redis 配置 named volume 持久化；保留数据升级、备份和恢复仍需在目标环境发布前单独验证。
- 真实 OpenAI API 调用、模型质量和目标环境超时/并发表现本轮未运行，待目标环境凭据复验。

## 最近验证

- `PYTHONPATH=server pytest -q` 通过，154 passed。
- `PYTHONPATH=server pytest -q server/api/ai_analysis/tests/test_ai_analysis_service.py server/api/github_search/tests/test_worker_service.py server/api/settings/tests/test_settings_contract.py server/workers/tests/test_analysis_tasks.py server/tests/test_openapi_contract.py` 通过，51 passed。
- `PYTHONPATH=server python scripts/backend_worker_smoke.py --json` 通过，覆盖 `workers.analysis_tasks.analyze_leakage`、搜索任务和周期任务注册。
- `PYTHONPATH=server python scripts/backend_openapi_check.py` 通过，覆盖 25 paths、37 operations。
- `PYTHONPATH=server python scripts/backend_route_coverage.py` 通过，25 final `/api/v1` paths。
- `PYTHONPATH=server python scripts/backend_architecture_guard.py` 通过。
- 2026-06-15 任务调度 minute 修复已验证：后端 pytest 131 passed，worker smoke、architecture guard、OpenAPI check 和 compose smoke 单测通过。
- `python3 -m compileall -q scripts server` 通过。
- `git diff --check` 通过。
- `NPM_CONFIG_REGISTRY=https://registry.npmjs.org python3 scripts/backend_compose_smoke.py --project-name skyradar-real-smoke --http-port 18081 --fresh-volumes --json` 通过，覆盖 build/up、MongoDB 8.2.7 ping/CRUD、Redis ping、API service 进程边界、`/api/v1/health`、静态首页、nginx 配置、worker 任务消费和日志 failure/secret scan。
- `NPM_CONFIG_REGISTRY=https://registry.npmjs.org python3 scripts/backend_compose_smoke.py --project-name skyradar-real-smoke --http-port 18081 --fresh-volumes --no-build --keep-running --json` 通过，并用于后续浏览器 smoke。
- `docker compose -f compose.yml -p skyradar-real-smoke down -v --remove-orphans` 已清理真实 smoke 栈和临时 volume。
- 真实 GitHub/PAT 和真实 webhook 外部投递链路本轮未运行，待目标环境凭据复验。
