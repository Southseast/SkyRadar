# SkyRadar 后端设计规范

职责：本文是后端稳定架构、domain 分层、REST API 契约语义和安全边界的主要来源。

职责边界：

- 本文记录“系统应该如何组织”和“最终 REST API 契约语义是什么”。
- 后续路线写入 `PLAN.md`，当前状态和验证写入 `PROGRESS.md`。
- 命令、配置、CI、部署、依赖和 Agent 操作规则写入 `IMPLEMENTATION_GUIDE.md`。
- 测试策略和执行门禁分别写入 `TESTING.md` 与 `CHECKLIST.md`；本文只引用测试要求，不维护完整 checklist。
- 风险登记写入 `RISKS.md`，本文只记录架构边界本身。

当前后端以 FastAPI/ASGI、domain 内聚、OpenAPI 契约、同步 SDK 边界和 compose 拆分拓扑为基线。

本文参考 `PLAN.md` 和 `REFERENCES.md`，吸收 `fastapi/full-stack-fastapi-template` 的工程 harness 观念，以及 `zhanymkanov/fastapi-best-practices` 的 domain 组织和 sync/async 规则。规范优先服务 SkyRadar 当前代码，不照搬完整 DDD/CQRS 模板。

## 设计目标

- 以 `/api/v1/*` 作为最终 RESTful API 形态，使用标准 HTTP 方法、HTTP status 和统一响应结构。
- FastAPI 是主 HTTP 入口；测试 monkeypatch 必须挂到 service、repository 或 integration 边界。
- HTTP 适配、业务流程、数据库访问、外部服务和 worker 调度必须分层。
- Swagger/OpenAPI、契约测试、CI、worker smoke 和部署验证构成同一套后端 harness。
- 敏感字段默认不出 route、schema、日志、文档示例和测试快照。

## 当前边界

```text
server/
  api/<domain>/        # routes、schemas、service、repository、tests
  core/                # config、database、responses、logging
  integrations/        # github、mail、dingtalk、feishu
  workers/             # Huey app、搜索任务、调度任务
  tests/               # 跨域工程 harness
```

当前 domain：

- `docs`：OpenAPI/Swagger 开关和文档服务。
- `health`：API、GitHub 和 MongoDB 健康检查。
- `results`：泄露列表、详情、代码和状态处理。
- `settings`：GitHub、规则、任务、黑名单、通知、SMTP、webhook 设置。
- `statistics`：趋势和统计面板。
- `github_search`：GitHub Code Search、rate limit、资产提取、结果入库。
- `notifications`：邮件和 webhook 通知发送编排。

新增业务优先进入同一 domain 的 routes/schema/service/repository/tests。跨域基础能力进入 `core`，外部服务进入 `integrations`，后台任务入口进入 `workers`。

## 架构维护门禁

架构维护规则必须优先落到 `scripts/backend_architecture_guard.py`，并通过 CI 执行。

不可回退边界：

- 不恢复 `server/api.py`、`server/task.py`、`server/settings.py`、`server/responses.py`、`server/config/database.py`、`server/controllers`、集中式 `server/services` 或集中式 `server/repositories`。
- 不恢复 `server/utils` 泛工具桶、通知旧模块 `server/utils/notice.py`、`server/utils/webhook.py`、`server/utils/dingtalk_message.py`、`server/integrations/webhook.py` 或已废弃的 `server/core/security.py` 薄转发层。
- 后端运行源码不得重新 import Flask、Flask-RESTful、`reqparse`、controller、集中式 service/repository 或旧 Huey task 入口。
- HTTP domain routes 必须导入同域 service；有 `routes.py` 的 domain 必须保留同域 `service.py`、`schemas.py` 和 tests。
- 有 `repository.py` 的 domain 必须有同域 service 作为调用边界。
- Route 和 worker task 不得直接 import repository、integration、`core.database` 或同步外部 SDK；它们必须通过 domain service 编排。
- `async def` route 调同步 service 时必须使用 `run_in_threadpool`。
- Huey supervisor 必须继续使用 `workers.huey`。

