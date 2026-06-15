# 实现指南

职责：本文是前端实现期操作规则的收敛入口，负责类型、状态、API adapter、错误处理、安全展示、依赖、本地开发、部署、CI、浏览器目标和文档维护规则。

职责边界：

- 产品气质、视觉规范、信息架构、组件原则和可访问性要求写入 `DESIGN.md`，本文只保留实现规则。
- 长期技术选择的理由写入 `DECISIONS.md`，本文只记录当前如何执行。
- 当前状态和真实验证结果写入 `PROGRESS.md`，本文只维护可复用命令和规则。
- 测试分层写入 `TESTING.md`，功能完成和发布门禁写入 `CHECKLIST.md`。
- 后续不要再为类型、状态、错误、安全、依赖、本地开发、CI 或部署等主题拆更多小文档；除非内容已经大到难以维护，否则统一补充到本文。

## 数据类型

当前前端使用 TypeScript。核心类型应集中定义在 `client/src/types/` 或相近的共享目录，不要在页面组件中重复声明。

优先定义以下类型：

- `Leakage`
- `LeakageInfo`
- `LeakageCode`
- `AffectedAsset`
- `GithubAccount`
- `QueryRule`
- `TaskSetting`
- `NoticeRecipient`
- `MailSetting`
- `WebhookSetting`
- `ApiResponse<T>`
- `PaginatedResponse<T>`

规则：

- 类型字段以后端 `docs/api/openapi.yaml`、本文件 API Client 规则和实际 adapter 契约为准。
- 后端可能缺失的可选字段必须标为可选。
- 不在页面中用 `any` 绕过不确定字段；先补类型或 adapter。
- API response adapter 负责把后端 REST 结构转成页面更容易消费的结构。

## 状态管理

默认不引入全局状态库，除非出现明确复杂度。

状态分层：

- URL 状态：分页、过滤、标签、语言、状态。
- Server state：后端 API 数据、加载状态、错误状态。
- 本地组件状态：表单输入、弹窗开关、临时 UI 状态。
- 派生状态：统计、筛选展示文案、badge 状态。

建议：

- 结果页分页和过滤必须同步到 URL query。
- 设置页表单状态优先放在局部组件中。
- 如果引入 TanStack Query，需要在 `DECISIONS.md` 记录原因。
- mutation 成功后应刷新相关查询或局部更新缓存。

## API Client

当前前端应通过统一 API client 访问后端。

要求：

- 所有 `/api/v1/*` 路径集中维护。
- 所有请求参数序列化集中处理。
- 所有 response shape 映射逻辑集中处理。
- 页面组件不直接拼接复杂 query。
- 页面组件不直接依赖 axios/fetch 的底层错误结构。
- 成功响应使用 `data/meta/links`；分页读取 `meta.page`、`meta.page_size` 和 `meta.total`。
- 错误响应使用 `error/message/detail/request_id`，页面优先展示 `message`。
- DELETE 成功使用 HTTP 204；adapter 必须转换为页面可消费的成功结果或同步迁移调用层。
- 写接口默认提交 JSON；前端优先使用当前 API client 的封装。
- 后端返回的 `password`、token、secret、完整 webhook URL 不得进入页面状态、日志或错误采集。
- 页面状态仍由 adapter 映射，避免组件直接依赖后端分页和错误细节。

建议目录：

```text
client/src/lib/api/
  endpoints.ts
  client.ts
  results.ts
  settings.ts
```

当前页面结构：

```text
client/src/
  App.tsx
  components/layout/AppShell.tsx
  components/ui/
  features/results/
  features/settings/
  lib/api/
  pages/
  types/api.ts
```

前端路由兼容：

- `/`：结果仪表盘和结果表格。
- `/view/leakage/:id`：泄露详情。
- `/setting`：设置页默认 tab。
- `/setting/:tab`：设置页指定 tab。
- `/?tag=...`：告警链接过滤入口。
- 设置 tab 的 URL 值由前端 adapter 维护；如未来重命名，必须保留旧值兼容。
- 结果筛选、分页和状态处理必须同步 URL query，便于刷新和分享。

结果接口：

- `GET /api/v1/leakages` 使用明确 query 字段：`security`、`ignored`、`reviewed`、`tag`、`language`、`page`、`page_size`。
- `GET /api/v1/leakages/{leakage_id}` 读取详情元信息，adapter 需要容忍缺失字段和空值。
- `PATCH /api/v1/leakages/{leakage_id}` 提交 `security`、`ignored`、`desc` 和可选 `project`。
- `GET /api/v1/leakages/{leakage_id}/code` 返回 `code` 和 `affect`，前端负责展示，并支持长行、空内容和解码失败状态。

统计和设置接口：

