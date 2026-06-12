# 后端 Harness 进度

更新时间：2026-06-12

职责：本文只记录当前有效状态、已完成事项、下一步、阻塞项、待补验证和最近真实验证。

职责边界：

- 后续路线写入 `PLAN.md`，本文只引用下一步，不展开路线设计。
- 架构、domain 边界和 API 兼容语义写入 `DESIGN.md`，本文不复制规范全文。
- 命令模板、配置、CI 和部署规则写入 `IMPLEMENTATION_GUIDE.md`，本文只记录已经运行的命令结果。
- 测试策略和门禁分别写入 `TESTING.md` 与 `CHECKLIST.md`，本文只记录验证状态。
- 未运行事项必须写为“待补”或“未运行”，不能写成通过。

## 当前状态

- HTTP 入口为 FastAPI/ASGI，`api:app` 由 `server/api/__init__.py` 暴露。
- 部署入口为 Gunicorn 26 + Uvicorn worker，API service 监听 `0.0.0.0:8888`。
- 运行时目标为 Python 3.13；主要依赖为 PyMongo 4、Redis client 8、Huey 2、PyGithub 2、Requests 2。
- compose 默认拓扑为 `skyradar`、`nginx`、`worker`、`redis` 和 `mongo`。
- OpenAPI 契约源为 `docs/api/openapi.yaml`；`GET /api/openapi.json` 和 `GET /api/docs` 默认关闭，`SKYRADAR_API_DOCS_ENABLED=true` 时启用。
- 业务代码已按 domain/core/integrations/workers 边界组织，测试目录已按 domain/core/workers/harness 边界内聚。

## 已完成

- FastAPI/ASGI 主入口、domain 分层、统一 response helper、统一配置边界和 PyMongo 4 兼容已落地。
- GitHub、SMTP、DingTalk webhook 和 Feishu webhook 调用已放入 provider 命名的 integration 边界，设置接口敏感字段脱敏已落地。
- Webhook 设置外部契约已收敛到 `/api/setting/webhook`、`provider`、`webhook_url` 和 `webhook_hash`；新存储记录必须包含 `provider`，不兼容缺少 `provider` 的旧 Mongo 数据。
- `server/utils` 泛工具桶已清空；日志、MongoDB、通知和哈希逻辑分别收敛到 `core`、`integrations` 或直接标准库调用。
- nginx Basic Auth 已作为部署层访问保护落地。
- Web、Worker、nginx、Redis、MongoDB 已在 compose 中拆分。
- OpenAPI check、route coverage、secret scan、architecture guard、HTTP smoke、worker smoke、Schemathesis smoke、MongoDB smoke、Redis/Huey smoke、compose smoke 和 GitHub/PAT smoke 脚本已落地。
- GitHub Actions `backend` workflow 已接入本地同等验证命令。

## 下一步

- 回填最新远端 GitHub Actions `backend` 运行结果。
- 按 `PLAN.md` 推进 GitHub Code Search 加固和 baseline/误报治理。
- 继续维护 domain 边界和 architecture guard。
- 如需要更强访问控制，再单独设计应用层用户、审计和权限。

## 阻塞项

- 当前无文档设计阻塞。

## 已知待补验证

- 最新未提交变更推送后，需要回填远端 GitHub Actions 结果。
- 保留数据升级验证不纳入当前范围；当前 compose 结论按可丢数据 fresh volume 场景成立。

## 最近验证

- `python3 -m compileall -q scripts server` 通过。
- `python3 -m pytest server/api/settings/tests server/tests/test_openapi_contract.py server/tests/test_openapi_secret_scan.py` 通过，35 passed。
- `python3 -m pytest` 通过，109 passed。
- `python3 scripts/backend_openapi_check.py` 通过，覆盖 15 paths、28 operations。
- `python3 scripts/backend_route_coverage.py` 通过，15 个 `/api` route 全覆盖。
- `python3 scripts/backend_openapi_secret_scan.py` 通过，0 findings。
- `python3 scripts/backend_architecture_guard.py` 通过。
- `python3 scripts/backend_worker_smoke.py --json` 通过。
- `cd client && npm run lint` 通过。
- `cd client && npm run test` 通过，10 个 test files、23 tests。
- `cd client && npm run build` 通过。
- `git diff --check` 通过。
