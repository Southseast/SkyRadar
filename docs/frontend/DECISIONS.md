# 决策记录

职责：本文只保留当前有效的前端长期技术和产品实现决策，也就是 ADR。

职责边界：

- 本文记录“为什么选择某个方向”和该选择的长期影响。
- 产品气质、视觉规范和 UI 架构写入 `DESIGN.md`。
- 命令、依赖、CI、部署、API adapter 和实现规则写入 `IMPLEMENTATION_GUIDE.md`。
- 当前状态、已完成事项和验证结果写入 `PROGRESS.md`。
- 风险、缓解和剩余缺口写入 `RISKS.md`。

## 001 - 使用 React、Vite、TypeScript、Tailwind CSS 和 shadcn/ui

状态：Accepted

决策：当前前端使用 React + Vite + TypeScript + Tailwind CSS + shadcn/ui。

影响：

- shadcn/ui 组件作为可编辑源码基元进入 `client/src/components/ui/`。
- 页面业务逻辑放在 pages 或 feature modules。
- 后端 API 契约通过 adapter 兼容。

## 002 - 前端源码统一在 client/

状态：Accepted

决策：前端源码统一位于 `client/`，生产静态资源统一来自 `client/dist`。

影响：

- Dockerfile、compose 和 nginx 只引用当前 `client/dist`。
- 回滚使用 Git 版本或已发布镜像版本。

## 003 - 保持后端 API 契约稳定

状态：Accepted

决策：前端不随意修改 `/api/*` 路径、请求参数或响应结构；兼容差异优先放在 API adapter。

影响：

- 页面组件不直接处理后端兼容细节。
- API 行为发现必须同步 `IMPLEMENTATION_GUIDE.md` 和测试。

## 004 - 按垂直功能切片演进

状态：Accepted

决策：一次推进一个用户可见功能，并在继续下一个切片前完成验证。

影响：

- `PLAN.md` 的功能矩阵是功能覆盖状态源。
- 每个功能都需要明确验收边界。

## 005 - 将 shadcn/ui 组件视为通用源码基元

状态：Accepted

决策：生成的 UI 组件放在 `client/src/components/ui/`，页面特定行为放在功能模块中。

影响：

- 可以本地定制，但定制必须有明确理由。
- `components/ui` 不承载页面业务逻辑。

## 006 - 产品命名统一为 SkyRadar

状态：Accepted

决策：前端、harness 文档和 UI 文案统一使用 SkyRadar。

影响：

- 界面标题、导航和文档中的产品称呼统一。
- 非当前产品命名不再作为当前前端描述。

## 007 - 运行路径统一为 client/dist

状态：Accepted

决策：前端目录统一为 `client/`，Dockerfile 和 compose 固定使用 `client/dist`，不再支持当前分支内多前端运行目录切换。

影响：

- nginx 运行时静态资源来自 `client` 构建产物。
- 回滚使用 Git 版本或已发布镜像版本。