- `GET /api/v1/trends` 提供仪表盘总览和任务运行信息。
- `GET /api/v1/statistics` 使用 `by` 查询参数做 tag、language、security、ignore、project 等维度聚合，adapter 必须容忍空数组和未知语言。
- GitHub 设置响应不得把原始 `password` 存入页面状态；adapter 必须删除后端写入或删除响应中可能出现的 `password` 字段。
- Query 设置使用 `/api/v1/search-rules` 和 `/api/v1/search-rules/{tag}`；删除规则前端必须给出明确确认和反馈。
- Task schedule 使用 `/api/v1/task-schedules/current`；未配置时前端应展示默认值。
- SMTP `password` 只允许作为输入值提交，不得从响应写回页面状态。
- Webhook `POST` 和 webhook 测试请求必须提交 `secret`；Webhook `GET` 返回掩码 URL、稳定 `id` 和 `has_secret`，删除 webhook 时使用 `id`，避免携带完整 URL。
- 前端不得展示完整 `access_token`、`sign`、`signature`、`timestamp`、`secret`、`token`。

健康检查：

- `GET /api/v1/health` 使用标准 `data` 成功响应。
- `data` 包含 `api`、`mongodb` 和 `redis` 子项；健康检查不依赖 GitHub 外部网络探测。
- 发布门禁不能只看 HTTP 200，还必须检查子项是否符合当前后端预期。

## 错误处理

错误展示应统一、明确、靠近用户正在执行的任务。

规则：

- 网络错误显示可理解的错误信息。
- 后端错误体优先展示 `message`，并保留 `error` 机器码供 adapter 或表单字段映射使用。
- 表单错误显示在字段附近。
- 页面级错误提供重试或返回操作。
- 空数据不是错误，应使用 empty state。
- 不把完整敏感 response 打到 console。

状态区分：

- loading：请求中。
- empty：请求成功但无数据。
- error：请求失败或数据不可用。
- success：用户操作成功。

## 安全和敏感信息展示

SkyRadar 会处理开源项目匹配内容和凭据配置，前端不能扩大敏感信息暴露面。

规则：

- GitHub token/password 只展示后端返回的脱敏字段。
- SMTP password 不在 UI 中明文展示。
- 不把敏感字段写入 console。
- 外链 `target="_blank"` 必须带 `rel="noreferrer noopener"`。
- 展示泄露代码时按文本处理，不使用 `dangerouslySetInnerHTML`。
- 从后端返回的链接用于跳转前，应保持最小信任，不做 HTML 注入。

## 依赖策略

维护 `client/` 时固定以下原则：

- 使用 Node LTS。
- 包管理器先选 npm，除非项目明确改用 pnpm。
- 必须提交 lockfile。
- 不引入第二套大型 UI 组件库。
- shadcn/ui 组件按需添加。
- 图标优先使用 `lucide-react`。
- 新增依赖必须有明确用途，不为单个小函数引入大型包。

建议基础依赖：

- React
- Vite
- TypeScript
- Tailwind CSS
- shadcn/ui
- react-router
- axios 或 fetch wrapper
- lucide-react
- Vitest
- React Testing Library
- MSW
- Python Camoufox 脚本用于浏览器冒烟检查，不作为 npm 依赖引入

是否引入 TanStack Query 需要单独决策。

当前依赖基线：

- React 19、React Router 7、Vite 8、TypeScript 6、Tailwind CSS 4。
- axios 作为 API client 底层请求库。
- Vitest、React Testing Library、MSW 和 jsdom 作为测试栈。
- lucide-react 作为图标库。

## 本地开发

当前前端本地开发应支持两种模式：

- 连接真实 FastAPI/ASGI 后端。
- 使用 MSW mock `/api/v1/*`。

要求：

- Vite dev server 代理 `/api` 到后端。
- 没有后端时，关键页面能通过 mock 数据打开。
- mock 数据覆盖空列表、错误、长文本、多页结果、详情和设置页。
- 本地启动说明写入 `client/README.md`。

## 部署切换

Dockerfile 当前固定使用 `client` 构建静态资源：

```bash
docker build -t skyradar .

# Apple Silicon 本地验证镜像时可显式使用 amd64
docker build --platform linux/amd64 -t skyradar .
```

规则：

- Dockerfile 会在 Node 构建阶段自动执行 `client` production build。
- 发布或部署切换前仍应在 `client/` 执行 `npm run check`，确保 lint、测试和构建都通过。
- `deploy/nginx/SkyRadar.conf` 文件名保留历史名称，不因产品名改为 SkyRadar 而重命名。
- nginx 的 `/api` 反向代理行为不因前端切换而改变。
- 当前分支只维护 `client/dist` 作为前端运行产物，不再支持通过 `SKYRADAR_FRONTEND_DIR` 切换多套前端目录。

compose 一键启动：

