# 后端实现指南

职责：本文是后端实现期操作规则的收敛入口，负责本地运行、标准命令、配置、CI、部署、运维、安全操作、依赖基线和 Agent 执行规则。

职责边界：

- 架构分层、domain 边界、REST API 契约语义和 sync/async 设计原则写入 `DESIGN.md`，本文只保留执行规则和命令。
- 长期技术选择的理由写入 `DECISIONS.md`，本文只记录当前如何执行。
- 当前状态和真实验证结果写入 `PROGRESS.md`，本文只维护可复用命令模板。
- 测试分层写入 `TESTING.md`，切片门禁写入 `CHECKLIST.md`。
- 后续不要再为本地开发、CI、运维、安全、依赖、FastAPI 维护、Agent 规则等主题新增独立文档；除非内容已经大到影响维护，否则统一补充到本文。

## 基本原则

- API 契约以 `/api/v1/*` 为最终 RESTful 形态；修改路径、HTTP 方法、query/body 参数或 response body 必须同步 OpenAPI、契约测试和前端 adapter。
- 先补契约测试和 OpenAPI 校验，再升级 Python、PyMongo、Web 框架或 Docker 镜像。
- 当前主 HTTP 入口为 FastAPI ASGI app：`api:app`，由 `server/api/__init__.py` 暴露。
- 架构禁区和 sync/async 规则以 `DESIGN.md` 为准；新增实现不得恢复 Flask、Flask-RESTful、controller monkeypatch 或 `reqparse`。
- 未运行的测试、smoke 和校验只能记录为“未运行”或“待补”，不能写成通过。
- 写接口默认接收 JSON；参数解析保留在 FastAPI route 适配层或 schema adapter 中，不再引入 `reqparse`。

## 本地开发

当前运行基线：

- FastAPI app 入口：`api:app`。
- Gunicorn/ASGI 入口：`gunicorn -w10 -k uvicorn.workers.UvicornWorker -b0.0.0.0:8888 api:app`。
- Huey worker：`huey_consumer.py workers.huey -k process -w 4`；Huey app 和任务定义位于 `server/workers/`，任务业务流程调用 `server/api/<domain>/` 下的 service。
- 后端脚本、测试和容器 supervisor 程序默认从项目根目录执行；通过 `PYTHONPATH=server` 暴露 `api`、`core`、`workers` 等现有顶层导入。
- 默认 compose 拓扑中，独立 `nginx` service 监听 `80`，静态资源来自 `/SkyRadar/client/dist`，`/api` 反向代理到 `skyradar:8888`。
- `skyradar-all-in-one` 回滚 profile 中，nginx 与 Gunicorn 同容器运行，`/api` 反向代理到 `127.0.0.1:8888`。
- Redis 当前由 compose 独立 `redis` service 提供；单容器兼容模式仍可由 supervisor 启动。
- MongoDB 通过 `MONGODB_URI` 指向外部或 compose 内的 `mongo` 服务。
- 新代码通过 `server/core/` 边界读取配置、数据库句柄、统一 response helper、日志和安全脱敏 helper；不恢复旧全局配置、数据库或全局 response 入口。

当前可用入口：

```bash
PYTHONPATH=server uvicorn api:app --reload --host 127.0.0.1 --port 8888
```

生产入口：

```bash
PYTHONPATH=server gunicorn -w10 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8888 api:app
```

当前 `compose.yml` 提供 API、nginx、Worker、Redis、MongoDB 拆分拓扑，并保留单容器兼容 profile：

```bash
docker compose up --build
```

当前 compose 服务拆分：

```text
skyradar              # API role，只运行 Gunicorn/FastAPI，监听 8888
nginx               # nginx role，负责静态资源和 /api 反向代理，暴露外部 HTTP 端口
worker              # Worker role，运行 Huey consumer，只处理后台任务消费
redis               # Huey broker/cache，独立 service
mongo               # MongoDB，独立 service
skyradar-all-in-one   # all-in-one profile，短期兼容/回滚路径
```

当前 compose 基线：

