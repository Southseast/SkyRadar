# 后端切片完成检查清单

职责：本文只维护后端切片完成和发布前需要逐项确认的门禁清单。

职责边界：

- 本文使用 checkbox 表达“是否已检查”，不解释设计背景。
- 架构和 API 契约语义见 `DESIGN.md`，测试策略见 `TESTING.md`，命令和 CI/部署规则见 `IMPLEMENTATION_GUIDE.md`。
- 风险背景见 `RISKS.md`，当前真实验证结果见 `PROGRESS.md`。
- 如果某项规则需要长期解释，应更新对应职责文档，再在本文保留简短检查项。

使用规则：

- 每个切片完成前复制本清单并逐项确认。
- 未涉及的项目可以标记为不适用，但必须说明原因。
- 未运行的验证不能写成通过。
- 如果用户限制只能编辑部分文件，不得越界修改其他文档；需要补的内容在汇报中列为待办。

## 1. 范围和回滚

- [ ] 本切片目标单一，未把运行时、数据库 API、HTTP 框架、Docker 拓扑和安全修复混在一起。
- [ ] 已列出受影响文件、接口、配置、worker、部署入口和文档。
- [ ] 已确认不修改无关业务行为。
- [ ] 已确认不修改生成产物，例如 `client/dist`。
- [ ] 已准备回滚方式，例如恢复旧镜像 tag、依赖锁、配置开关、路由开关或单个 commit revert。
- [ ] 如回滚会影响数据结构或任务状态，已写明人工恢复步骤。

## 2. API 契约门禁

- [ ] 所有业务接口使用 `/api/v1/*` 路径、复数名词资源、标准 HTTP 方法和精确 HTTP status。
- [ ] 成功响应使用 `data/meta/links`；列表分页使用 `meta.page`、`meta.page_size` 和 `meta.total`。
- [ ] 错误响应使用统一 `error/message/detail/request_id` 结构，且不回显敏感 payload。
- [ ] DELETE 成功使用 HTTP 204 且不返回 body。
- [ ] `/api/v1/health` 使用标准成功响应结构，依赖不可用时可返回 HTTP 503 和统一错误体。
- [ ] `/api/v1/leakages` 使用明确 query 字段，不透传 JSON 字符串查询或 Mongo 查询操作符。
- [ ] 搜索、筛选、排序和分页字段符合 `DESIGN.md` 的 RESTful API 设计规范。
- [ ] 涉及前端依赖的行为时，已检查 `docs/frontend/IMPLEMENTATION_GUIDE.md` 和前端 adapter 影响。
- [ ] API 行为变化已同步契约测试；涉及前端依赖时已同步前端 adapter。

## 3. OpenAPI 和 Swagger 门禁

- [ ] 如新增、删除或改变 API，已同步 `docs/api/openapi.yaml`。
- [ ] OpenAPI paths 只描述最终 `/api/v1/*` 契约。
- [ ] 如 runtime 已注册 `/api/v1/*` route，OpenAPI 已覆盖这些 route。
- [ ] 已运行 `python scripts/backend_openapi_secret_scan.py`，OpenAPI 示例不包含真实 GitHub PAT、SMTP password、webhook token、MongoDB URI、Redis secret、内网地址或生产域名。
- [ ] Swagger UI、ReDoc 和 `/api/v1/openapi.json` 的暴露方式符合生产默认关闭策略。
- [ ] 如引入自动生成 OpenAPI，已与人工 `docs/api/openapi.yaml` 做差异审查。
- [ ] 如工具已配置，已运行 OpenAPI schema 校验。

## 4. 测试门禁

- [ ] 已运行后端 pytest；如未配置或未运行，已记录原因。
- [ ] API 行为变化已补或更新 FastAPI TestClient 契约测试。
- [ ] OpenAPI 变化已补 schema 校验或至少运行 YAML/OpenAPI 解析检查。
- [ ] 高风险行为已有回归测试：`data/meta/links`、错误体、DELETE 204、`/api/v1/health`、敏感字段脱敏。
- [ ] GitHub、SMTP、webhook、MongoDB、Redis 默认使用 mock、fake 或受控测试环境。
- [ ] 测试输出、fixture、snapshot、CI artifact 不包含真实 secret、泄露代码或完整敏感资产。
- [ ] 如引入 Schemathesis，只读 smoke 不覆盖会修改数据的 POST、PATCH、DELETE，除非有隔离环境。
- [ ] 已更新 `PROGRESS.md` 最近验证记录，且没有把未运行测试写成通过。

## 5. 敏感字段和安全门禁

