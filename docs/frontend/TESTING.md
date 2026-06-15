# 前端测试策略

职责：本文记录前端测试分层、覆盖范围、测试数据规则和必须补测试的变更类型。

职责边界：

- 具体命令、CI job、workflow 策略和 smoke 脚本调用方式统一维护在 `IMPLEMENTATION_GUIDE.md`。
- 产品气质、视觉规范和可访问性要求维护在 `DESIGN.md`；本文只从测试视角列覆盖点。
- 功能完成和发布前的执行门禁维护在 `CHECKLIST.md`，本文不维护 checkbox。
- 当前真实验证结果维护在 `PROGRESS.md`，本文不记录某次执行是否通过。

## 测试目标

- 防止页面白屏。
- 防止 API adapter 兼容逻辑回退。
- 防止关键交互、空态、错误态和 loading 态缺失。
- 防止敏感字段进入页面状态或测试快照。
- 防止 Docker/nginx 发布形态破坏静态资源或 `/api/v1/*` 代理。

## 技术栈

- Vitest：单元测试和轻量组件测试。
- React Testing Library：面向用户行为的组件测试。
- MSW：需要网络层 mock 时使用。
- Python Camoufox 脚本：浏览器冒烟和多视口检查。

项目内不引入 Playwright npm 依赖。

## 测试分层

### Unit

覆盖：

- API response adapter。
- `/api/v1/leakages` 列表 query 参数序列化。
- base64 代码解码。
- URL query 和 tab 状态转换。
- 敏感字段剥离，例如 GitHub `password`、SMTP password、webhook token。

### Component

覆盖：

- 结果表格 loading、empty、error、分页、筛选、行操作。
- 泄露详情代码展示、状态表单、受影响资产和错误态。
- 设置页 tab 切换、表单校验、保存、删除、测试通知。

### Browser Smoke

覆盖：

- `/` 可渲染，结果列表主路径可用。
- `/view/leakage/:id` 可渲染，详情主路径可用。
- `/setting/:tab` 可渲染，tab 切换可用。
- 关键视口下文本不重叠、按钮不溢出、弹窗不超出视口。

### Release Gate Smoke

发布前必须对预发或生产形态 URL 执行只读 smoke，并保留 JSON 或截图证据。

必须覆盖：

- 静态资源可访问。
- SPA fallback 可用。
- `/api/v1/health` 可访问且子项符合预期。
- `/api/v1/leakages`、`/api/v1/leakages/{id}`、`/api/v1/leakages/{id}/code` 只读链路可用。
- `/api/v1/github-accounts`、`/api/v1/search-rules`、`/api/v1/task-schedules/current`、`/api/v1/blacklist-items`、`/api/v1/notification-recipients`、`/api/v1/mail-settings/current`、`/api/v1/webhooks` 只读链路可用。

## 测试数据

- 使用脱敏 fixture。
- 不提交真实 GitHub PAT、SMTP password、webhook URL、泄露代码和内部资产。
- 真实数据验证只保留摘要、JSON smoke 输出或脱敏截图。

## 必须补测试的变更类型

- 修改 API adapter、请求参数或响应解析。
- 修改路由、URL query 或 tab 映射。
- 修改结果列表、详情页、设置页主工作流。
- 修改敏感字段展示、过滤或日志。
- 修改 Docker/nginx 静态资源路径、SPA fallback 或 `/api` 代理。
- 引入新的 UI primitive 或页面布局模式。

## 记录规则

- 每次有意义的前端切片完成后，更新 `PROGRESS.md`。
- 功能状态变化时，更新 `PLAN.md` 的功能矩阵和 `PROGRESS.md`。
- 未运行的测试只能写“未运行”或“待补”，不能写成通过。