- MongoDB 默认镜像为 `mongo:8.2.7`，可通过 `SKYRADAR_MONGO_IMAGE` 覆盖。
- Redis service 不再拉取独立 Redis 镜像，复用项目镜像内 Debian Trixie `redis-server`，以无持久化模式运行；实际 Redis server 版本以镜像构建和 compose smoke 输出为准。
- Node 构建阶段使用 `public.ecr.aws/docker/library/node:24-trixie-slim`。
- Python 运行阶段使用 `python:3.13-slim-trixie`，通过 `uv==0.11.19` 安装 requirements。
- Docker 镜像运行阶段 `WORKDIR` 为 `/SkyRadar`，并设置 `PYTHONPATH=/SkyRadar/server`；supervisor 管理的 API 和 Worker 程序也从 `/SkyRadar` 启动。

拓扑约束：

1. `skyradar-all-in-one` profile 仅作为短期回滚路径。
2. API、Worker 都通过 `REDIS_HOST=redis`、`REDIS_PORT=6379` 访问独立 Redis service。
3. API service 只跑 Gunicorn/FastAPI，Worker service 只跑 Huey consumer。
4. API 和 Worker 必须使用同一组业务配置来源，至少包括 `MONGODB_URI`、`REDIS_HOST`、`REDIS_PORT` 和外部通知配置。
5. `SKYRADAR_ROLE=nginx` 只启动 nginx，`SKYRADAR_NGINX_UPSTREAM` 默认由 compose 设置为 `skyradar:8888`；`SKYRADAR_ROLE=all` 默认 upstream 为 `127.0.0.1:8888`。
6. `depends_on` 只能表达启动顺序，不能代替健康检查；compose smoke 必须用真实请求、静态资源请求、nginx 配置检查和 worker 任务消费结果确认服务可用。

Huey 调度实现规则：

- periodic task 使用固定 tick 唤醒 worker 检查，不根据用户配置的 `minute` 动态注册或重写 Huey crontab。
- MongoDB task setting 是调度事实来源；`minute` 和 `next_due_at` 共同决定是否到期以及下一次到期时间。
- `PUT /api/v1/task-schedules/current` 更新 `minute` 后，不要求向 worker 发送 SIGHUP，也不要求动态重启 Huey consumer；新周期必须在下一次固定 tick 读取 MongoDB setting 后尽快生效。
- claim 到期任务必须通过 MongoDB 原子条件更新完成，条件至少约束当前任务存在、启用状态和 `next_due_at <= now`，更新必须同时推进 `next_due_at` 或写入等价防重复状态。
- enqueue 必须发生在成功 claim 之后；未 claim 成功的 worker 不得 enqueue 同一周期任务。
- 推进 `next_due_at` 时使用 claim 时读取到的当前 `minute`，并以可测试的时钟来源计算，避免多 worker、时间漂移或 PUT 并发导致重复投递。

标准后端验证命令：

```bash
# backend-test
uv run --no-project --python 3.13 --with-requirements deploy/pyenv/requirements-dev.txt pytest

# backend-openapi-check
uv run --no-project --python 3.13 --with-requirements deploy/pyenv/requirements-dev.txt python scripts/backend_openapi_check.py

# backend-openapi-secret-scan
uv run --no-project --python 3.13 --with-requirements deploy/pyenv/requirements-dev.txt python scripts/backend_openapi_secret_scan.py

# backend-route-coverage
uv run --no-project --python 3.13 --with-requirements deploy/pyenv/requirements-dev.txt python scripts/backend_route_coverage.py

# backend-architecture-guard
uv run --no-project --python 3.13 --with-requirements deploy/pyenv/requirements-dev.txt python scripts/backend_architecture_guard.py

# backend-http-smoke
uv run --no-project --python 3.13 --with-requirements deploy/pyenv/requirements-dev.txt python scripts/backend_http_smoke.py

# backend-github-pat-smoke
uv run --no-project --python 3.13 --with-requirements deploy/pyenv/requirements-dev.txt python scripts/backend_github_pat_smoke.py

# backend-worker-smoke
uv run --no-project --python 3.13 --with-requirements deploy/pyenv/requirements-dev.txt python scripts/backend_worker_smoke.py

# backend-schemathesis-smoke
uv run --no-project --python 3.13 --with-requirements deploy/pyenv/requirements-dev.txt python scripts/backend_schemathesis_smoke.py

# backend-redis-worker-smoke
uv run --no-project --python 3.13 --with-requirements deploy/pyenv/requirements-dev.txt python scripts/backend_redis_worker_smoke.py

# backend-mongo8-smoke
uv run --no-project --python 3.13 --with-requirements deploy/pyenv/requirements-dev.txt python scripts/backend_mongo8_smoke.py

# backend-docker-build-smoke
uv run --no-project --python 3.13 --with-requirements deploy/pyenv/requirements-dev.txt python scripts/backend_docker_build_smoke.py

# backend-compose-smoke
uv run --no-project --python 3.13 --with-requirements deploy/pyenv/requirements-dev.txt python scripts/backend_compose_smoke.py
```

