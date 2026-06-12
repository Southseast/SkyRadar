# 后端参考资料

职责：本文只记录后端可参考的官方文档、GitHub 工程和对 SkyRadar 的适配性结论。

职责边界：

- 本文提供外部参考和借鉴判断，不作为项目规范源。
- 已采纳的长期决策写入 `DECISIONS.md`，当前架构规范写入 `DESIGN.md`。
- 后续路线只以 `PLAN.md` 为准；本文的参考项目启发不能单独视为承诺。
- 命令、CI、部署和测试规则不在本文维护。

## 官方文档

- Python 版本状态：<https://devguide.python.org/versions/>
- Flask 安装要求：<https://flask.palletsprojects.com/en/stable/installation/>
- Gunicorn 安装要求：<https://docs.gunicorn.org/en/stable/install.html>
- PyMongo 4 迁移指南：<https://pymongo.readthedocs.io/en/stable/migrate-to-pymongo4.html>
- FastAPI 版本策略：<https://fastapi.tiangolo.com/deployment/versions/>
- FastAPI WSGI 挂载：<https://fastapi.tiangolo.com/advanced/wsgi/>

## GitHub 工程参考

### fastapi/full-stack-fastapi-template

地址：<https://github.com/fastapi/full-stack-fastapi-template>

可借鉴：

- 完整工程 harness：`backend/`、`frontend/`、`scripts/`、`.github/`、compose、开发和部署文档。
- Docker Compose 组织本地开发和生产相近环境。
- `pyproject.toml`、`uv.lock`、CI、coverage、部署文档和环境变量模板。

对 SkyRadar 的启发：

- 后端应有文档、脚本、CI 和 compose，而不是只改 Dockerfile。
- 本地环境应逐步从单容器 supervisor 过渡到 api、worker、redis、mongo、nginx 分开验证。

不直接照搬：

- 模板围绕 PostgreSQL/SQLModel，不适合直接套用到当前 MongoDB 数据模型。
- 认证和用户体系不是后端第一阶段目标。

### zhanymkanov/fastapi-best-practices

地址：<https://github.com/zhanymkanov/fastapi-best-practices>

可借鉴：

- 按 domain/bounded context 组织目录。
- 每个 domain 下放 route、schema、service、repository、dependencies、tests 等边界。
- 明确 sync/async 规则：阻塞 I/O 不应放进 `async def`。
- 用 Agent 规则沉淀工程约束。

对 SkyRadar 的启发：

- 当前后端可按 `results`、`settings`、`statistics`、`health`、`github_search`、`notifications` 拆 domain。
- 当前 PyGithub、PyMongo、Requests、smtplib、Huey 都是同步逻辑；即使后续迁 FastAPI，也不盲目改 `async def`。

### ivan-borovets/fastapi-clean-example

地址：<https://github.com/ivan-borovets/fastapi-clean-example>

可借鉴：

- 业务核心不依赖框架、数据库、broker、云 SDK 等外部实现。
- service/repository 边界降低框架切换成本。
- tests、scripts、workflow、Makefile、pyproject 等配套 harness。

不直接照搬：

- 完整 Clean Architecture、DDD、CQRS 对当前 SkyRadar 过重。

### Netflix Dispatch

地址：

- GitHub：<https://github.com/Netflix/dispatch>
- 文档：<https://netflix.github.io/dispatch/docs/administration/contributing/core>

可借鉴：

- 生产级 Python/FastAPI 项目组织。
- 贡献规范要求测试、格式和 lint。
- API 和 UI 按业务模型组织文件。

### Schemathesis

地址：<https://github.com/schemathesis/schemathesis>

可借鉴：

- 从 OpenAPI schema 生成契约测试。
- 检查 500、schema mismatch、无效输入、响应不符合客户端预期。

对 SkyRadar 的启发：

- 建立 `docs/api/openapi.yaml` 后，可新增轻量 Schemathesis smoke。
- 第一批只覆盖只读接口，避免 POST/PATCH/DELETE 改数据或发通知。

## GitHub 泄露监控工程参考

### duo-labs/secret-bridge

地址：<https://github.com/duo-labs/secret-bridge>

GitHub 扫描方式：

