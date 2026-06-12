# 后端测试策略

职责：本文定义后端测试分层、覆盖范围、外部依赖策略和必须补测试的变更类型。

职责边界：

- 具体命令、CI job 和 smoke 脚本调用方式统一维护在 `IMPLEMENTATION_GUIDE.md`。
- API 人工兼容语义维护在 `DESIGN.md`，机器契约维护在 `docs/api/openapi.yaml`；本文只从测试视角列覆盖点。
- 切片完成前的执行门禁维护在 `CHECKLIST.md`，本文不维护 checkbox。
- 当前真实验证结果维护在 `PROGRESS.md`，本文不记录某次执行是否通过。

## 目标

- 保持 `/api/*` 路径、参数、HTTP 方法和 response body 稳定。
- 明确区分 HTTP status code 与响应 body 中的 `status` 字段。
- 覆盖当前前端依赖的接口行为。
- 外部系统默认 mock，必要时补受控 smoke。
- OpenAPI 同时服务 Swagger 文档和契约校验。

## 测试分层

### Unit

覆盖纯函数、参数转换、响应构造、分页参数、状态映射、document 到 response 的适配和敏感字段脱敏。Unit 测试不得连接 MongoDB、Redis、GitHub、SMTP 或真实 webhook。

### Service

覆盖结果处理、设置增删改查、统计聚合、GitHub 搜索编排、邮件和 webhook payload 构造。Service 测试通过 fake 或 monkeypatch 隔离 repository、integration 和 Huey enqueue。

### Repository

覆盖 MongoDB 查询条件、分页、排序、聚合、upsert、replace、delete 和 projection。新 repository 代码必须使用 PyMongo 4 兼容 API；真实 MongoDB 行为通过 MongoDB smoke 或 compose smoke 验证。

### API Contract

使用 FastAPI TestClient 对 ASGI app 发请求，验证 HTTP status、JSON shape、关键字段和兼容业务 `status` 值。

P0 覆盖：

- `GET /api/health`
- `GET /api/leakage`
- `PATCH /api/leakage`
- `GET /api/leakage/info`
- `GET /api/leakage/code`
- `GET /api/trend`
- `GET /api/statistic`
- `GET/POST/DELETE /api/setting/github`
- `GET/POST/DELETE /api/setting/query`
- `GET/POST /api/setting/cron`
- `GET/POST/DELETE /api/setting/blacklist`
- `GET/POST/DELETE /api/setting/notice`
- `GET/POST /api/setting/mail`
- `GET/POST/DELETE /api/setting/webhook`

高风险回归点：

- `/api/leakage` 的 `status` query 参数 JSON 字符串兼容行为。
- DELETE 接口 body `status: 404` 兼容成功语义。
- `/api/health` 非 `status/msg/result` response shape。
- GitHub account、SMTP 和 webhook 设置响应脱敏。

完整协议细节以 `DESIGN.md` 的 API 兼容语义为准。

### OpenAPI

OpenAPI 测试必须确认：

- `docs/api/openapi.yaml` 可被解析。
- OpenAPI paths 覆盖 `server/api/*/routes.py` 注册的全部 `/api/*`。
- 示例和描述不包含真实 PAT、SMTP password、webhook token、MongoDB URI secret 或 Redis secret。
- 高风险兼容行为写入 schema 或描述。

### Schemathesis Read-Only Smoke

Schemathesis smoke 只保留 `GET` operation，避免修改数据。`/api/leakage` 的 `status` query 使用 smoke-safe JSON 字符串。写接口仍由 API contract tests 和集成 smoke 覆盖。

### Worker Smoke

Worker smoke 覆盖 Huey app 初始化、任务注册、periodic task、mock 外部依赖下的最小任务流程，以及真实 Redis broker 下的后台 consumer 消费。默认测试不得访问真实 GitHub、SMTP 或生产 webhook。

### Compose Smoke

Compose smoke 从测试策略上必须覆盖 fresh volume 启动、service health、数据服务、HTTP 入口、静态资源、nginx、worker 消费和日志/secret 风险。具体脚本覆盖项和命令以 `IMPLEMENTATION_GUIDE.md` 为准。

## 测试目录

```text
server/
  conftest.py
  api/<domain>/tests/    # domain contract/service/repository tests
  core/tests/            # core response/config/security tests
  workers/tests/         # worker import/task tests
  tests/                 # compose、Docker、MongoDB、Redis、OpenAPI、Schemathesis 等工程 harness
```

规则：

- 有 `routes.py` 的 domain 必须有同域 tests。
- 有 `repository.py` 的 domain 必须通过 service 作为调用边界。
- 工程 smoke 保留在 `server/tests/`，不要塞进业务 domain。
- 共享 mock 通过 fixture 提供，避免在测试体内重复大段 monkeypatch。

## 外部依赖策略

- MongoDB：unit/service 使用 fake 或 mongomock；真实行为由 MongoDB smoke 或 compose smoke 覆盖。
- Redis/Huey：默认 mock enqueue；真实 broker 消费由 Redis worker smoke 或 compose smoke 覆盖。
- GitHub：默认 mock PyGithub client、搜索结果、rate limit 和异常；真实 GitHub smoke 只允许使用专用低权限 PAT，日志必须脱敏。
- Mail：mock SMTP client，捕获收件人、标题和正文，不发送真实邮件。
- Webhook：mock HTTP client 或本地 fake server，禁止使用生产机器人 URL。

## 必须补测试的变更类型

以下变更不能只改代码，必须同步补或更新测试：

- 修改 `/api/*` 路径、参数、HTTP method、query/body 结构。
- 修改任一响应 body 的 `status/msg/result/total` 或字段命名。
- 修改 `/api/leakage` 筛选、分页、排序、状态处理。
- 修改任何 settings 增删改查接口。
- 修改 GitHub token、SMTP password、webhook 等敏感字段展示或存储。
- 替换 PyMongo API、MongoDB 连接认证或 health check。
- 升级 Python、FastAPI、Uvicorn、Gunicorn、PyMongo、Redis client、Huey、PyGithub、Requests。
- 调整 Huey task、定时任务、GitHub 搜索、邮件或 webhook 通知。
- 引入新的 FastAPI route、schema 层或 domain service/repository。
- 新增或修改 `docs/api/openapi.yaml`。

## 记录规则

- 每次有意义的后端切片完成后，更新 `PROGRESS.md`。
- 未运行的测试只能写为“未运行”或“待补”，不能写成通过。
- 如果测试暴露的是当前兼容行为，不直接改协议，先记录风险和影响。