上述命令同步记录在 `pyproject.toml` 的 `[tool.skyradar.commands]` 中，作为不引入额外 task-runner 依赖的命令索引。
当前后端命令使用 `uv run --no-project --python 3.13 --with-requirements deploy/pyenv/requirements-dev.txt ...`，保持 requirements 驱动，不启用 uv project/lock 工作流。Docker 构建只用 pip bootstrap `uv==0.11.19`，应用运行依赖由 `uv pip install --system -r deploy/pyenv/requirements.txt` 安装。
`backend-docker-build-smoke` 默认等价于：

```bash
docker build -t skyradar-backend-refactor-smoke .
```

该脚本只负责镜像构建 smoke，不启动容器，也不执行真实 HTTP smoke。需要查看命令但不执行 Docker 时使用：

```bash
uv run --no-project --python 3.13 --with-requirements deploy/pyenv/requirements-dev.txt python scripts/backend_docker_build_smoke.py --dry-run
```

标准 compose smoke 命令：

```bash
uv run --no-project --python 3.13 --with-requirements deploy/pyenv/requirements-dev.txt python scripts/backend_compose_smoke.py \
  --project-name skyradar-compose-smoke \
  --http-port 18082 \
  --fresh-volumes \
  --json
```

该脚本覆盖：

- fresh volume 启动和自动清理。
- MongoDB 实际版本检查、`ping` 和 CRUD/聚合 smoke。
- Redis `PING` 和版本记录。
- API service 健康检查和经 nginx 反向代理的 `/api/v1/health` 真实请求。
- nginx service 健康检查、静态首页、nginx 配置和 `/var/log/nginx` 日志路径。
- Worker service Huey consumer 可用性检查和真实任务消费。
- compose logs failure/secret 扫描。

GitHub Actions 后端 workflow 位于 `.github/workflows/backend.yml`，包含：

- `backend-contract`：pytest、compileall、OpenAPI check、OpenAPI secret scan、route coverage、architecture guard。
- `backend-compose-smoke`：fresh volume compose smoke。

## 配置

当前后端已读取：

- `MONGODB_URI`：MongoDB 连接 URI，默认 `mongodb://localhost:27017`。
- `MONGODB_DATABASE`：MongoDB 数据库名，默认 `skyradar`。
- `MONGODB_USER`：历史 MongoDB 用户名。
- `MONGODB_PASSWORD`：历史 MongoDB 密码。
- `MONGODB_AUTH_SOURCE`：MongoDB 认证库，默认 `skyradar`。
- `REDIS_HOST`：Redis host，默认 `localhost`。
- `REDIS_PORT`：Redis port，默认 `6379`。
- `REDIS_RESULT_CACHE_DB`：Redis 结果缓存库，默认 `1`。
- `SKYRADAR_API_DOCS_ENABLED`：是否启用 `/api/v1/docs` 和 `/api/v1/openapi.json`，默认关闭。
- `SKYRADAR_OPENAPI_PATH`：OpenAPI YAML 文件路径，默认 `docs/api/openapi.yaml`。

当前 nginx/entrypoint 已读取：

- `SKYRADAR_ROLE`：容器角色，支持 `all`、`web`、`nginx`、`worker`。
- `SKYRADAR_NGINX_UPSTREAM`：nginx `/api` 反向代理 upstream，默认 `127.0.0.1:8888`；compose 的独立 nginx service 设置为 `skyradar:8888`。
- `SKYRADAR_BASIC_AUTH_ENABLED`：是否启用 nginx Basic Auth，默认 `true`；仅可信本地开发可显式设置为 `false`。
- `SKYRADAR_BASIC_AUTH_USERNAME`：nginx Basic Auth 用户名，默认启用时必须设置。
- `SKYRADAR_BASIC_AUTH_PASSWORD`：nginx Basic Auth 密码，默认启用时必须设置。

规则：

- MongoDB 认证优先放入 `MONGODB_URI` 或 `MongoClient(...)` 参数，不继续使用 `db.authenticate()`。
- 应用配置统一收敛到 `server/core/config.py` 或等价配置层；nginx 运行配置由 `docker-entrypoint.sh` 渲染。
- secret 不写入文档示例、OpenAPI 示例、测试快照、日志或前端可见状态。