- 通过 GitHub Events API 轮询 organization、user 或 repository 的事件，或通过 GitHub webhook 接收 push 事件。
- 只处理 push 类事件；首次遇到仓库时 clone 仓库并建立 baseline。
- 后续 push 到来后，对 commit checkout，并对变更文件执行 detector。
- detector 不自己重新发明规则引擎，而是包装 `detect-secrets`、`git-secrets` 和 `trufflehog`。
- 新 findings 与 baseline/历史 findings 做差集，只通知新增泄露。

对 SkyRadar 的启发：

- 当前 GitHub Code Search 主线可以继续保留；后续增强可增加 event/webhook 增量扫描模式。
- 借鉴 baseline 和差集去重，减少重复告警。
- detector 设计可插件化，先接入成熟工具输出，再映射为 SkyRadar 统一 result shape。

### SAP/credential-digger

地址：<https://github.com/SAP/credential-digger>

GitHub 扫描方式：

- 支持扫描单个 Git repository、GitHub user/org repositories、pull request、wiki、local repo 和文件目录。
- `scan_user` 使用 PyGithub 枚举用户或组织仓库，再逐仓 clone 扫描；可选择是否扫描 fork。
- `scan_pr` 使用 GitHub API 获取 PR commits 和 patch 内容后扫描。
- 核心检测是规则库 + Hyperscan；结果写入 DB，并记录 repo 的 last scan timestamp。
- 可接入机器学习模型或相似度模型降低 false positive。

对 SkyRadar 的启发：

- 将查询命中后的“结果状态”和“误报治理”建成显式流程，而不是只保存搜索结果。
- 后续如果从 Code Search 扩展到 clone/history scan，应记录 repo scan timestamp，支持增量重扫。
- 规则库、命中状态、人工复核状态和 false positive 相似度归并值得单独设计。

### Zomato/vinifera

地址：<https://github.com/Zomato/vinifera>

GitHub 扫描方式：

- 使用 Octokit 调 GitHub API，同步 organization users、user repositories、gists 和 user activity。
- 将 repo、gist、fork、branch 建成 target；将 commit/gist revision 建成 revision。
- monitor 发现新 revision 后投递 Sidekiq worker。
- worker 调 Gitleaks Docker image 扫描 repo、commit 或 file，并处理结果。
- 通过 throttling、retry 和 Slack notification 控制 GitHub API 和扫描任务。

对 SkyRadar 的启发：

- 后续可以引入 target/revision 模型，把 repo、gist、commit 等扫描对象从“搜索结果”中独立出来。
- 扫描任务适合继续放在 Huey worker，保持 API 和扫描执行分离。
- 复杂扫描器应容器隔离或进程隔离，避免阻塞主 API/worker。

### trufflesecurity/force-push-scanner

地址：<https://github.com/trufflesecurity/force-push-scanner>

GitHub 扫描方式：

- 不走 GitHub Code Search；数据来源是 GH Archive 衍生的 force-push 数据集，支持 SQLite/CSV 输入。
- 重点扫描 zero-commit force push，因为它常见于“提交 secret 后强推删除”的场景。
- 对目标 repo 执行 blobless/no-checkout clone。
- fetch 被覆盖的 commit，识别 base commit，再用 TruffleHog 扫描被覆盖提交。
- 优先输出 verified findings。

对 SkyRadar 的启发：

- GH Archive / force-push 是 Code Search 之外的高级增强源，适合作为后续独立切片。
- 该能力不应混入当前 GitHub Code Search 主线，应以单独 worker/harness 验证。

### Rsansan/leak_monitor

地址：<https://github.com/Rsansan/leak_monitor>

GitHub 扫描方式：

- 使用 PyGithub `search_code` 按关键词搜索 GitHub 代码。
- 对搜索结果读取 repository/path/content，再结合公司关键词做敏感信息判断。
- 命中后写入 SQLite，生成 Excel/HTML 报告，并可推送钉钉。
- 同时覆盖百度文档、CSDN、博客园、Bing 和网盘等多平台。

对 SkyRadar 的启发：

- 与 SkyRadar 当前 GitHub Code Search 主线最接近，可参考多平台监控和报告输出。
- GitHub 部分较轻量，SkyRadar 应继续加强 rate limit、去重、失败重试和结果复核。

