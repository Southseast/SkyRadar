# 后端风险登记

职责：本文只记录当前后端的已知风险、影响、状态和缓解方向。

职责边界：

- 本文不记录当前进度或某次验证结果；这些写入 `PROGRESS.md`。
- 本文不维护命令、CI、部署步骤或完整门禁；这些写入 `IMPLEMENTATION_GUIDE.md` 和 `CHECKLIST.md`。
- 本文不复制 API 兼容语义、架构规则或测试策略；这些分别写入 `DESIGN.md` 和 `TESTING.md`。
- 已缓解风险仍可保留为防回归风险，但实现细节只保留摘要。

## R001 - 后端 API 无应用级鉴权

状态：已选择部署层缓解方案，保留应用级鉴权缺口

描述：当前 `/api/v1/*` 没有应用级鉴权，依赖部署网络边界、反向代理、VPN 或内网访问控制。

影响：如果服务暴露到不可信网络，攻击者可能查看泄露结果、修改规则、删除配置或触发通知。

缓解：

- Swagger/OpenAPI 文档入口生产默认关闭。
- 生产必须通过网络边界或反向代理认证限制访问。
- 当前按 ADR-0008 使用 nginx Basic Auth 保护页面和 `/api` 入口。
- 公网或不可信网络必须叠加 HTTPS、VPN、防火墙或上游认证网关。
- 如未来需要多用户、审计或细粒度权限，再新增应用层用户体系 ADR。

## R002 - 运行时基线回退风险

状态：已缓解，保留防回归风险

描述：当前默认镜像基线为 Python 3.13 + Debian Trixie。后续 Dockerfile、CI 或回退镜像不得切回 EOL Python 或 EOL Debian。

影响：如果运行时基线回退到 EOL 版本，安全更新、依赖安装和镜像构建稳定性会退化。

缓解：

- 默认运行环境保持 Python 3.13 + Debian Trixie。
- Docker/Ops 门禁禁止把 EOL Python 或 EOL Debian 作为目标运行环境。
- 依赖和 compose smoke 继续记录 Python、Debian、nginx、MongoDB 和 Redis 实际版本。

## R003 - PyMongo 旧 API 阻塞升级

状态：已缓解，保留防回归风险

描述：当前运行代码使用 PyMongo 4 兼容写法。后续新增 MongoDB 代码如果误用 `count()`、`save()`、`update()`、`db.authenticate()`、`db.last_status()` 等 API，会重新引入兼容风险。

影响：如果后续新增或回退旧 API，PyMongo 4、MongoDB 8.x 或 health check 仍可能运行时失败。

缓解：

- 新代码不得新增旧 PyMongo API。
- 健康检查使用 `ping` 替代 `last_status()`。
- Mongo 查询、分页、upsert、replace 和聚合继续放入 repository/helper。
- 继续用 MongoDB 8 smoke 和 contract tests 防回归。

## R004 - REST API 契约容易被重构破坏

状态：已知风险

描述：当前 API 以 `/api/v1/*`、标准 HTTP status、`data/meta/links` 成功 envelope 和 `error/message/detail/request_id` 错误 envelope 作为最终契约。重构 route、schema 或 adapter 时容易让 OpenAPI、runtime 和前端解析发生漂移。

影响：契约漂移会导致前端请求失败、错误处理误判、分页或删除语义不一致。

缓解：

- 保持 `DESIGN.md` 的 REST 语义和 `docs/api/openapi.yaml` 为契约源。
- FastAPI TestClient 契约测试覆盖当前 response shape。
- API 或 route 变更必须通过 OpenAPI route coverage、Schemathesis 只读 smoke 和 compose smoke。

## R005 - 敏感字段回传和日志泄露

状态：已缓解，保留防回归风险

描述：GitHub password、SMTP password 和 webhook 敏感 query 参数已按契约脱敏；Mongo URI、Redis secret、泄露代码和内部资产仍需防止进入日志、OpenAPI 示例或测试快照。

影响：凭据、webhook、泄露代码或内部资产可能二次泄露。

缓解：

- 正式 schema 不包含 GitHub `password`。
- 测试、日志和 OpenAPI 示例必须脱敏。
- 后端 response 过滤已补契约测试；后续新增设置项或通知集成时继续先写脱敏契约。
- OpenAPI 示例和描述文本继续由 `backend_openapi_secret_scan.py` 扫描。

## R006 - FastAPI 重写扩大回归面

状态：已缓解，保留后续外部依赖 fixture 和远端 CI 回填风险

描述：后端 HTTP 入口已切到 FastAPI/ASGI，domain routes、service/repository/integration 分层和 worker 业务下沉已完成，Flask、Flask-RESTful、`reqparse` 和旧 `controllers/*` 兼容导出层已移除。后续继续强化 GitHub/SMTP/webhook fixture 或调整 domain 内聚时仍可能触及历史契约。

影响：大量历史协议和 worker 交互可能回归，且回滚困难。

缓解：

- 后续 GitHub/SMTP/webhook fixture 和 domain 内聚按独立切片推进。
- Redis client、Debian 和 Node 升级已作为独立切片完成；后续相关变更仍不得混入 FastAPI/domain 重构切片。
- 同步 SDK 调用保持普通 `def` route 或受控线程池。

## R007 - Worker 和外部通知副作用难以测试

状态：已知风险

描述：Huey task 当前混合 GitHub 搜索、MongoDB 写入、资产提取、SMTP 和 webhook 通知。

影响：测试容易误发通知、访问真实 GitHub 或污染生产数据。

缓解：

- worker 调用 service，外部依赖通过 integration 层隔离。
- 默认 mock GitHub、SMTP、webhook 和 MongoDB。
- 真实 smoke 使用专用低权限 PAT 和本地 fake webhook。

