# 前端 Harness 进度

职责：本文只记录当前有效状态、下一步、阻塞项、待补验证和最近真实验证。

职责边界：

- 后续路线和功能矩阵写入 `PLAN.md`，本文只引用下一步，不展开路线设计。
- 产品气质、视觉规范和 UI 架构写入 `DESIGN.md`，本文不复制规范全文。
- 命令模板、API adapter、CI、部署和实现规则写入 `IMPLEMENTATION_GUIDE.md`，本文只记录已经运行的验证结果。
- 测试策略和发布门禁分别写入 `TESTING.md` 与 `CHECKLIST.md`。
- 未运行事项必须写为“待补”或“未运行”，不能写成通过。

## 当前状态

- 当前前端源码位于 `client/`，技术栈为 React、Vite、TypeScript、Tailwind CSS 和 shadcn/ui。
- 核心工作流已落地：结果仪表盘、结果表格、泄露详情、设置页和通知配置。
- 架构为 `AppShell` + page routes + feature modules + typed API adapter。
- API 兼容逻辑集中在 `client/src/lib/api/*`。
- Docker/nginx 静态资源目标使用 `client/dist`，`/api` 反向代理行为保持稳定。

## 下一步

- 回填远端 GitHub Actions 的最新通过记录。
- 在预发或生产形态执行只读真实数据抽样，并保留 smoke 输出或截图证据。
- UI 发生有意义变更时，按 `DESIGN.md`、`TESTING.md` 和 `CHECKLIST.md` 复核。
- 新增实现期约束时优先更新 `IMPLEMENTATION_GUIDE.md`，避免继续拆分零散文档。

## 阻塞项

- 暂无本地实现阻塞。

## 最近验证

- `npm run check`
- `scripts/frontend_camoufox_smoke.py`
- `scripts/frontend_release_gate_smoke.py`
- Docker/nginx 静态资源与 `/api` 代理 smoke
- 真实 GitHub 搜索、PAT 配置和 DingTalk webhook smoke