## 本项目适用结论

- 当前 HTTP 主入口采用 FastAPI/ASGI，历史契约由 OpenAPI 和契约测试保护。
- 文档和脚本收敛为少量稳定入口，不继续扩散主题文档。
- 后端 domain 拆分应服务可测试性，不引入过重架构。
- 后续 FastAPI/service 拆分必须以同 URL、同 response、同契约测试为验收。
- OpenAPI 是契约源，不只是 Swagger 页面。
- GitHub 泄露监控继续以 Code Search 为主线；后续增强按 baseline/误报治理、target/revision、event/webhook 增量扫描和 GH Archive force-push 扫描分阶段推进。

## 适配性复核

当前 SkyRadar 已经具备的 GitHub 扫描链路是：

1. Huey 定时任务读取启用的 query 和 page 配置。
2. `github_search.service` 使用 PyGithub `search_code()` 执行 GitHub Code Search。
3. 账号池记录 search rate limit，并在异常时尝试切换账号重排任务。
4. 搜索结果按 GitHub blob sha、project/path/security 和 ignore 状态去重。
5. 命中内容提取 domain、email、ip 等影响资产。
6. 结果写入 MongoDB，并触发邮件和 webhook 通知。

因此，参考项目的可借鉴性不是“是否能替代 SkyRadar”，而是“是否补足当前扫描链路的明确缺口”。

| 参考方向 | 对应项目 | SkyRadar 现状 | 借鉴价值 | 优先级 |
| --- | --- | --- | --- | --- |
| Code Search 主线加固 | `Rsansan/leak_monitor` | 已有 PyGithub Code Search、账号池、Mongo 去重和通知 | 与 SkyRadar 当前 Code Search 模式最接近，可作为低成本关键词搜索和报告链路参考；SkyRadar 应补分页 checkpoint、限流恢复、搜索失败重试和更清晰的去重策略 | P0 |
| baseline/差集去重 | `duo-labs/secret-bridge` | 只有 `_id=sha`、project/path/security 和 ignore 级去重 | 可减少同一命中反复通知；适合先以 fingerprint、first_seen、last_seen、occurrence_count 落地 | P1 |
| 误报治理状态 | `SAP/credential-digger` | 已有 `security`、`ignore`、`desc`，但不是完整 finding 状态机 | 可演进为 confirmed、false_positive、dismissed、triaged 等状态；先做契约和数据迁移，不直接引入 ML | P1 |
| target/revision 模型 | `Zomato/vinifera` | repo、path、commit 只是 result 字段，不是独立扫描对象 | 后续支持 repo/gist/branch/commit 增量扫描的前置模型；适合新增 `targets`、`target_revisions`、`scan_runs` | P2 |
| event/webhook 增量扫描 | `duo-labs/secret-bridge` | 当前靠定时 Code Search，不接 GitHub push 事件 | 适合受控 org/repo 的近实时扫描；必须等 target/revision 基础模型后推进 | P2 |
| detector 插件化 | `secret-bridge`、`vinifera`、`credential-digger` | 当前主要依赖 GitHub 查询命中和资产提取，没有外部 detector 输出映射层 | 可为 Gitleaks/TruffleHog/detect-secrets 预留统一 finding mapper；暂不直接跑重扫描 | P2 |
| GH Archive force-push | `trufflesecurity/force-push-scanner` | 当前只能看到 GitHub Code Search 可见内容 | 能补“提交 secret 后强推删除”的盲区；工程成本高，应作为独立 worker/harness 和可选外部数据源 | P3 |

确认值得借鉴的判断：

- P0/P1 项直接补当前 SkyRadar 已有链路的短板，不改变主架构，值得近期作为独立切片评估和落地。
- P2 项是后续从“关键词搜索器”升级到“GitHub 泄露监控平台”的结构基础，值得规划但不应抢在 Code Search 加固之前。
- P3 项能覆盖 Code Search 的天然盲区，但依赖 GH Archive、git clone/fetch 和 TruffleHog，必须独立切片，不能混入当前搜索 worker。
- 不建议照搬任何一个项目的整体架构；SkyRadar 应保留 FastAPI + MongoDB + Redis/Huey + domain service/repository 的现有边界。
