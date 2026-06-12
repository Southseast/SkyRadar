# 后端架构决策记录

职责：本文只保留当前有效的长期技术决策，也就是 ADR。

职责边界：

- 本文记录“为什么选择某个方向”和该选择的长期影响。
- 具体架构规范写入 `DESIGN.md`，命令、配置和 CI 写入 `IMPLEMENTATION_GUIDE.md`。
- 当前状态、已完成事项和验证结果写入 `PROGRESS.md`。
- 风险、缓解和剩余缺口写入 `RISKS.md`。
- 已被当前架构取代的过渡决策不继续保留在本文。

状态取值：

- `Proposed`：已提出，尚未执行。
- `Accepted`：当前有效决策。

## ADR-0001：Python 目标版本选择 3.13

状态：Accepted

背景：

后端需要一个仍处于官方支持周期、依赖生态稳定、基础镜像可获得的运行时版本。Python 3.13 在维护窗口和第三方依赖支持之间更适合作为当前项目默认目标。

决策：

后端目标版本为 Python 3.13。CI、本地 uv 命令、Docker 基础镜像和依赖验证都以 Python 3.13 为准。

影响：

- Docker 基础镜像优先使用 `python:3.13-slim-trixie` 或等价团队镜像。
- `pyproject.toml`、`uv.lock` 和后端验证命令保持 Python 3.13 一致。
- 如果未来降级到 Python 3.12 或升级到 Python 3.14，需要新增 ADR 说明原因、验证范围和退出条件。

## ADR-0002：OpenAPI YAML 是机器可读契约源

状态：Accepted

背景：

SkyRadar 的 `/api/*` 存在当前前端依赖的兼容行为，例如 body `status` 与 HTTP status 分离、部分删除接口使用兼容 body、`/api/leakage` 的 `status` 查询参数使用 JSON 字符串。FastAPI 自动 schema 不能未经审查直接代表这些兼容语义。

决策：

`docs/api/openapi.yaml` 是当前机器可读契约源。Swagger UI、OpenAPI JSON、契约测试、route coverage 和前后端协作都围绕该文件对齐。FastAPI 自动 OpenAPI 不直接覆盖该文件。

影响：

- API 行为变化必须同步更新 `DESIGN.md` 的兼容语义和 `docs/api/openapi.yaml`。
- OpenAPI 示例必须脱敏。
- `scripts/backend_openapi_check.py` 和 `scripts/backend_route_coverage.py` 作为必跑门禁。

## ADR-0003：FastAPI/ASGI 是主 HTTP 入口

状态：Accepted

背景：

当前后端需要类型化 route、OpenAPI/Swagger 协作能力、现代 ASGI 部署入口和更清晰的参数声明。业务 I/O 仍以同步 SDK 为主，因此框架切换不以盲目 async 化为目标。

决策：

主 HTTP 入口为 FastAPI ASGI app：`api:app` 由 `server/api/__init__.py` 暴露。生产由 Gunicorn 使用 `uvicorn.workers.UvicornWorker` 运行，nginx 反向代理 `/api` 到 API service。

影响：

- 不恢复 Flask、Flask-RESTful、`reqparse`、controller 兼容层或单文件 `server/api.py`。
- HTTP route 拆到 `server/api/<domain>/routes.py`。
- `docs/api/openapi.yaml` 仍是人工审查后的契约源。
- 部署入口保持 `gunicorn ... -k uvicorn.workers.UvicornWorker api:app`。

## ADR-0004：同步 SDK 保持同步边界或受控线程池

状态：Accepted

背景：

当前后端主要 I/O 依赖 PyMongo、PyGithub、Requests、smtplib、Huey 和 Redis 同步客户端。同步 SDK 直接放入 `async def` route 会阻塞事件循环，并让性能问题更隐蔽。

决策：

调用链包含同步 SDK 或同步 service 时，route 默认使用普通 `def`。必须读取 request body 且只能使用 `async def` 的 route，需要通过 `fastapi.concurrency.run_in_threadpool` 调用同步 service。

影响：

- FastAPI 代码不以 `async def` 数量作为质量指标。
- 同步 GitHub、MongoDB、SMTP、webhook、Redis 和 Huey 调用必须保持在同步 route 或受控线程池边界内。
- 如果未来引入 async MongoDB、async HTTP client 或 async mail client，需要新增 ADR 说明迁移边界。

## ADR-0005：API 文档入口生产默认关闭

状态：Accepted

背景：