## nginx Basic Auth

状态：已采纳的最小访问保护方案。

边界：

- 只在 nginx 层做访问保护，不新增应用内用户、登录页、服务端 session 或 RBAC。
- 适用于单人或小范围可信部署。
- 不替代 HTTPS、VPN、防火墙、MongoDB/Redis 网络隔离和 secret 管理。

实现规则：

- Basic Auth 默认启用；未显式设置 `SKYRADAR_BASIC_AUTH_ENABLED=false` 时，`SKYRADAR_BASIC_AUTH_USERNAME` 和 `SKYRADAR_BASIC_AUTH_PASSWORD` 必须同时设置，否则 nginx/all-in-one 角色启动失败。
- 仅可信本地开发环境可设置 `SKYRADAR_BASIC_AUTH_ENABLED=false`；关闭后不生成 `auth_basic` 配置。
- entrypoint 使用运行时密码生成 `/etc/nginx/.skyradar_htpasswd`，不写入仓库或镜像构建层。
- nginx server 级别启用 Basic Auth，覆盖前端页面、静态资源和 `/api`。
- compose healthcheck 在默认启用 Basic Auth 时必须使用同一组环境变量携带认证信息；显式关闭时才允许无认证 healthcheck。
- 生产或公网可达环境必须配合 HTTPS 或受控内网；不得在明文 HTTP 公网环境下依赖 Basic Auth。
- 日志、测试输出和错误消息不得打印 Basic Auth 密码。

## CI 设计

后端 CI 应在以下文件变化时触发：

- `server/**`
- `deploy/pyenv/requirements.txt`
- `Dockerfile`
- `compose.yml`
- `deploy/supervisor/**`
- `deploy/nginx/**`
- `docker-entrypoint.sh`
- `docs/api/openapi.yaml`
- `docs/backend/**`
- `.github/workflows/**`
- `client/src/lib/api/**`
- `client/src/types/api.ts`
- `client/src/features/**` 中依赖 `/api/v1/*` adapter 的变更

必跑目标检查：

- OpenAPI schema validation：当前由 `scripts/backend_openapi_check.py` 做 OpenAPI 3.0.x 基础结构校验、本地 `$ref` 校验、唯一 `operationId` 和 response 结构校验。
- route coverage：当前由 `scripts/backend_route_coverage.py` 校验 `docs/api/openapi.yaml` 只描述最终 `/api/v1/*` paths；v1 runtime routes 落地后可启用注册路由覆盖检查。
- 后端 pytest：当前由 `uv run --no-project --python 3.13 --with-requirements deploy/pyenv/requirements-dev.txt pytest` 执行。
- worker smoke：涉及任务调度 minute 修复时，必须覆盖固定 tick、MongoDB `minute/next_due_at` 控制周期、原子 claim、防重复 enqueue 和 `next_due_at` 推进。
- Docker build smoke。
- compose smoke：目标覆盖 fresh volume 启动、service health、真实 `/api/v1/health`、静态首页、nginx 配置和日志路径、MongoDB 版本和 Redis/Huey 消费。
- 前端 API adapter 联动检查：`cd client && npm run check`。

阶段能力门禁：

- OpenAPI 解析、route coverage、最小 API contract pytest。
- PyMongo 兼容改造测试、MongoDB health ping smoke。
- Python/依赖升级后的 pytest、worker smoke、Docker build smoke。
- FastAPI 主入口迁移后的同组 API contract 测试。
- service/repository 抽取、Flask-RESTful 过渡依赖移除和 domain 测试内聚。
- 任务调度 minute 修复后的固定 tick 行为、PUT 后新周期生效、原子 claim、防重复 enqueue 和 `next_due_at` 推进测试。
- nginx 独立 service、真实 compose smoke、Basic Auth 可选保护和远端 CI 回填。

## 运维和排障

当前默认 compose 拓扑由独立 service 管理：

- `nginx` service：nginx 静态资源和 `/api` 反向代理。
- `skyradar` service：Gunicorn + Uvicorn worker 运行 `api:app`。
- `worker` service：Huey worker。
- `redis` service：Huey broker/cache。
- `mongo` service：MongoDB。

单容器兼容模式由 `skyradar-all-in-one` profile 保留，并由 supervisor 管理：

- nginx。
- Gunicorn。
- Huey worker。
- Redis。

