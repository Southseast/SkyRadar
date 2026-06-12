# SkyRadar

SkyRadar 是一个面向 GitHub Code Search 的代码泄露发现系统。它按规则周期性检索 GitHub 代码内容，记录命中结果，提供复核界面，并通过邮件或钉钉 webhook 发送通知。

- 产品名：SkyRadar
- 后端：FastAPI/ASGI + Gunicorn/Uvicorn + MongoDB + Redis + Huey
- 前端：React + Vite + TypeScript + Tailwind CSS + shadcn/ui
- 部署：Docker Compose 拆分 API、nginx、worker、Redis、MongoDB
- API 文档：`docs/api/openapi.yaml`，可通过 `/api/docs` 暴露 Swagger UI

## 目录

- [能力边界](#能力边界)
- [技术路线](#技术路线)
- [项目架构](#项目架构)
- [快速开始](#快速开始)
- [配置](#配置)
- [开发](#开发)
- [测试与验证](#测试与验证)
- [部署](#部署)
- [安全注意](#安全注意)
- [文档索引](#文档索引)

## 能力边界

SkyRadar 当前聚焦 GitHub Code Search 主线：

- 周期性执行 GitHub code search。
- 支持多 GitHub 账号/PAT 配置和搜索配额展示。
- 展示泄露结果、趋势统计、标签统计、详情代码片段和受影响资产。
- 支持结果状态处理：确认、误报、忽略、备注。
- 支持查询规则、任务周期、黑名单、通知邮箱、SMTP、钉钉 webhook 配置。
- 支持邮件和钉钉 webhook 通知。

不在当前主线内的能力：

- 不把 TruffleHog/Gitleaks 等重扫描器直接放进 API route。
- 不在 FastAPI 请求线程内执行长时间扫描。
- 不默认提供公网多租户、用户权限和审计系统。
- 不把 GitHub PAT、SMTP 密码或 webhook token 展示给前端。

## 技术路线

SkyRadar 的路线按“稳定主链路、增强治理、再扩展扫描源”的顺序推进。

| 阶段 | 目标 | 状态 |
| --- | --- | --- |
| P0 | FastAPI 后端、React 前端、Docker Compose 拆分部署、OpenAPI 契约和基础 smoke | 已落地 |
| P1 | GitHub Code Search 稳定性：rate limit、账号轮转、分页恢复、失败重试、去重 | 进行中 |
| P2 | Baseline 和误报治理：finding fingerprint、首次/最近发现、重复命中收敛 | 规划中 |
| P3 | Target/revision 模型：把 repo、branch、commit、gist 等扫描对象建模 | 规划中 |
| P4 | Event/webhook 增量扫描：GitHub Events 或 webhook 作为受控增量输入 | 规划中 |
| P5 | 高级扫描：GH Archive、force-push、外部 detector harness | 评估中 |

详细后端路线见 `docs/backend/PLAN.md`，前端路线见 `docs/frontend/PLAN.md`。

## 项目架构

```mermaid
flowchart LR
    user[Browser] --> nginx[nginx]
    nginx --> ui[React static assets]
    nginx --> api[FastAPI API]
    api --> mongo[(MongoDB)]
    api --> redis[(Redis)]
    api --> github[GitHub API]
    api --> notify[Mail / DingTalk]
    worker[Huey worker] --> redis
    worker --> mongo
    worker --> github
    worker --> notify
```

运行时拓扑：

- `nginx`：对外 HTTP 入口，服务 `client/dist`，并把 `/api` 反向代理到 API service。
- `skyradar`：FastAPI API service，监听容器内 `8888`。
- `worker`：Huey 后台任务消费者，负责周期任务和扫描任务。
- `redis`：Huey broker/cache。
- `mongo`：持久化配置、扫描结果和处理状态。

代码目录：

```text
client/
  src/components/      通用布局和 shadcn/ui 组件
  src/features/        按业务功能组织的前端组合组件
  src/lib/api/         类型化 API client 和兼容适配
  src/pages/           页面入口

server/
  api/                 FastAPI routes，按 domain 内聚
  core/                配置、数据库、响应、安全等基础边界
  integrations/        GitHub、邮件、webhook 等外部系统适配
  workers/             Huey worker、调度和后台任务
  tests/               跨 domain 的后端 smoke/contract 测试

deploy/
  nginx/               nginx 站点配置
  supervisor/          容器内进程编排配置
  pyenv/               Python 运行和测试依赖

docs/
  api/openapi.yaml     OpenAPI 契约源
  backend/             后端路线、设计、测试、门禁和风险
  frontend/            前端路线、设计、测试、门禁和风险
```

## 快速开始

推荐用 Docker Compose 启动完整拓扑。

```bash
docker compose up --build -d
```

默认访问：

- 前端：`http://127.0.0.1/`
- 健康检查：`http://127.0.0.1/api/health`

停止：

```bash
docker compose down
```

修改对外端口：

```bash
SKYRADAR_HTTP_PORT=8080 docker compose up --build -d
```

启用 Swagger UI：

```bash
SKYRADAR_API_DOCS_ENABLED=1 docker compose up --build -d
```

启用后访问：

- Swagger UI：`http://127.0.0.1/api/docs`
- OpenAPI JSON：`http://127.0.0.1/api/openapi.json`

## 配置

常用环境变量：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `MONGODB_URI` | `mongodb://mongo:27017` | MongoDB 连接地址 |
| `MONGODB_DATABASE` | `skyradar` | MongoDB database |
| `MONGODB_AUTH_SOURCE` | `skyradar` | MongoDB 认证库 |
| `REDIS_HOST` | `redis` | Redis host |
| `REDIS_PORT` | `6379` | Redis port |
| `SKYRADAR_HTTP_PORT` | `80` | Compose nginx 对外端口 |
| `SKYRADAR_IMAGE` | `skyradar:latest` | Compose 构建/运行镜像名 |
| `SKYRADAR_MONGO_IMAGE` | `mongo:8.2.7` | Compose MongoDB 镜像 |
| `SKYRADAR_API_DOCS_ENABLED` | `false` | 是否启用 `/api/docs` |
| `SKYRADAR_OPENAPI_PATH` | `docs/api/openapi.yaml` | OpenAPI 契约文件路径 |
| `SKYRADAR_BASIC_AUTH_USERNAME` | 空 | nginx Basic Auth 用户名 |
| `SKYRADAR_BASIC_AUTH_PASSWORD` | 空 | nginx Basic Auth 密码 |

Basic Auth 必须同时设置用户名和密码：

```bash
SKYRADAR_BASIC_AUTH_USERNAME=admin \
SKYRADAR_BASIC_AUTH_PASSWORD='change-me' \
docker compose up --build -d
```

GitHub PAT 建议使用 Fine-grained PAT：

- 只检索公开仓库：通常不需要额外 repository permission。
- 需要检索私有或组织仓库：只给目标仓库 `Contents: Read-only`。
- 不要授予写权限，例如 `Contents: Write`、`Administration`、`Actions`、`Secrets`。
- 建议使用短期 token，并按部署环境最小化仓库范围。
- 如果组织启用了 SSO/SAML，需要对 token 做组织授权。

钉钉 webhook 示例：

```json
{
  "webhook": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
  "domain": "https://your-skyradar.example",
  "enabled": true
}
```

`domain` 会用于告警消息中的结果页链接。

## 开发

前端开发：

```bash
cd client
npm install
npm run dev
```

Vite dev server 已配置 `/api` 代理到 `http://127.0.0.1:8888`。

后端本地开发需要先提供本机可访问的 MongoDB 和 Redis，再运行 API：

```bash
cd server
MONGODB_URI=mongodb://127.0.0.1:27017 \
REDIS_HOST=127.0.0.1 \
uv run --no-project --python 3.13 \
  --with-requirements ../deploy/pyenv/requirements-dev.txt \
  gunicorn -w 2 -k uvicorn.workers.UvicornWorker -b 127.0.0.1:8888 api:app
```

后台 worker：

```bash
cd server
MONGODB_URI=mongodb://127.0.0.1:27017 \
REDIS_HOST=127.0.0.1 \
uv run --no-project --python 3.13 \
  --with-requirements ../deploy/pyenv/requirements-dev.txt \
  huey_consumer.py workers.huey_app.huey
```

## 测试与验证

前端检查：

```bash
cd client
npm run check
```

后端单测：

```bash
uv run --no-project --python 3.13 \
  --with-requirements deploy/pyenv/requirements-dev.txt \
  pytest
```

后端契约检查：

```bash
uv run --no-project --python 3.13 \
  --with-requirements deploy/pyenv/requirements-dev.txt \
  python scripts/backend_openapi_check.py

uv run --no-project --python 3.13 \
  --with-requirements deploy/pyenv/requirements-dev.txt \
  python scripts/backend_route_coverage.py
```

Docker Compose smoke：

```bash
uv run --no-project --python 3.13 \
  --with-requirements deploy/pyenv/requirements-dev.txt \
  python scripts/backend_compose_smoke.py --fresh-volumes
```

## 部署

默认拆分拓扑：

```bash
docker compose up --build -d
```

短期单容器兼容模式：

```bash
docker compose --profile all-in-one up --build -d skyradar-all-in-one mongo
```

构建镜像：

```bash
docker build -t skyradar .
```

使用外部 MongoDB：

```bash
docker run -d \
  --name skyradar \
  -p 80:80 \
  -e MONGODB_URI=mongodb://username:password@host:27017/skyradar \
  skyradar
```

## 安全注意

- `/api/*` 当前没有应用级登录态。部署到不可信网络前，应至少启用 nginx Basic Auth，并配合 HTTPS、VPN、内网或可信反向代理。
- GitHub PAT、SMTP 密码和 webhook token 都属于敏感配置，避免在日志、截图、Issue 或聊天记录中暴露。
- `POST /api/setting/github` 不应向页面回显原始 token；前端 adapter 会在边界删除 `password` 字段，后端也应保持敏感字段不回显。
- MongoDB、Redis 和 Docker 基础镜像升级后，需要在目标部署环境复验 `/api/health`、worker 消费和通知链路。

## 文档索引

后端：

- `docs/backend/PLAN.md`：路线
- `docs/backend/PROGRESS.md`：当前状态
- `docs/backend/DESIGN.md`：架构和 domain 边界
- `docs/backend/IMPLEMENTATION_GUIDE.md`：实现规则
- `docs/backend/TESTING.md`：测试策略
- `docs/backend/CHECKLIST.md`：门禁
- `docs/backend/RISKS.md`：风险
- `docs/backend/DECISIONS.md`：ADR
- `docs/backend/REFERENCES.md`：参考资料

前端：

- `docs/frontend/PLAN.md`：路线
- `docs/frontend/PROGRESS.md`：当前状态
- `docs/frontend/DESIGN.md`：产品气质和 UI 规范
- `docs/frontend/IMPLEMENTATION_GUIDE.md`：实现规则
- `docs/frontend/TESTING.md`：测试策略
- `docs/frontend/CHECKLIST.md`：门禁
- `docs/frontend/RISKS.md`：风险
- `docs/frontend/DECISIONS.md`：ADR
- `docs/frontend/REFERENCES.md`：参考资料

## 许可证

AGPLv3。详见 `LICENSE`。
