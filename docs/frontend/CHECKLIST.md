# 前端完成清单

职责：本文只维护前端功能完成和发布前需要逐项确认的门禁清单。

职责边界：

- 本文使用 checkbox 表达“是否已检查”，不解释设计背景。
- 功能矩阵和路线见 `PLAN.md`，设计规范见 `DESIGN.md`，实现规则和命令见 `IMPLEMENTATION_GUIDE.md`，测试策略见 `TESTING.md`。
- 风险背景见 `RISKS.md`，当前真实验证结果见 `PROGRESS.md`。
- 如果某项规则需要长期解释，应更新对应职责文档，再在本文保留简短检查项。

本清单分为 `Feature Done` 和 `Release Gate` 两层。`Feature Done` 用于更新 `PLAN.md` 功能矩阵状态；`Release Gate` 用于发布或生产形态放行。

## Feature Done

### 功能兼容

- [ ] 用户可见行为与 `PLAN.md` 功能矩阵和 `IMPLEMENTATION_GUIDE.md` API Client 规则兼容。
- [ ] API endpoint、请求参数和 payload 结构兼容。
- [ ] 响应解析兼容后端 `status/msg/result` 结构。
- [ ] URL、query 和 tab 行为与路由契约一致。

### UI 状态

- [ ] loading、empty、error 和 success 状态完整。
- [ ] 删除、忽略、确认等关键操作有明确反馈。
- [ ] 表单错误靠近对应字段。
- [ ] 表格、列表、代码块和弹窗在主要视口下不破坏布局。

### 设计和可访问性

- [ ] 符合 `DESIGN.md` 的产品气质、颜色、间距、圆角和密度要求。
- [ ] 没有 landing、hero、渐变装饰、玻璃拟态或卡片套卡片。
- [ ] 表单字段有关联 label。
- [ ] 纯图标按钮有 `aria-label` 或 tooltip。
- [ ] focus-visible 清晰可见。
- [ ] 状态不只依赖颜色表达。

### 测试和文档

- [ ] 单元测试、组件测试或 API adapter 测试已添加；如不需要，已说明原因。
- [ ] Python Camoufox 冒烟或人工截图已覆盖主路径；如未运行，已记录原因。
- [ ] `npm run check` 通过，或记录未运行原因。
- [ ] `PROGRESS.md` 已更新。
- [ ] `PLAN.md` 功能矩阵状态已更新。
- [ ] 新增 API 行为发现已补充到 `IMPLEMENTATION_GUIDE.md`。

## Release Gate

发布验收或生产形态放行前必须确认：

- [ ] 所有 P0 feature 状态为 `Done` 或明确风险接受。
- [ ] `npm run check` 通过。
- [ ] Docker build 通过。
- [ ] 静态资源可访问。
- [ ] SPA fallback 可用。
- [ ] `/api/v1/health` 可访问，且 MongoDB/GitHub 子项符合当前后端预期。
- [ ] `/api/v1/leakages` 列表参数符合 REST 契约。
- [ ] `/api/v1/leakages/{id}` 和 `/api/v1/leakages/{id}/code` 详情链路符合 REST 契约。
- [ ] `/api/v1/*` 设置资源只读链路可用。
- [ ] `/`、`/view/leakage/:id`、`/setting/:tab`、`/?tag=...` 可用。
- [ ] 多视口检查覆盖桌面、平板和移动端。
- [ ] 预发或生产形态真实数据只读 smoke 通过，或明确风险接受。
- [ ] 回滚方式明确：Git 版本或已发布镜像版本。
- [ ] 发布门禁评审记录包含命令输出、JSON 或截图证据。

## 发布门禁评审模板

- 评审时间：
- 评审范围：
- 构建结果：
- 测试结果：
- 浏览器 smoke：
- 真实数据 smoke：
- API/路由兼容：
- UI/可访问性：
- 已知风险：
- 回滚方式：
- 结论：允许发布 / 不允许发布
