# AGENTS.md

## 项目概况

本项目是 SkyRadar，一个用于监控 GitHub 代码泄露的系统。

- 后端：FastAPI/ASGI、Gunicorn/Uvicorn、MongoDB、Redis、Huey。
- 当前前端：React、Vite、TypeScript、Tailwind CSS、shadcn/ui。
- 部署：Docker、OpenResty/nginx、supervisor。

## 前端 Harness 目标

维护当前 React + Vite + TypeScript + Tailwind CSS + shadcn/ui 前端，保持 API 兼容、UI 质量、测试策略、CI 和发布门禁可追踪。

## 约束

- 前端维护期间保持后端 `/api/*` 请求路径、参数和响应结构稳定。
- 当前前端源码位于 `client/`。
- 不要直接编辑生成产物 `client/dist`。
- 除非某个前端维护任务明确需要，不要修改 FastAPI、MongoDB、Redis、Huey、Docker 或 nginx 行为。
- 回滚依赖 Git 版本、已发布镜像版本或明确的配置开关。

## 前端文档 Harness

前端文档位于 `docs/frontend/`。`AGENTS.md` 只维护项目级协作规则和文档入口；每份前端文档的详细职责边界、更新规则和防重复规则以 `docs/frontend/IMPLEMENTATION_GUIDE.md` 为准。

当前前端文档采用 `PLAN.md`、`PROGRESS.md`、`DECISIONS.md`、`DESIGN.md`、`IMPLEMENTATION_GUIDE.md`、`TESTING.md`、`CHECKLIST.md`、`RISKS.md`、`REFERENCES.md` 九文件架构。

涉及前端路线、状态、设计、实现、测试、门禁、风险或参考资料变化时，按 `docs/frontend/IMPLEMENTATION_GUIDE.md` 的文档维护规则更新对应文件。

## 后端 Harness

后端文档位于 `docs/backend/`。`AGENTS.md` 只维护项目级协作规则和文档入口；每份后端文档的详细职责边界、更新规则和防重复规则以 `docs/backend/IMPLEMENTATION_GUIDE.md` 为准。

当前后端文档采用 `PLAN.md`、`PROGRESS.md`、`DECISIONS.md`、`DESIGN.md`、`IMPLEMENTATION_GUIDE.md`、`TESTING.md`、`CHECKLIST.md`、`RISKS.md`、`REFERENCES.md` 九文件架构；具体职责说明和防重复规则只在 `docs/backend/IMPLEMENTATION_GUIDE.md` 维护。

`docs/api/openapi.yaml` 是 Swagger/OpenAPI 机器可读契约源，不属于 `docs/backend/` 的 Markdown 文档架构。
涉及后端 API 行为时，必须同步 `DESIGN.md` 的 API 兼容语义、`docs/api/openapi.yaml` 和契约测试；涉及运行命令、配置、CI、部署或 Agent 规则时，更新 `IMPLEMENTATION_GUIDE.md`。

## 验证

前端发生有意义的修改后，运行以下检查：

- `npm run build`
- `npm run test`，如果已配置
- 如果已配置，则运行 `npm run lint`
- 按 `docs/frontend/CHECKLIST.md` 进行 UI 自查
- 浏览器冒烟检查：
  - 结果仪表盘和结果表格
  - 泄露详情页
  - 设置页签

部署相关修改需要验证 Docker/nginx 静态资源目标以及 `/api` 反向代理行为。
生产静态资源或 nginx 行为切换前，必须按 `CHECKLIST.md` 的发布切换门禁完成检查。

## 提交规则

- 当用户要求提交 commit 时，不直接执行 `git commit`。
- 只给出用户可复制执行的完整提交命令。
- 如果需要先暂存文件，一并给出对应的 `git add ...` 命令。
- 提交信息仍需符合 Conventional Commits，并在存在破坏性变更时包含 `BREAKING CHANGE`。

## 前端维护规则

- 按垂直功能切片推进，不做大批量无关重写。
- 实现或修改任何前端页面前，先读取 `DESIGN.md`、`IMPLEMENTATION_GUIDE.md` 和 `PLAN.md` 中的功能矩阵。
- 每个功能切片完成前，按 `CHECKLIST.md` 检查。
- 涉及部署或 CI 的变更必须符合 `IMPLEMENTATION_GUIDE.md` 和 `CHECKLIST.md`。
- 类型、状态、错误、安全、依赖和本地开发策略必须符合 `IMPLEMENTATION_GUIDE.md`。
- 新增 API 调用前先补齐类型化 API client/adapter。
- 将 API 兼容性处理放在前端适配层，不通过修改后端行为解决。
- shadcn/ui 源码组件优先放在 `client/src/components/ui/`。
- 功能相关组合组件优先放在 `client/src/features/*`。
- 保持生成的 UI 组件通用，不要把页面特定逻辑写进 `components/ui`。