健康检查：

- `GET /api/v1/health` 使用标准 `data/meta/links` 成功响应。
- 响应 `data` 包含 `api`、`github`、`mongodb` 和 `redis` 子项。
- 依赖不可用时可以返回 HTTP `503` 和统一错误体。
- HTTP `200` 只代表健康检查成功，不应忽略子项状态。

排障顺序：

1. 检查容器是否存活。
2. 访问 `/api/v1/health`，区分 API 进程问题和依赖问题。
3. 检查 nginx 是否正确代理 `/api` 到 `skyradar:8888`。
4. 检查 Gunicorn 是否在 `skyradar` service 内监听 `0.0.0.0:8888`。
5. 检查 MongoDB URI、认证和网络连通性。
6. 检查 Redis host/port 和 Huey worker 日志。
7. 检查 GitHub rate limit、SMTP 或 webhook 外部依赖。

拆分后排障顺序：

1. 检查 `mongo` 和 `redis` service health。
2. 检查 `api` service 是否能解析并连接 `mongo`、`redis`。
3. 检查 `worker` service 是否使用与 `api` 一致的 `MONGODB_URI`、`REDIS_HOST` 和 `REDIS_PORT`。
4. 通过真实 Huey 消费 smoke 判断 Redis broker、任务序列化和 worker 进程是否同时可用。
5. 再检查 nginx 反向代理、静态资源和 `/var/log/nginx`，不把代理问题误判为 API 或 worker 问题。

日志规则：

- 不打印 GitHub PAT、SMTP password、webhook token、MongoDB URI 凭据。
- webhook URL 如果包含签名或 token，只记录平台、host 或脱敏摘要。
- API 错误响应和 worker 异常日志不拼接原始 secret。

回滚策略：

- 文档变更可单独回滚，不影响运行代码。
- Python/依赖升级每次只升级一个可验证切片，并保留旧镜像 tag。
- 服务拆分失败时回退到 supervisor 同容器兼容模式。
- nginx 独立 service 失败时可用 `docker compose --profile all-in-one up skyradar-all-in-one mongo` 启动短期回滚入口；避免同时启动默认 `nginx` 和 `skyradar-all-in-one` 占用同一 HTTP 端口。
- 无版本化前不发布破坏性 API 变化。

## 安全

当前安全基线：

- `/api/v1/*` 没有应用级鉴权。
- 设置、通知、任务调度和泄露代码接口都依赖部署网络边界保护。
- Swagger/OpenAPI 如果公网暴露，会成为无鉴权 API 的索引入口。

文档入口长期目标：

- `GET /api/v1/openapi.json`
- `GET /api/v1/docs`
- `GET /api/v1/redoc`

当前已落地：

- `GET /api/v1/openapi.json`
- `GET /api/v1/docs`

默认关闭，设置 `SKYRADAR_API_DOCS_ENABLED=true`、`1`、`yes` 或 `on` 后启用。
Docker 镜像会复制 `docs/api/openapi.yaml` 到 `/SkyRadar/docs/api/openapi.yaml`。
如需覆盖契约文件位置，可设置 `SKYRADAR_OPENAPI_PATH`。

安全规则：

- 生产默认关闭 `/api/v1/docs`、`/api/v1/redoc` 和 `/api/v1/openapi.json`。
- 如生产必须启用，必须放在认证代理、VPN、内网或应用鉴权之后。
- Swagger UI 的 Try it out 只允许在开发、预发或受控内网使用。

敏感字段：

- GitHub password、PAT、token。
- SMTP password。
- webhook token、签名参数、完整敏感 webhook URL。
- MongoDB URI 中的用户名、密码、认证库和内网地址。
- Redis password 或未来 Redis ACL secret。
- 生产数据库中的泄露代码内容、受影响资产、私有仓库链接和内部项目标识。

响应规则：

- GitHub account 正式响应 schema 不包含 `password`。
- SMTP password 不进入 response、日志、OpenAPI 示例或测试快照。
- webhook URL 应脱敏展示。
- `GET /api/v1/leakages/{leakage_id}/code` 返回泄露代码是产品功能，但不得进入普通日志和测试快照。

外部请求：

- GitHub、SMTP、DingTalk/Feishu webhook 调用应集中在 integration 层。
- DingTalk/Feishu webhook HTTP 请求必须设置超时。
- 单元测试默认不访问真实 GitHub、不发送真实邮件、不调用生产 webhook。