如果未来确实需要突破某条规则，必须先在 `DESIGN.md` 或 `DECISIONS.md` 记录原因、替代边界和验证结果，再调整 guard 和测试。

## 分层边界

### Route

职责：

- 绑定 URL、HTTP 方法和 FastAPI 路由。
- 解析 query、body、path 参数。
- 调用 service 执行业务流程。
- 使用统一 response helper 返回 `data/meta/links` 成功结构和 `error/message/detail/request_id` 错误结构。

禁止：

- 直接写复杂 MongoDB 查询或 upsert 流程。
- 直接调用 PyGithub、Requests、smtplib 等外部 SDK。
- 返回原始 `password`、GitHub PAT、SMTP password、webhook token。
- 为了“看起来更合理”偏离 REST response shape。

### Schema

职责：

- 描述请求参数、响应字段、OpenAPI 组件和测试 fixture。
- 在 FastAPI 主线中可使用 Pydantic model，schema 必须表达最终 REST 契约。
- 明确字段脱敏策略。

规则：

- Schema 记录最终 REST 契约。
- OpenAPI 示例必须使用假 token、假邮箱、假 webhook。
- 新增 schema 时同步检查 `docs/api/openapi.yaml` 和契约测试。

### Service

职责：

- 承载业务流程和跨 repository/integration 编排。
- 负责状态转换、结果去重、批量标记、通知触发条件和错误语义。
- 对 route 和 worker 提供可测试函数。

规则：

- Service 不依赖 Flask request、FastAPI Request 或 HTTP response 对象。
- Service 可以接收 repository 和 integration 对象，便于测试隔离。
- Service 返回 domain 数据或应用层结果，由 route 转换为 HTTP response。

### Repository

职责：

- 封装 MongoDB collection 访问、查询条件、排序、分页、upsert、聚合和索引创建。
- 对外提供语义化方法。

规则：

- 新代码必须使用 PyMongo 4 兼容 API；具体允许 API 清单维护在 `IMPLEMENTATION_GUIDE.md`。
- MongoDB 认证由配置层的 `MongoClient` URI 或参数处理。
- 不在 route 或 worker 中新增裸 collection 操作。

### Integration

职责：

- 封装 GitHub、SMTP、DingTalk、Feishu 等外部系统调用。
- 统一超时、错误转换、重试边界、日志脱敏和测试替身。
- 隔离第三方 SDK 版本差异。

规则：

- GitHub integration 不向上层暴露原始 token/password。
- Requests 调 DingTalk/Feishu webhook 必须设置合理超时。
- SMTP password 只能用于发送流程，不进入 response、OpenAPI 示例、日志或测试快照。
- 通知通道按 provider 命名为 `integrations/mail.py`、`integrations/dingtalk.py`、`integrations/feishu.py`；不要新增 `notice.py`、`webhook.py` 这类泛名模块。
- provider integration 负责各自外部通道的 validate、mask、sign 和 post 边界，例如 `send_smtp_notice()`、`prepare_dingtalk_webhook_url()`、`post_dingtalk_webhook()`、`post_feishu_webhook()`；不要恢复旧的 `post_dingtalk_markdown()` 或 `post_feishu_text()`。
- 通知消息 payload builder 位于 `api.notifications.messages`，例如 `build_dingtalk_search_notice_payload()`、`build_feishu_search_notice_payload()`、`build_dingtalk_test_payload()`、`build_feishu_test_payload()`；不要把 `build_*_search_notice_payload()` 归入 provider integration 职责。
- `api/notifications` 负责通知业务编排和选择 message builder，不直接构造 provider 签名、HTTP 请求或 SMTP message。
- 内部函数命名采用动宾结构并保留领域上下文，例如 `search_github_code()`、`schedule_github_search()`、`send_webhook_notice()`；避免 `check()`、`new_github()`、`webhook_notice()`、`send_mail()` 这类泛名。
- 基础设施能力进入 `core`，外部系统能力进入 `integrations`，不要用 `utils` 作为无法归属代码的默认位置。

### Worker

职责：

- 只负责 Huey app、任务注册、调度入口和任务参数反序列化。
- 调用 service 完成 GitHub 搜索、rate limit 更新、通知发送和任务状态更新。
- 提供 worker smoke 可验证的最小任务。