- [ ] API response 不新增 GitHub PAT、password、token、SMTP password、webhook token、MongoDB URI 或 Redis secret。
- [ ] GitHub account response 仍只包含展示字段，或已把当前实现风险记录为安全债务。
- [ ] SMTP password 不进入 response、日志、OpenAPI 示例或测试快照。
- [ ] webhook URL 已脱敏展示；完整 URL 不进入日志、示例或快照。
- [ ] 错误消息不回显 secret 或完整外部请求 payload。
- [ ] 日志记录已脱敏，只保留必要状态码、错误类型和摘要。
- [ ] 通知测试不会默认打生产邮箱或生产 webhook。
- [ ] 当前 `/api/v1/*` 无应用级鉴权的风险未被新入口扩大。

## 5A. nginx Basic Auth 门禁

适用于 nginx Basic Auth 相关切片；其他切片可标记为不适用。长期决策见 ADR-0008。

- [ ] 未设置 `SKYRADAR_BASIC_AUTH_ENABLED` 时，nginx Basic Auth 默认启用。
- [ ] 默认启用时，同时设置 `SKYRADAR_BASIC_AUTH_USERNAME` 和 `SKYRADAR_BASIC_AUTH_PASSWORD` 可启动并访问。
- [ ] 只配置用户名或只配置密码时容器启动失败。
- [ ] 未配置用户名和密码且未显式关闭 Basic Auth 时，nginx/all-in-one 角色启动失败。
- [ ] 仅设置 `SKYRADAR_BASIC_AUTH_ENABLED=false` 时允许无认证本地开发或 smoke。
- [ ] 启用 Basic Auth 后，无认证访问页面、静态资源和 `/api/v1/health` 返回 HTTP `401`。
- [ ] 启用 Basic Auth 后，正确用户名和密码可访问页面和 `/api/v1/health`。
- [ ] compose nginx 和 all-in-one healthcheck 默认携带同一组环境变量认证信息；显式关闭时才无认证。
- [ ] htpasswd 文件在运行时生成，不写入 Git、镜像构建层、日志或测试快照。
- [ ] Basic Auth 密码不出现在 `docker compose logs`、OpenAPI 示例、测试 fixture 或 CI artifact。
- [ ] 文档明确 Basic Auth 需要 HTTPS、VPN、内网或可信反向代理配合。

## 6. PyMongo 4 门禁

- [ ] 未新增 `collection.count()`。
- [ ] 未新增 `collection.save()`。
- [ ] 未新增旧式 `collection.update()`。
- [ ] 未新增 `db.authenticate()`。
- [ ] 未新增 `db.last_status()`。
- [ ] 新增 MongoDB 代码符合 `IMPLEMENTATION_GUIDE.md` 维护的 PyMongo 4 允许 API 清单。
- [ ] MongoDB 认证由 `MongoClient(...)` URI 或参数处理。
- [ ] health check 使用 `client.admin.command("ping")` 或 `db.command("ping")`。
- [ ] 复杂查询、upsert、分页、聚合和删除逻辑放入 repository 或 helper，未散落到 route 和 worker。

## 7. FastAPI 和防回归门禁

- [ ] `api:app` 保持 FastAPI ASGI 入口，除非本切片明确改变部署入口。
- [ ] Gunicorn 使用 Uvicorn worker 运行 ASGI app，或已记录替代 ASGI server 策略。
- [ ] schema、service、repository、integration 调整未改变 URL 和 response shape。
- [ ] 不恢复 Flask、Flask-RESTful、`reqparse` 或 `controllers/*` 兼容导出；参数默认值、类型转换和错误语义由 contract 测试覆盖。
- [ ] FastAPI route 保持原 URL、参数、body 和 response body。
- [ ] 调用同步 PyMongo、PyGithub、Requests、smtplib 或 Huey 的 FastAPI route 使用普通 `def`，或在必须 `async def` 读取 body/form 时显式通过 `run_in_threadpool` 调同步 service，并记录原因和验证。
- [ ] 同一组契约测试覆盖 FastAPI 实现。

## 8. Worker 门禁