## R008 - MongoDB latest tag 漂移

状态：已缓解，保留显式 latest 覆盖风险

描述：当前 compose 默认 MongoDB 镜像已从 mutable `latest` 固定到 `mongo:8.2.7`。`latest` 仍可通过 `SKYRADAR_MONGO_IMAGE` 显式覆盖用于开发探索。

影响：CI、问题复现、宿主 kernel 兼容性、PyMongo 行为和 MongoDB feature compatibility 判断可能随时间漂移。此前 `public.ecr.aws/docker/library/mongo:8.0` 已在当前 Docker/Linux kernel 6.19+ 环境触发 `SERVER-121912` 启动失败，说明固定版本也必须经过当前环境 smoke。

缓解：

- `latest` 只作为开发探索或显式 smoke 输入，不作为长期稳定基线。
- 当前默认 tag 使用已验证的 MongoDB `8.2.7`。
- CI、发布 smoke 和可复现问题定位使用固定 tag。
- 涉及保留数据时不得沿用 fresh volume 结论，必须补备份、恢复、FCV、索引和回滚路径。

## R009 - Redis 内嵌在后端容器导致生命周期耦合

状态：已缓解，保留固定版本和运维收敛风险

描述：当前 compose 已拆出独立 Redis service，Web 和 Worker 通过 `REDIS_HOST=redis`、`REDIS_PORT=6379` 访问。`skyradar-all-in-one` profile 仍保留内嵌 Redis 作为短期兼容/回滚路径。

影响：默认拆分拓扑已解决 Web、Worker、Redis 生命周期耦合；剩余风险在于 Redis 持久化策略、队列积压监控和兼容 profile 被误用于稳定环境。

缓解：

- Web 和 Worker 统一通过 `REDIS_HOST=redis`、`REDIS_PORT=6379` 或等价配置访问 Redis。
- Redis service 默认复用项目镜像内 Debian Trixie `redis-server`，并以无持久化模式运行，记录 `redis-server --version`，避免 CI 额外拉取 Redis 镜像触发 registry rate limit，也避免读取旧 Redis 8.6 AOF/RDB 后因格式版本不兼容启动失败。
- 用 compose smoke 和真实 Redis/Huey 后台消费 smoke 证明 broker、worker 和任务链路可用。
- 保留 all-in-one profile 作为短期回滚路径，但 CI/发布默认使用拆分拓扑。

## R010 - API/Worker/nginx 拆分可能改变任务和代理语义

状态：已缓解，保留配置一致性和代理路径风险

描述：当前 compose 已拆出 API service、Worker service 和 nginx service。`skyradar` role 只运行 Gunicorn/FastAPI，`worker` role 运行 Huey consumer，`nginx` role 负责静态资源和 `/api` 反向代理。

影响：环境变量遗漏、工作目录差异、Python path 差异、MongoDB/Redis 网络名变化、nginx upstream 错误或日志路径变化，仍可能导致任务无法消费、重复消费、通知不发送、API 与 worker 看到不同配置，或静态资源和 `/api` 反向代理不可用。

缓解：

- API 和 Worker 使用同一组业务配置来源，至少包括 `MONGODB_URI`、`REDIS_HOST`、`REDIS_PORT`、GitHub、SMTP 和 webhook 配置。
- Worker/nginx 拆分切片必须跑 import smoke、真实 Redis/Huey 消费 smoke、compose 级别 HTTP smoke、静态首页 smoke 和 nginx 配置检查。
- `depends_on` 不能作为可用性证明，必须以真实请求和真实任务消费结果为准。
- nginx 独立 service 使用 `SKYRADAR_NGINX_UPSTREAM=skyradar:8888`；all-in-one profile 默认 upstream 为 `127.0.0.1:8888`。
- compose smoke 覆盖独立 nginx service health、静态首页、`/api/v1/health` 反向代理、`nginx -t` 和 `/var/log/nginx` 可写检查。
- 拆分失败时回退到 `skyradar-all-in-one` profile，且避免和默认 `nginx` service 同时占用 HTTP 端口。

## R011 - compose smoke 需要持续接入 CI

状态：已缓解，保留拓扑变更后远端 CI 回填风险

描述：当前已新增 `scripts/backend_compose_smoke.py`，把 compose fresh volume、service health、MongoDB 版本/ping/CRUD、Redis ping/version、nginx 静态资源和 `/api` 反代、真实请求和 worker 真实任务消费串成一个标准命令。

影响：如果远端 CI 未实际跑通或未定期运行，仍可能漏掉环境差异、worker 消费异常、日志异常或 secret 泄露检查，导致“本地通过”无法稳定复现。

缓解：

- `backend-compose-smoke` 覆盖 `down -v`、`up -d --build`、service health、`/api/v1/health`、静态首页、nginx 配置和日志路径、MongoDB `ping/CRUD`、Redis ping/version 和 worker 真实任务消费。
- 已新增 `.github/workflows/backend.yml` 接入 CI；拓扑变更提交推送后需回填新的远端运行结果。
- `PROGRESS.md` 必须区分“已运行单项 smoke”和“已运行完整 compose smoke”。
- 每次运行拓扑变更都必须在最终汇报里列出完整 compose smoke 结果和未覆盖项。

## R012 - 文档和实现状态混淆

状态：已知风险

描述：后端 harness 同时包含目标命令、人工步骤、本地 smoke 和远端 CI。文档如果没有清楚区分“已运行”“待运行”和“目标命令”，会误导发布判断。

影响：如果把目标命令、人工步骤或未落地 CI 写成已运行，会误导发布判断。

缓解：

- `PROGRESS.md` 明确记录未运行项。
- 未配置或未脚本化命令只能写“目标命令/待实现”。
- 完成实现切片后再更新验证状态。