禁止：

- 在 Huey task 中堆叠大段 MongoDB、GitHub SDK、邮件和 webhook 逻辑。
- 在 worker import 阶段执行不可控外部请求。
- 让 worker 的任务调度变更隐式改变 API 契约。

## FastAPI 架构规则

- 保持 `api:app` ASGI 入口。
- Gunicorn 使用 Uvicorn worker 运行 ASGI app。
- `/api/v1/openapi.json` 和 `/api/v1/docs` 继续由受控开关启用，生产默认关闭。
- `docs/api/openapi.yaml` 是机器可读契约源，不直接用 FastAPI 自动 OpenAPI 覆盖。
- 如果某个端点为了满足 REST 契约需要绕开 FastAPI/Pydantic 默认行为，必须记录在本文的 API 契约语义、`docs/api/openapi.yaml` 和对应测试中。

## RESTful API 设计规范

当前 API 以 `/api/v1/*` 为最终 RESTful 契约。OpenAPI、文档入口、健康检查、契约测试和部署 healthcheck 都应围绕 v1 路径维护。

### 资源和 URL

- URL 表达资源，不表达动作；资源名使用小写复数名词，必要时使用连字符。
- 示例：`/api/v1/leakages`、`/api/v1/search-rules`、`/api/v1/webhooks`。
- 禁止新增 `get*`、`create*`、`delete*`、`test*` 这类动词型路径。
- 单资源使用资源 ID 表达：`/api/v1/leakages/{leakage_id}`。
- 避免深层嵌套；跨资源筛选优先放 query，例如 `/api/v1/leakages?tag=github-token`。
- 外部系统 provider 用字段表达，不用新增 provider 专用路径，例如 `provider=dingtalk`。
- 与结果处理、通知测试这类非 CRUD 行为相关的动作，优先建模为子资源或任务资源；如果确实必须用动作名，必须在 `DECISIONS.md` 记录原因。

### HTTP 方法

- `GET` 读取集合或单个资源，不产生业务写入。
- `POST` 创建资源，或创建异步任务、测试发送任务等动作资源。
- `PUT` 全量替换资源；没有全量替换语义时不要为了凑方法使用 `PUT`。
- `PATCH` 局部更新资源。
- `DELETE` 删除资源；幂等删除语义必须在 OpenAPI 中说明。
- 不新增 `X-HTTP-Method-Override`，除非明确支持受限客户端并同步测试。

### 查询参数

- 搜索、筛选、排序和分页统一放在 query string。
- 常用字段：
  - `search`：文本搜索。
  - `sort`：排序字段。
  - `order`：`asc` 或 `desc`。
  - `page`：页码，从 1 开始。
  - `page_size`：每页数量，必须有服务端上限。
- 过滤字段使用资源字段名，例如 `tag`、`language`、`status`、`provider`。
- RESTful API 不接受 JSON 字符串 query 作为筛选条件；复杂筛选应设计为明确 query 字段或 POST 到搜索任务资源。

### HTTP 状态码

- RESTful API 必须让 HTTP status 反映结果：
  - `200 OK`：读取、更新或同步动作成功。
  - `201 Created`：资源创建成功。
  - `202 Accepted`：异步任务已接受。
  - `204 No Content`：删除成功且无需返回 body。
  - `400 Bad Request`：请求格式或参数无法处理。
  - `401 Unauthorized`：未认证。
  - `403 Forbidden`：已认证但无权限。
  - `404 Not Found`：资源不存在。
  - `409 Conflict`：状态冲突。
  - `422 Unprocessable Entity`：语义校验失败。
  - `429 Too Many Requests`：限流。
  - `500 Internal Server Error`：未预期服务端错误。
  - `503 Service Unavailable`：依赖服务不可用或系统暂不可用。
- 禁止用 HTTP 200 表示业务失败。

### 响应体

- API response 默认为 JSON；除 Swagger UI HTML 外，不返回纯文本业务响应。
- 成功响应使用 HTTP status 表达状态，body 使用以下结构：