- [ ] Huey worker import 阶段不发起 GitHub、SMTP、webhook 等外部请求。
- [ ] 修改任务调度、队列、Redis 配置或任务参数时，已补 worker smoke 或记录验证缺口。
- [ ] worker 只负责任务注册、调度入口和参数反序列化；业务逻辑逐步下沉到 service。
- [ ] Huey periodic task 采用固定 tick；实际调度周期由 MongoDB task setting 的 `minute` 和 `next_due_at` 控制。
- [ ] `PUT /api/v1/task-schedules/current` 后新 `minute` 不依赖 SIGHUP、worker 重启或动态改 Huey crontab，并在下一次固定 tick 尽快生效。
- [ ] 到期任务 claim 使用 MongoDB 原子条件更新，并已覆盖并发或连续 tick 下防重复 enqueue。
- [ ] enqueue 成功后按当前 `minute` 推进 `next_due_at`；未到期、禁用或 claim 失败场景不会 enqueue。
- [ ] GitHub 搜索、rate limit、结果入库、资产提取和通知发送可被 mock 测试。
- [ ] worker 日志不打印 token、SMTP password、完整 webhook URL、完整泄露代码或敏感资产。
- [ ] Python、Huey 或 Redis 升级后，已验证 worker 可初始化并执行最小任务。
- [ ] 如拆出独立 Redis service，Web 和 Worker 均通过 `REDIS_HOST`、`REDIS_PORT` 或等价配置连接独立 Redis，而不是隐式连接容器内 localhost。
- [ ] 如拆出独立 Worker service，API service 不再托管 Huey consumer，Worker service 可独立重启且不影响 API HTTP 进程。
- [ ] Web/Worker 拆分后已验证真实 Redis broker 下的 Huey 后台消费，而不只是 import smoke。
- [ ] Web 和 Worker 使用一致的 MongoDB、Redis、GitHub、SMTP 和 webhook 配置来源，未出现只在一个 service 中生效的隐式配置。

## 9. Docker 和 Ops 门禁

- [ ] Python 运行时目标符合决策记录，优先 Python 3.13，阻塞时才使用 3.12。
- [ ] 不依赖 EOL Python 或 EOL Debian 作为目标运行环境。
- [ ] Dockerfile、supervisor、Gunicorn、nginx 变更已说明影响范围。
- [ ] `/api` 反向代理可覆盖 `/api/v1/*`，或已完成部署验证和回滚设计。
- [ ] Swagger/OpenAPI 文档入口在生产默认关闭，或被认证代理、VPN、内网保护。
- [ ] 环境变量不在镜像层、日志或文档示例中泄露真实值。
- [ ] MongoDB 和 Redis 连接配置支持测试环境和生产环境隔离。
- [ ] 如拆分 API、worker、nginx 镜像或进程，已分别验证启动、健康检查和日志路径。
- [ ] MongoDB 镜像如果使用 `latest`，仅作为开发探索或显式 smoke 输入；CI、发布和稳定复现必须使用固定 tag 或固定 minor 系列。
- [ ] MongoDB 固定版本候选已记录真实版本号、宿主 Docker/Linux kernel 验证结果和回滚方式。
- [ ] 使用 fresh volume 的验证已明确标注为非生产数据丢弃场景；生产或保留数据场景必须另有备份、恢复、FCV、索引和回滚步骤。
- [ ] Redis 独立 service 已固定运行来源和服务端版本，并记录 `redis-server --version` 验证结果。
- [ ] compose smoke 已按 `IMPLEMENTATION_GUIDE.md` 标准覆盖项执行；未覆盖项已记录为待补验证。
- [ ] `depends_on` 未被当成服务可用性的唯一依据；真实请求或消费结果已作为最终可用性判断。

## 10. 文档门禁

- [ ] 架构、目录、分层或 FastAPI/ASGI 路线变化已更新 `DESIGN.md` 或 `DECISIONS.md`。
- [ ] API 行为变化已更新 `DESIGN.md` 和 `docs/api/openapi.yaml`。
- [ ] Swagger/OpenAPI 暴露方式变化已更新 `IMPLEMENTATION_GUIDE.md`。
- [ ] 测试策略或 coverage 范围变化已更新 `TESTING.md`；命令变化已更新 `IMPLEMENTATION_GUIDE.md`。
- [ ] 安全边界、敏感字段或日志规则变化已更新 `IMPLEMENTATION_GUIDE.md` 或 `RISKS.md`。
- [ ] CI、Docker、部署或 worker 验证变化已更新 `IMPLEMENTATION_GUIDE.md` 或 `PROGRESS.md`。
- [ ] 完成有意义后端切片后已更新 `PROGRESS.md`。
- [ ] 文档没有记录未实际执行的验证。

## 11. 发布前最终门禁

- [ ] 后端 pytest 通过，或已明确阻塞原因和放行风险。
- [ ] OpenAPI schema 校验通过，或已明确阻塞原因和放行风险。
- [ ] 关键 API contract smoke 通过：v1 health、leakage 列表、leakage 详情、统计、设置读写。
- [ ] worker smoke 通过，或本次发布不涉及 worker 且已说明。
- [ ] Docker/nginx/Gunicorn 或等价部署入口验证通过，或本次发布不涉及部署且已说明。
- [ ] 安全检查通过：无真实 secret、无新增公网文档入口、无通知测试外发风险。
- [ ] 回滚路径已确认可执行。
- [ ] `PROGRESS.md` 已记录本次真实验证结果、未验证项和下一步。

## 12. 汇报模板

完成切片后汇报：

```text
改动文件：
- ...

关键内容：
- ...

验证：
- 已运行：...
- 未运行：...

风险和待办：
- ...
```