## PyMongo 4

新增或重构 MongoDB 代码必须兼容 PyMongo 4：

- 使用 `count_documents()` 或 `estimated_document_count()`，不新增 `collection.count()`。
- 使用 `insert_one()`、`update_one()`、`update_many()`、`replace_one(..., upsert=True)`、`delete_one()`、`delete_many()`，不新增 `collection.save()`。
- 不新增旧式 `collection.update()`。
- 认证放到 `MongoClient(...)` URI 或参数，不新增 `db.authenticate()`。
- 健康检查使用 `client.admin.command("ping")` 或 `db.command("ping")`，不使用 `db.last_status()`。
- 复杂查询、upsert 和索引创建放入 repository 或数据库 helper。

当前代码不使用 collection shim。`count()`、`save()`、`update()`、
`db.authenticate()` 和 `db.last_status()` 等 PyMongo 4 不兼容 API 不得出现在新代码中。
后续重构切片应继续把 Mongo 调用保持在 repository/helper 层。

Compose 默认 MongoDB 镜像当前固定为 `mongo:8.2.7`。
固定 tag 避免 CI、发布 smoke 和问题复现依赖 mutable `latest`。

版本策略：

- 开发探索可以显式使用 `latest`，但必须在 `PROGRESS.md` 记录当次解析出的真实版本。
- CI、发布 smoke 和可复现问题定位必须使用固定 tag，不依赖 mutable `latest`。
- 从旧数据升级时不能直接使用 fresh volume 结论；必须补备份、恢复、FCV、索引和回滚路径。
- 当前默认验证按 fresh volume 场景成立；保留数据场景必须单独验证。
- `public.ecr.aws/docker/library/mongo:8.0` 在当前 Docker/Linux kernel 6.19+ 环境下会因 MongoDB `SERVER-121912` 兼容问题拒绝启动；后续固定版本候选优先选择已通过当前宿主环境 smoke 的版本。

## 依赖升级

当前基线来自 `deploy/pyenv/requirements.txt`、`Dockerfile`、`compose.yml` 和 `deploy/supervisor/*.conf`。

| 组件 | 当前基线 | 维护规则 |
| --- | --- | --- |
| Python | `3.13` | CI、本地 uv、Docker 和 smoke 命令保持一致；降级或升级大版本需新增 ADR |
| FastAPI | `>=0.136,<0.137` | 主 HTTP 入口；route 保持薄适配层 |
| Uvicorn | `>=0.49,<0.50` | 仅作为 Gunicorn ASGI worker 使用 |
| Gunicorn | `>=26,<27` | 生产入口保持 `uvicorn.workers.UvicornWorker` |
| PyMongo | `>=4.11,<5` | 只能使用 PyMongo 4 兼容 API；MongoDB 8 smoke 防回归 |
| Redis client | `>=8,<9` | 与真实 Redis/Huey 消费 smoke 一起验证 |
| MongoDB 服务端 | `mongo:8.2.7` | CI、发布和稳定复现使用固定 tag；`latest` 仅用于显式探索 |
| Redis 服务端 | Debian Trixie `redis-server` | 由项目镜像提供，独立无持久化 service；实际版本以 compose smoke 输出为准 |
| Huey | `>=2.5,<3` | worker import、真实 Redis broker 和后台消费必须可验证 |
| Loguru | `>=0.7,<0.8` | 后端和 smoke 脚本统一日志入口；CLI JSON 输出必须保持 stdout 纯 JSON |
| PyGithub | `>=2.6,<3` | 真实 GitHub/PAT smoke 覆盖认证、rate limit 和 code search |
| Requests | `>=2.32,<3` | health check 和 webhook 调用保持脱敏日志 |
| psutil | `>=7,<8` | pytest import 和运行时依赖保持可用 |
| tldextract | `>=5,<6` | `cache_dir` 兼容已验证 |
| Docker/Debian | `python:3.13-slim-trixie` | 默认使用宿主原生架构，必要时通过 `--platform` 或 `SKYRADAR_PLATFORM` 显式覆盖 |
| nginx | Debian Trixie 官方 nginx `1.26.3` | 独立 nginx service，负责静态资源和 `/api` 反向代理 |

当前保守策略：