```json
{
  "data": {},
  "meta": {},
  "links": {}
}
```

- `data` 承载资源或资源数组；没有 body 的成功删除使用 HTTP 204。
- `meta` 承载分页、统计、生成时间等非资源数据。
- `links` 可选，承载 `self`、`next`、`prev`、`related` 等链接；不强制实现 HATEOAS，但分页和异步任务建议提供。
- 列表分页示例：

```json
{
  "data": [],
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 0
  },
  "links": {
    "self": "/api/v1/leakages?page=1&page_size=20"
  }
}
```

### 错误体

- 错误响应使用统一 JSON 结构：

```json
{
  "error": "invalid_request",
  "message": "请求参数无效",
  "detail": {},
  "request_id": "optional-request-id"
}
```

- `error` 使用稳定机器码，采用小写 snake_case。
- `message` 面向用户或调用方，不能包含 secret、完整 token、完整 webhook URL 或泄露代码。
- `detail` 可包含字段级错误，不得回显敏感 payload。
- `request_id` 可选；如果后续加入链路追踪，必须贯穿日志和响应。

### 版本控制和迁移

- 当前最终版本路径使用 `/api/v1/*`；后续不兼容修改进入 `/api/v2/*`。
- 新版本迁移必须同时提供 OpenAPI 契约、contract tests、前端 adapter 迁移计划、发布切换和回滚策略。

### OpenAPI 和测试

- 每个新增 RESTful operation 必须有唯一 `operationId`，命名使用动作 + 资源，例如 `listLeakages`、`createWebhook`。
- `docs/api/openapi.yaml` 必须记录 HTTP status、请求体、响应体、错误体和分页字段。
- OpenAPI 示例不得包含真实 GitHub PAT、SMTP password、webhook token、MongoDB URI、Redis secret、内网地址或生产域名。
- RESTful API 必须补 FastAPI TestClient contract tests，至少覆盖：
  - 成功 HTTP status。
  - 错误 HTTP status 和错误体。
  - JSON key 顺序和分页 `meta`。
  - 敏感字段脱敏。
  - OpenAPI route coverage。
- 涉及前端的 API 变化必须同步 `client/src/lib/api/*` adapter 和 `docs/frontend/IMPLEMENTATION_GUIDE.md`。

## API 契约语义

`docs/api/openapi.yaml` 是路径、参数、request body、response schema 和 examples 的机器可读源；本文记录 `/api/v1/*` 的人工可读契约语义和高风险行为。

通用规则：

- 所有业务路径使用 `/api/v1/*`。
- 成功响应使用 `data/meta/links`；删除成功且无需返回资源时使用 HTTP 204 且无 body。
- 错误响应使用 `error/message/detail/request_id`，HTTP status 必须与错误语义一致。
- 写接口默认接收 `application/json`，表单请求不属于 REST 契约要求。
- 当前 API 无应用级鉴权；启用 nginx Basic Auth 时，鉴权发生在反向代理层，不改变 FastAPI 业务契约。
- Swagger 示例、测试快照和日志不能包含真实 GitHub PAT、SMTP password、webhook token、MongoDB URI secret 或 Redis secret。

机器契约范围：

- `docs/api/openapi.yaml` 必须覆盖 `/api/v1/health`、`/api/v1/docs`、`/api/v1/openapi.json`、结果、统计和全部设置资源。
- 路径范围由 `scripts/backend_route_coverage.py` 校验：默认拒绝非 `/api/v1/*` OpenAPI path；未来 v1 runtime route 落地后可启用注册路由覆盖检查。
- 修改任一 `/api/v1/*` 行为时，必须同步 `docs/api/openapi.yaml`、FastAPI TestClient contract tests、前端 API adapter 和本文契约语义。

核心资源：