```bash
docker compose up --build -d
```

compose 默认使用 MongoDB 8.2.7。后端健康检查以当前 FastAPI/ASGI 实现为准，目标环境发布前应复验 `/api/v1/health` 中各子项状态。

## 性能原则

当前项目优先稳定维护，不做复杂性能工程，但应避免明显问题。

规则：

- 代码查看器和高亮库可以懒加载。
- 表格不要在 render 中做昂贵计算。
- 长列表优先分页，不一次性渲染大量数据。
- 图标按需导入。
- 不引入大型图表库，除非页面确实需要。
- production build 后关注 bundle 体积异常增长。

## 浏览器目标

默认支持现代浏览器：

- 最新两个稳定版本 Chrome、Edge、Firefox、Safari。
- 移动端 Safari 和 Chrome 需要基本可用。

不需要支持 IE。

## CI 规则

CI 目标：

- 防止当前前端无法构建。
- 防止类型错误进入主分支。
- 防止 API adapter 行为回退。
- 防止核心页面白屏。
- 防止部署形态破坏静态资源、SPA fallback 或 `/api` 反向代理。
- 防止涉及前端行为的变更遗漏 harness 文档更新。

触发范围：

- `client/**`
- `docs/frontend/**`
- `AGENTS.md`
- `.github/workflows/**`
- Docker/nginx 部署相关文件

必跑检查：

- `npm ci`
- `npm run check`

`npm run check` 应覆盖 lint、test 和 production build。若未来拆分脚本，必须保持等价覆盖。

当前 workflow 为 `.github/workflows/frontend.yml`。pull request 和主分支 push 时按路径触发；`client/package.json` 存在时运行 `client` job；Node 版本、包管理器和 cache 策略必须与 `client` lockfile 保持一致；不安装 Playwright npm 依赖。

浏览器 smoke 不作为项目内 Playwright npm job。使用 `scripts/frontend_camoufox_smoke.py`、人工截图或发布门禁记录覆盖；远端 CI 是否执行 Camoufox 取决于 runner 能力，未执行时必须在 `PROGRESS.md` 或发布记录中说明。

最低本地检查：

```bash
cd client
npm run check
```

浏览器 smoke：

```bash
uv run --no-project --with camoufox==0.4.11 python scripts/frontend_camoufox_smoke.py \
  --base-url http://127.0.0.1:18080 \
  --screenshot-dir .artifacts/camoufox-smoke
```

如果缺少 Camoufox 浏览器二进制：

```bash
uv run --no-project --with camoufox==0.4.11 python -m camoufox fetch
```

## 文档维护规则

`docs/frontend/` 只保留 9 个 Markdown 文件：

- `PLAN.md`：路线和功能矩阵。
- `PROGRESS.md`：当前状态。
- `DECISIONS.md`：ADR。
- `DESIGN.md`：架构/设计规范。
- `IMPLEMENTATION_GUIDE.md`：实现规则。
- `TESTING.md`：测试策略。
- `CHECKLIST.md`：门禁。
- `RISKS.md`：风险。
- `REFERENCES.md`：参考。

更新规则：

- 完成一个有意义的前端切片后，更新 `PROGRESS.md`。
- 路线、功能矩阵或功能状态变化时，更新 `PLAN.md`。
- 产品气质、视觉规范、信息架构、组件原则或可访问性要求变化时，更新 `DESIGN.md`。
- API adapter、类型、状态、错误处理、安全展示、依赖、本地开发、CI 或部署规则变化时，更新 `IMPLEMENTATION_GUIDE.md`。
- 测试范围或覆盖策略变化时，更新 `TESTING.md`。
- 发布门禁或功能完成条件变化时，更新 `CHECKLIST.md`。
- 新风险出现时，更新 `RISKS.md`。
- 新参考资料或外部工程经验需要保留时，更新 `REFERENCES.md`。

收敛规则：

- 不为 API 契约、CI、功能矩阵、设计规则、依赖或本地开发新增独立文档，统一进入上述 9 个文件。
- 不为临时队伍分工、过程流水或一次性验证新增独立文档，结论进入 `PROGRESS.md`。
- 不在 `PLAN.md` 重复当前实现基线、命令、API adapter 细节或风险清单。
- 不在 `TESTING.md` 重复完整命令矩阵，命令以本文为准。

## 新文档例外

默认不新增 `docs/frontend/` 下的专题 Markdown。只有满足以下条件之一，才考虑新增独立文件：

- 需要被 CI 或脚本单独消费。
- 内容已经大到影响现有 9 个文件可读性，并且无法合理拆到既有职责中。
- 不是工程文档，而是机器可读产物、脚本输入或外部发布材料。

涉及长期架构决策应进入 `DECISIONS.md`；涉及发布切换门禁应进入 `CHECKLIST.md`。