- `deploy/pyenv/requirements.txt` 保留直接运行时依赖和当前 harness 需要的 PyYAML，移除 2018 年转移依赖硬 pin。
- FastAPI 固定到 `>=0.136,<0.137`；Uvicorn 固定到 `>=0.49,<0.50`；Gunicorn 固定到 `>=26,<27`。
- 后端运行时不依赖 Flask 或 Flask-RESTful；JSON 请求解析由 FastAPI route adapter 保持。
- PyMongo 保持 `>=4.11,<5` 以覆盖 Python 3.13；不兼容 API 已显式替换。
- PyGithub 2.x 推荐迁移到 `github.Auth`；当前切片不改 GitHub 业务逻辑，真实账号/PAT 验证后再决定是否补认证兼容层。
- Docker 构建使用阿里云 Debian Trixie 源，并删除基础镜像默认 `debian.sources`。
- 当前镜像使用 Debian 官方 nginx 包，不再依赖 OpenResty Bookworm 仓库。

## FastAPI 实现规则

FastAPI 的架构边界和 sync/async 原则维护在 `DESIGN.md`；本文只保留实现期执行规则：

- `api:app` 是 ASGI 入口，生产入口继续使用 Gunicorn + Uvicorn worker。
- `docs/api/openapi.yaml` 是人工审查契约源，不用 FastAPI 自动 OpenAPI 覆盖。
- 新增 route 必须保持薄适配层，业务逻辑进入同 domain service/repository/integration。
- 测试 monkeypatch 必须挂到 service/repository/integration 边界。
- 若为了满足 REST 契约绕开 FastAPI/Pydantic 默认行为，必须同步 `DESIGN.md`、`docs/api/openapi.yaml` 和契约测试。

## 文档维护规则

`docs/backend/` 只保留 9 个 Markdown 文件：

- `PLAN.md`：路线。
- `PROGRESS.md`：当前状态。
- `DECISIONS.md`：ADR。
- `DESIGN.md`：架构/设计规范。
- `IMPLEMENTATION_GUIDE.md`：实现规则。
- `TESTING.md`：测试策略。
- `CHECKLIST.md`：门禁。
- `RISKS.md`：风险。
- `REFERENCES.md`：参考。

`docs/api/openapi.yaml` 是 Swagger/OpenAPI 机器可读契约源，不算入后端 Markdown 文档架构。

更新规则：

- 完成一个后端切片后，更新 `PROGRESS.md`。
- API 行为变化时，更新 `DESIGN.md` 的契约语义、`docs/api/openapi.yaml` 和契约测试。
- 架构、目录、分层或 FastAPI 路线变化时，更新 `DESIGN.md` 或 `DECISIONS.md`。
- 测试范围或覆盖策略变化时，更新 `TESTING.md`。
- 开发命令、CI、部署、安全、依赖或 Agent 规则变化时，更新 `IMPLEMENTATION_GUIDE.md`。
- 发布门禁或切片完成条件变化时，更新 `CHECKLIST.md`。
- 新风险出现时，更新 `RISKS.md`。
- 新参考资料或外部工程经验需要保留时，更新 `REFERENCES.md`。

收敛规则：

- 不为本地开发、CI、运维、安全、依赖、API 契约或 FastAPI 维护新增独立文档，统一进入上述 9 个文件。
- 不为临时队伍分工、过程流水或一次性验证新增独立文档，结论进入 `PROGRESS.md`。
- 不在 `PLAN.md` 重复架构、命令、API 细节或风险清单。
- 不在 `TESTING.md` 重复完整命令矩阵，命令以 `IMPLEMENTATION_GUIDE.md` 为准。

## Agent 规则

后端改动前至少读取：

- `PLAN.md`
- `DESIGN.md`
- `IMPLEMENTATION_GUIDE.md`
- `TESTING.md`
- `PROGRESS.md`
- `CHECKLIST.md`
- `docs/api/openapi.yaml`

涉及前端依赖的 `/api/v1/*` 行为时，同时读取：

- `docs/frontend/IMPLEMENTATION_GUIDE.md`

任务规则：

- 不改业务代码，除非用户明确要求实现代码变更。
- 不把运行时、依赖、数据库 API、HTTP 框架和 Docker 拓扑变更揉成一个不可回滚的大切片。
- 修改 API 行为时同步 `docs/api/openapi.yaml`、契约测试、`DESIGN.md` 和前端 adapter。
- 修改 MongoDB 操作必须考虑 PyMongo 4。
- 修改 OpenAPI 时运行 schema 校验；若未配置，记录缺口。
- 完成一个后端切片后更新 `PROGRESS.md`。