- `GET /api/v1/leakages` 使用显式 query 字段过滤、排序和分页，禁止透传 Mongo 查询操作符。
- `GET /api/v1/leakages/{leakage_id}` 返回泄露详情元信息，不包含代码正文。
- `PATCH /api/v1/leakages/{leakage_id}` 更新 `security`、`ignored`、`desc` 和可选同项目结果。
- `GET /api/v1/leakages/{leakage_id}/code` 返回 base64 编码代码和受影响资产；代码内容不得进入普通日志、OpenAPI 示例或测试快照。
- `GET /api/v1/trends` 返回仪表盘统计和扫描任务运行信息。
- `GET /api/v1/statistics` 使用 `group_by` 明确聚合维度，当前维度为 `tag` 或 `language`。

设置资源：

- GitHub 账号使用 `/api/v1/github-accounts` 和 `/api/v1/github-accounts/{username}`；响应不得包含原始 token。
- 查询规则使用 `/api/v1/search-rules` 和 `/api/v1/search-rules/{tag}`。
- 任务调度使用 `/api/v1/task-schedules/current`。
- 黑名单使用 `/api/v1/blacklist-items` 和 `/api/v1/blacklist-items/{text}`。
- 邮件通知接收人使用 `/api/v1/notification-recipients` 和 `/api/v1/notification-recipients/{mail}`。
- SMTP 配置使用 `/api/v1/mail-settings/current`；响应不得包含 SMTP password。
- Webhook 配置使用 `/api/v1/webhooks` 和 `/api/v1/webhooks/{webhook_id}`；响应只返回脱敏 URL、稳定 ID 和 `has_secret`。
- Webhook 测试建模为任务资源 `POST /api/v1/webhook-tests`，成功接受使用 HTTP 202。

API 文档入口：

- `GET /api/v1/openapi.json`、`GET /api/v1/docs` 和未来 `GET /api/v1/redoc` 生产默认关闭。
- 关闭时返回 HTTP 404，body 使用统一错误结构。
- Swagger UI 会读取 `/api/v1/openapi.json`。
- 文档入口暴露 API 路径、参数和响应结构，生产环境必须放在认证代理、VPN、内网或应用鉴权之后。

健康检查：

- `GET /api/v1/health` 使用标准成功响应结构。
- `data.api`、`data.github`、`data.mongodb` 和 `data.redis` 统一使用 `{ ok, message, latency_ms }`。
- HTTP 200 代表健康检查请求成功；依赖不可用时可以返回 HTTP 503 和统一错误体。
- MongoDB 检查使用 `db.command("ping")`。

## Sync 和 Async 规则

当前主要 I/O 都是同步 SDK：PyMongo、PyGithub、Requests、smtplib、Huey、Redis。

- 同步 PyMongo、PyGithub、Requests、smtplib 调用不得直接放入 FastAPI `async def`。
- FastAPI route 中，只要调用同步 service 或同步 SDK，route 默认写成普通 `def`。
- 如果必须在 `async def` route 中读取 JSON 或 form body，同步 service 调用必须显式使用受控线程池。
- 只有当调用链全部使用可 `await` 的异步客户端，并且测试覆盖并发和超时行为时，才使用 `async def`。
- 不为了“FastAPI 就要 async”重写业务逻辑。

## 敏感字段边界

敏感字段包括但不限于：

- GitHub username 和 PAT/token。
- SMTP password。
- webhook token、完整 webhook URL 中的签名参数。
- MongoDB URI 中的用户名和密码。
- Redis 密码或未来 Redis ACL secret。
- 泄露代码内容、受影响资产和内部项目标识。

规则：

- 数据库可以存储业务必需 secret，但返回给 route 前必须提供 public view 或脱敏方法。
- API response 不得包含原始 `password`、`token`、`secret`、完整 webhook 签名。
- OpenAPI schema、Swagger 示例、README、测试 fixture 和日志不得包含真实 secret。
- OpenAPI 示例和描述文本必须由 `scripts/backend_openapi_secret_scan.py` 扫描。
- 日志记录外部请求失败时，只记录平台、脱敏 URL、状态码和错误摘要。

## 与测试和门禁的关系

- 测试分层、覆盖范围和外部依赖策略维护在 `TESTING.md`。
- 切片完成和发布前逐项检查维护在 `CHECKLIST.md`。
- 标准命令、CI 触发、部署 smoke 和 Agent 执行规则维护在 `IMPLEMENTATION_GUIDE.md`。
