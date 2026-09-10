# 后端工程路线

职责：本文只记录后端后续路线、阶段目标和明确不做事项。

职责边界：

- 当前状态和最近验证写入 `PROGRESS.md`，不在本文重复维护。
- 架构、domain 边界、API 兼容语义写入 `DESIGN.md`，不在本文展开。
- 命令、配置、CI、部署和 Agent 规则写入 `IMPLEMENTATION_GUIDE.md`。
- 测试策略、发布门禁、风险和参考资料分别写入 `TESTING.md`、`CHECKLIST.md`、`RISKS.md`、`REFERENCES.md`。
- 本文可以引用这些文档，但不复制其中的事实清单。

## 近期目标

1. 回填最新远端 GitHub Actions `backend` 运行结果。
2. 持续维护 architecture guard，防止 route/worker 变胖或业务回流到全局工具层。
3. 优先推进 GitHub Code Search 加固和 baseline/误报治理。
4. 推进 OpenAI SDK 驱动的泄露简析能力，保持扫描保存和通知链路非阻塞。
5. 如需要公网或多人使用，再单独设计应用层用户、审计和权限。

## GitHub 扫描能力路线

当前主线继续使用 GitHub Code Search：按配置关键词查询，读取命中文件元数据和必要内容，写入结果并触发通知。后续增强按独立切片推进，不一次性引入大型扫描平台。

### P0 - Code Search 加固

目标：

- 强化 rate limit 处理、账号轮转、分页恢复、失败重试和重复结果去重。
- 保持 GitHub/PAT live smoke 作为受控外部链路验证。
- 结果继续落在 `github_search`、`results` 和 `notifications` domain 边界内。

验收：

- 分页 checkpoint 可恢复。
- rate limit 降级可观测。
- 失败任务可重试。
- 重复命中不会重复告警。

### P1 - Baseline 和误报治理

目标：

- 增加 finding fingerprint、首次发现、最近发现、出现次数和人工复核状态。
- 支持 false positive、confirmed、ignored 等 triage 状态。
- 避免同一命中反复通知。

建议字段：

- `fingerprint`
- `first_seen`
- `last_seen`
- `occurrence_count`
- `triage_state`
- `dismiss_reason`

验收：

- 新增状态不破坏 `/api/v1/*` REST response envelope。
- 重复 finding 只更新内部字段。
- 列表筛选继续使用显式 REST query 参数，不恢复 JSON 字符串过滤。

### P1.5 - OpenAI 泄露简析

目标：

- 新增 OpenAI/AI 分析全局配置，支持 DB 保存、接口脱敏和环境变量兜底。
- 查询规则新增 `analysis_enabled`，默认关闭；只有开启的规则命中并保存结果后才投递分析任务。
- GitHub 扫描先保存结果并照常触发通知，AI 分析通过独立 Huey 任务异步执行，失败不影响扫描保存和通知。
- 每条结果保存 `ai_analysis` 附加状态，不自动修改 `security`、`ignore` 或 `desc`。
- 分析输入使用泄露元信息、受影响资产和全局受控代码片段窗口，不额外脱敏。
- 支持可选 `有用才推送 webhook` 模式：启用 AI 分析的规则先保存结果并等待 AI 判断，只有 `is_useful=true` 才推送 webhook。

建议配置：

- `enabled`
- `api_key` / `has_api_key` / `mask_api_key`
- `base_url`
- `model`
- `prompt`
- `max_context_lines`
- `max_context_chars`
- `timeout_seconds`
- `max_retries`
- `concurrency`

建议结果字段：

- `ai_analysis.status`: `pending`、`running`、`success`、`failed`、`skipped`
- `ai_analysis.risk_level`: `low`、`medium`、`high`、`unknown`
- `ai_analysis.summary`
- `ai_analysis.evidence`
- `ai_analysis.recommendation`
- `ai_analysis.false_positive_reason`
- `ai_analysis.model`
- `ai_analysis.analyzed_at`
- `ai_analysis.error`
- `ai_analysis.is_useful`
- `ai_analysis.usefulness_reason`
- `ai_analysis.matched_interests`

实施顺序：

1. 增加 OpenAI SDK 依赖和独立 integration wrapper，避免 route、worker 直接散落 SDK 调用。
2. 在 settings domain 增加 OpenAI 全局配置读写接口，并在查询规则中加入 `analysis_enabled`。
3. 在 AI analysis domain 中封装上下文截取、prompt 组装、结构化 JSON 校验、状态写回、超时、重试和全局并发控制。
4. 在 GitHub 扫描保存结果成功后按规则开关投递 Huey 分析任务；任务失败只写入 `ai_analysis.failed`，不影响扫描、保存和通知。
5. 在 results domain 增加单条重新分析接口，强制覆盖旧的 `ai_analysis` 状态并重新投递任务。
6. 同步 OpenAPI 契约、后端契约测试和 worker service 测试。

验收：

- OpenAI API Key 不从 GET 接口返回明文，不进入日志。
- 自定义 prompt 允许编辑，但后端必须追加结构化 JSON 输出约束。
- 模型返回非法 JSON 时标记 `failed`，不保存原始模型输出。
- 全局并发限制生效；达到 `concurrency` 时任务延后重试，不并发打爆 OpenAI。
- 详情页手动重新分析接口可投递单条重跑；第一版不做列表页批量重跑。
- 未配置 API Key、全局关闭或规则关闭时不得阻塞扫描结果保存。
- 开启 `有用才推送 webhook` 后，启用 AI 分析的规则不得在扫描阶段提前推送 webhook。

### P2 - Target/revision 模型

目标：

- 将 repo、gist、fork、branch 或其他扫描对象建成 target。
- 将 commit/gist revision 建成 revision。
- Huey worker 负责扫描调度，API 只负责配置、查询和状态展示。

验收：

- 新模型不影响现有 `/api/v1/leakages` 查询、结果处理和通知链路。
- 新 collection、索引和 API 边界先通过 ADR 确认。

### P3 - Event/webhook 增量扫描

目标：

- 通过 GitHub Events API 或 webhook 捕获 push 事件。
- 首轮只做受控仓库或组织，不替代 Code Search 主线。
- 先设计统一 finding mapper，再评估 Gitleaks、TruffleHog 或 detect-secrets 等 detector。

验收：

- 覆盖 webhook 签名校验、delivery 去重、push event 解析和本地 fixture smoke。
- 外部 detector 不进入 FastAPI route，只能在 worker/harness 边界中运行。

### P4 - GH Archive / force-push 高级扫描

目标：

- 独立评估 GH Archive force-push 数据源和 dangling commit 扫描。
- 第一阶段只允许离线 SQLite/CSV fixture，不把真实 GH Archive 查询作为必跑门禁。

验收：

- 离线 fixture 可复现 force-push 输入、clone/fetch 命令构造、finding 映射和超时/磁盘限制。
- 该能力必须独立 worker、独立 smoke、独立风险登记。

## 不做事项

- 不把 TruffleHog/Gitleaks 等重扫描直接塞进 FastAPI route。
- 不在当前切片引入完整 ML false-positive 平台。
- 不为了高级扫描破坏当前 settings、results 和 notification response shape。
- 不恢复 Flask、Flask-RESTful、`reqparse`、controller 兼容层、单文件 API 入口或集中式业务目录。