Swagger UI、OpenAPI JSON 和接口示例会暴露 endpoint、参数、错误行为和部分业务语义。当前项目默认不引入应用级登录态，因此文档入口必须受控。

决策：

`/api/docs`、`/api/redoc` 和 `/api/openapi.json` 生产默认关闭。仅当 `SKYRADAR_API_DOCS_ENABLED=true` 时启用，并且应部署在内网、VPN、认证代理或本地开发环境之后。

影响：

- 默认未启用时这些路径返回 404。
- 启用时仍必须使用脱敏示例。
- 测试需要覆盖默认关闭和显式启用两种情况。

## ADR-0006：Domain 内聚是后端默认组织方式

状态：Accepted

背景：

集中式 service/repository 目录会让 API、worker、测试和业务领域之间的归属变得含混。当前项目规模适合按 domain 收拢 route、schema、service、repository 和 tests。

决策：

HTTP domain 放在 `server/api/<domain>/` 下。`docs`、`health`、`results`、`settings`、`statistics`、`github_search` 和 `notifications` 均按 domain 组织生产代码和测试。跨域基础能力放入 `server/core/`；外部服务适配放入 `server/integrations/`；Huey app 和任务注册放入 `server/workers/`。

影响：

- Route 只做 HTTP 参数解析和 response 适配。
- Service 承载业务流程。
- Repository 封装 MongoDB 访问。
- Integration 封装外部服务。
- Worker 只负责任务注册和参数反序列化，业务调用 domain service。
- 架构 guard 负责防止恢复集中式业务目录或 route/worker 直连 repository/integration/database。

## ADR-0007：PyMongo 4 兼容采用显式 API

状态：Accepted

背景：

PyMongo 4 移除了多项不兼容 API。用 shim 隐藏差异会让后续 MongoDB 8.x 行为更难定位。

决策：

使用显式 PyMongo 4 API，不通过 collection shim 隐藏兼容差异。具体允许 API 清单维护在 `IMPLEMENTATION_GUIDE.md`；健康检查使用 `ping`。

影响：

- 新代码不得新增 `collection.count()`、`collection.save()`、`collection.update()`、`db.authenticate()` 或 `db.last_status()`。
- MongoDB 查询、分页、upsert、replace、聚合和删除继续放在 repository/helper 层。
- MongoDB 8 smoke 和契约测试作为防回归验证。

## ADR-0008：nginx Basic Auth 作为当前访问保护

状态：Accepted

背景：

SkyRadar 当前主要是单人或小范围部署工具，访问面由 nginx 暴露。当前安全目标是避免未授权访问页面、设置接口、规则和结果数据，而不是建设多用户、SSO、RBAC 或应用内会话体系。

决策：

短期采用 nginx Basic Auth 作为统一访问保护。通过同时配置 `SKYRADAR_BASIC_AUTH_USERNAME` 和 `SKYRADAR_BASIC_AUTH_PASSWORD` 启用；未配置时保持本地开发兼容。Basic Auth 覆盖前端页面、静态资源和 `/api` 反向代理入口，不新增 `/api/auth/*`。

影响：

- 不引入用户表、服务端 session、登录页或前端登录态。
- 未通过 Basic Auth 的请求由 nginx 返回 HTTP `401`，不会进入 FastAPI。
- 只配置用户名或只配置密码时容器启动失败。
- Basic Auth 必须配合 HTTPS、VPN、内网或可信反向代理使用。
- 如果未来需要多用户、审计、权限或公网长期暴露，再新增应用层用户体系 ADR。

## ADR-0009：compose 默认使用拆分拓扑

状态：Accepted

背景：

API、nginx、worker、Redis 和 MongoDB 有不同生命周期和健康检查方式。拆分 service 能让真实请求、worker 消费、静态资源和数据服务各自被 smoke 验证。

决策：

compose 默认拓扑为 `skyradar`、`nginx`、`worker`、`redis` 和 `mongo`。`skyradar` 只运行 FastAPI/Gunicorn；`nginx` 服务静态资源和 `/api` 反代；`worker` 运行 Huey consumer；`redis` 和 `mongo` 独立提供数据服务。`skyradar-all-in-one` profile 只作为短期回退/兼容拓扑保留。

影响：

- CI 和发布 smoke 默认验证拆分拓扑。
- `nginx` 默认 upstream 为 `skyradar:8888`。
- Web 和 Worker 共享同一组业务配置来源。
- compose smoke 标准覆盖项以 `IMPLEMENTATION_GUIDE.md` 为准。
