# 前端工程路线

职责：本文只记录前端后续路线、阶段目标、功能矩阵和明确不做事项。

职责边界：

- 当前状态和最近验证写入 `PROGRESS.md`，不在本文重复维护。
- 产品气质、视觉规范、信息架构和组件原则写入 `DESIGN.md`。
- API adapter、类型、状态、依赖、本地开发、CI 和部署规则写入 `IMPLEMENTATION_GUIDE.md`。
- 测试策略、发布门禁、风险和参考资料分别写入 `TESTING.md`、`CHECKLIST.md`、`RISKS.md`、`REFERENCES.md`。
- 本文可以引用这些文档，但不复制其中的事实清单。

## 后续目标

1. 回填远端 GitHub Actions 最新通过记录。
2. 在预发或生产形态执行只读真实数据抽样，并保留 JSON 或截图证据。
3. 继续维护 API adapter 边界，新增 API 使用时同步更新 `IMPLEMENTATION_GUIDE.md`。
4. UI 发生有意义变更时，按 `DESIGN.md` 复核密度、层级、状态、空态、错误态和移动端布局。
5. Docker/nginx 相关修改必须验证静态资源、SPA fallback 和 `/api` 反向代理。
6. 文档继续保持收敛，不为一次性验证、临时分工或小主题新增独立文档。

## 功能矩阵

状态说明：

- `Done`：功能代码和基础验收完成。
- `Gate Pending`：功能可用，但发布门禁仍有待补验证。
- `Planned`：尚未实现。

| ID | 功能 | 状态 | 主要 API/路由 | 验收边界 |
| --- | --- | --- | --- | --- |
| F001 | 结果仪表盘和结果表格 | Done | `/`, `/api/v1/trends`, `/api/v1/statistics`, `/api/v1/leakages`, `PATCH /api/v1/leakages/{id}` | 列表、筛选、分页、统计、loading/empty/error、行级状态处理可用 |
| F002 | 泄露详情 | Done | `/view/leakage/:id`, `/api/v1/leakages/{id}`, `/api/v1/leakages/{id}/code`, `PATCH /api/v1/leakages/{id}` | 详情加载、base64 解码、受影响资产、安全/忽略/备注提交可用 |
| F003 | 设置页框架和页签 | Done | `/setting`, `/setting/:tab` | tab 可直达，切换同步 URL |
| F004 | GitHub 账号设置 | Done | `/api/v1/github-accounts` | 账号列表、添加、删除、配额展示和敏感字段过滤可用 |
| F005 | 查询规则设置 | Done | `/api/v1/search-rules` | 规则列表、添加、编辑、启停、删除和 GitHub 搜索链接可用 |
| F006 | 任务调度设置 | Done | `/api/v1/task-schedules/current` | 读取默认值、保存扫描间隔和查询页数可用 |
| F007 | 黑名单设置 | Done | `/api/v1/blacklist-items` | 黑名单列表、添加、删除和状态反馈可用 |
| F008 | 通知设置 | Done | `/api/v1/notification-recipients`, `/api/v1/mail-settings/current`, `/api/v1/webhooks` | 收件人、SMTP、webhook 保存/删除/测试链路可用，secret 不展示 |
| F009 | 部署切换准备 | Gate Pending | `client/dist`, `/api/v1/health`, SPA fallback | Docker/nginx 静态资源目标和 `/api` 代理已准备，正式发布仍需 release gate |

## P0 验收规则

- 用户可见主路径可用。
- API adapter 兼容 `IMPLEMENTATION_GUIDE.md` 中的请求参数和 response shape。
- loading、empty、error、success 状态完整。
- 敏感字段不进入页面展示、测试快照或日志。
- `npm run check` 通过或明确记录无法运行原因。
- 浏览器 smoke 或等价人工截图覆盖主路径。

## 不做事项

- 不恢复多套前端运行目录。
- 不把 API 兼容逻辑散落到页面组件中。
- 不把页面业务逻辑放进 `client/src/components/ui/*`。
- 不用 landing/hero/装饰性视觉替代实际工作台界面。
- 不在项目内引入 Playwright npm 依赖；浏览器冒烟使用 Python Camoufox 脚本或人工截图门禁。
