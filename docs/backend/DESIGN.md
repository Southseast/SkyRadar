# SkyRadar 后端设计规范

职责：本文是后端稳定架构、domain 分层、API 人工兼容语义和安全边界的主要来源。

职责边界：

- 本文记录“系统应该如何组织”和“历史 API 兼容语义是什么”。
- 后续路线写入 `PLAN.md`，当前状态和验证写入 `PROGRESS.md`。
- 命令、配置、CI、部署、依赖和 Agent 操作规则写入 `IMPLEMENTATION_GUIDE.md`。
- 测试策略和执行门禁分别写入 `TESTING.md` 与 `CHECKLIST.md`；本文只引用测试要求，不维护完整 checklist。
- 风险登记写入 `RISKS.md`，本文只记录架构边界本身。

当前后端以 FastAPI/ASGI、domain 内聚、OpenAPI 契约、同步 SDK 边界和 compose 拆分拓扑为基线。

本文参考 `PLAN.md` 和 `REFERENCES.md`，吸收 `fastapi/full-stack-fastapi-template` 的工程 harness 观念，以及 `zhanymkanov/fastapi-best-practices` 的 domain 组织和 sync/async 规则。规范优先服务 SkyRadar 当前代码，不照搬完整 DDD/CQRS 模板。

## 设计目标

- 保持 `/api/*` 路径、参数、HTTP 方法和 response body 兼容，直到显式版本化。
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
- 使用统一 response helper 返回兼容 `status/msg/result/total` 结构。

禁止：

- 直接写复杂 MongoDB 查询或 upsert 流程。
- 直接调用 PyGithub、Requests、smtplib 等外部 SDK。
- 返回原始 `password`、GitHub PAT、SMTP password、webhook token。
- 为了“看起来更合理”修改兼容 response shape。

### Schema

职责：

- 描述请求参数、响应字段、OpenAPI 组件和测试 fixture。
- 在 FastAPI 主线中可使用 Pydantic model，但不得为了类型化修正兼容协议。
- 明确字段脱敏策略。

规则：

- Schema 记录当前真实契约。
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
- `/api/openapi.json` 和 `/api/docs` 继续由受控开关启用，生产默认关闭。
- `docs/api/openapi.yaml` 是机器可读契约源，不直接用 FastAPI 自动 OpenAPI 覆盖。
- 如果某个端点为了保持兼容契约需要绕开 FastAPI/Pydantic 默认行为，必须记录在本文的 API 兼容语义、`docs/api/openapi.yaml` 和对应测试中。

## API 兼容语义

`docs/api/openapi.yaml` 是路径、参数、request body、response schema 和 examples 的机器可读源；本文记录 `/api/*` 的人工可读兼容语义和高风险行为。

通用规则：

- 除 `/api/health` 外，大多数业务接口返回 `status/msg/result` body；`GET /api/leakage` 额外返回 `total`。
- HTTP status 通常为 200；body 内的 `status` 是业务兼容字段，不等同于 HTTP status code。
- 多个创建或保存接口成功时 body `status=201`，HTTP status 仍可能为 200。
- 多个 DELETE 接口成功时 body `status=404`，这是兼容成功语义，不得误改为 HTTP 404。
- 写接口必须兼容 `application/json` 和 `application/x-www-form-urlencoded`。
- 当前 API 无应用级鉴权；启用 nginx Basic Auth 时，鉴权发生在反向代理层，不改变 FastAPI 业务契约。
- Swagger 示例、测试快照和日志不能包含真实 GitHub PAT、SMTP password、webhook token、MongoDB URI secret 或 Redis secret。

机器契约范围：

- `docs/api/openapi.yaml` 必须覆盖健康检查、文档入口、结果、统计和全部 setting API。
- 路由覆盖由 `scripts/backend_route_coverage.py` 校验。
- 修改任一 `/api/*` 行为时，必须同步 `docs/api/openapi.yaml`、FastAPI TestClient contract tests、前端 API adapter 和本文兼容语义。

高风险端点：

- `GET /api/leakage` 的 `status` query 是必传 JSON 字符串，例如 `{"security":0,"ignore":0}`；缺失时当前 FastAPI 参数校验返回 HTTP 422，非 JSON 字符串仍可能触发 service 层 500。
- `GET /api/leakage` 的 `status` 当前允许携带 Mongo 查询操作符，这是兼容协议，也是输入校验风险；列表查询排除 `code` 和 `affect` 字段。
- `PATCH /api/leakage` 按 `_id` 更新单条结果；当 `security=0, ignore=0` 或 `security=1, ignore=1` 时，会批量更新同 `project` 的结果；成功 body 使用 `status=201`、`msg=处理成功`、`result=[]`。
- `GET /api/leakage/info` 返回单条结果元信息，排除 `code` 字段，当前也排除 `_id`。
- `GET /api/leakage/code` 返回 base64 编码 `code` 和历史扫描数据中的 `affect`；代码内容不得进入普通日志、OpenAPI 示例或测试快照。
- `GET /api/trend` 返回仪表盘统计和扫描任务状态，`result.engine.status` 表示任务进程 PID 是否存在，`result.engine.last` 未配置时为 `0`。
- `GET /api/statistic` 的 `by` 默认 `tag`，常用值为 `tag`、`language`；`tag` 不传或为空字符串时表示不过滤；`by` 当前仍需白名单加固。

Settings 兼容语义：

- GitHub 设置响应不得包含原始 `password` 或 PAT；`POST` 成功使用 body `status=201`，认证失败使用 body `status=401`；`DELETE` 成功使用 body `status=404`。
- Query 设置的 `POST /api/setting/query` 按 `tag` 判断新增或更新；`DELETE` 删除规则时会删除同 tag 的泄露结果，成功使用 body `status=404`。
- Cron 未配置时 `GET /api/setting/cron` 使用 body `status=400`、`msg=请配置查询页数和周期`、`result=null`；保存后会尝试向已有任务 PID 发送 `SIGHUP`。
- Blacklist 和 Notice 的 `POST` 会对输入文本执行 `strip()` 并移除空格；`DELETE` 成功使用 body `status=404`。
- Mail 设置响应不得包含 SMTP `password`；`test=true` 的发送行为必须可 mock，不得在默认测试中发送真实邮件。
- Webhook 设置使用 `GET/POST/DELETE /api/setting/webhook`；请求字段为 `provider`、`webhook_url`、`secret`、`domain`、`enabled`、`test`，当前 `provider` 支持 `dingtalk` 和 `feishu`。
- Webhook `GET` 返回 `provider`、脱敏 `webhook_url` 和 `webhook_hash`；`DELETE` 使用 `webhook_url` 或 `webhook_hash` 参数，成功时 body `status=200`。
- Webhook 存储要求新记录包含 `provider`；不为缺少 `provider` 的旧 Mongo 数据做自动兼容或推断。

API 文档入口：

- `GET /api/openapi.json`、`GET /api/docs` 和未来 `GET /api/redoc` 生产默认关闭。
- 关闭时返回 HTTP 404，body 为 `status=404`、`msg=API docs disabled`、`result=[]`。
- Swagger UI 会读取 `/api/openapi.json`。
- 文档入口暴露 API 路径、参数和响应结构，生产环境必须放在认证代理、VPN、内网或应用鉴权之后。

健康检查：

- `GET /api/health` 不使用 `status/msg/result` 包裹结构。
- 响应字段为 `github` 和 `mongodb`；两者都可能是成功对象/布尔值或错误字符串。
- 后端访问 `https://api.github.com/`，HTTP 状态码小于 500 视为 GitHub API 可达；匿名 rate limit 403 不判为不可达。
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

- GitHub username/password 兼容登录字段和 PAT。
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
