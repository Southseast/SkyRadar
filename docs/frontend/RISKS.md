# 风险登记

职责：本文只记录当前前端的已知风险、影响、状态和缓解方向。

职责边界：

- 本文不记录当前进度或某次验证结果；这些写入 `PROGRESS.md`。
- 本文不维护命令、CI、部署步骤或完整门禁；这些写入 `IMPLEMENTATION_GUIDE.md` 和 `CHECKLIST.md`。
- 本文不复制设计规范、API adapter 规则或测试策略；这些分别写入 `DESIGN.md`、`IMPLEMENTATION_GUIDE.md` 和 `TESTING.md`。
- 已缓解风险仍可保留为防回归风险，但实现细节只保留摘要。

## R001 - 后端 API 无应用级鉴权

状态：已知风险

描述：当前 `/api/*` 访问控制主要依赖部署网络边界或反向代理保护。

影响：服务暴露到不可信网络时，攻击者可能查看结果、修改规则、删除配置或调整通知。

缓解：

- 前端不改变后端鉴权行为。
- 部署环境应通过网络边界、反向代理认证、VPN 或防火墙限制访问。
- 应用级鉴权作为后端独立工作推进。

## R002 - 后端 response shape 不统一

状态：已知风险

描述：大多数接口返回 `status/msg/result`，但 `/api/health` 等接口结构不同；部分 DELETE 接口用 body `status=404` 表示成功。

影响：页面如果直接解释后端 response，容易误判成功或失败。

缓解：

- API adapter 统一兼容差异。
- 页面组件不直接解释底层后端细节。
- 新发现写入 `IMPLEMENTATION_GUIDE.md`。

## R003 - 敏感信息展示风险

状态：已知风险

描述：GitHub token/password、SMTP password、webhook URL 和 secret 可能出现在设置接口响应或错误对象中。

影响：敏感信息可能进入 React state、console、错误采集、截图或测试快照。

缓解：

- Adapter 删除或掩码敏感字段。
- UI 只展示必要脱敏字段。
- 测试 fixture、截图和日志不得包含真实 secret。

## R004 - 运行路径回退风险

状态：已缓解，保留防回归风险

描述：当前前端运行路径统一为 `client/` 和 `client/dist`。如果后续重新引入多套运行目录，会增加构建、发布和回滚复杂度。

影响：Docker/nginx 可能服务错误产物，或者发布时无法判断真实静态资源来源。

缓解：

- 当前分支只维护 `client/`。
- Dockerfile、compose 和 nginx 使用 `client/dist`。
- 回滚使用 Git 版本或已发布镜像版本。

## R005 - 大范围改动导致功能遗漏

状态：已知风险

描述：结果页、详情页和设置页共享 API adapter、状态转换和 UI primitives，大范围改动容易漏掉小交互。

影响：分页、筛选、表单错误、删除确认、空态或错误态可能回归。

缓解：

- 使用 `PLAN.md` 的功能矩阵跟踪功能状态。
- 使用 `CHECKLIST.md` 做完成检查。
- 按垂直功能切片推进。

## R006 - 发布形态回滚风险

状态：已知风险

描述：发布形态依赖 `client/dist`、SPA fallback 和 `/api` 反向代理。任一环节配置错误都会导致页面或 API 不可用。

影响：用户可能无法访问前端、刷新深链 404，或 API 请求落到错误 upstream。

缓解：

- 发布前执行 Release Gate。
- Docker/nginx 变更必须验证静态资源、SPA fallback 和 `/api/health`。
- 回滚方式使用 Git 版本或镜像版本。

## R007 - UI 风格漂移

状态：已知风险

描述：不同会话或不同 agent 可能生成不一致的颜色、间距、圆角、密度和组件组合。

影响：页面之间视觉割裂，削弱产品质感和可扫描性。

缓解：

- 实现页面前读取 `DESIGN.md`。
- 通用 UI primitive 保持通用，页面逻辑放在 feature modules。
- 视觉方向变化必须更新 `DESIGN.md`。

## R008 - 测试落地滞后

状态：已知风险

描述：如果先修改大量页面，再补测试，回归问题会难以定位。

影响：后续修改容易破坏 API adapter、URL 状态、表格和表单行为。

缓解：

- 修改 adapter、路由或关键工作流时同步补测试。
- CI 保持 `npm run check` 可执行。
- 浏览器 smoke 或人工截图覆盖主路径。

## R009 - Docker 基线回退风险

状态：已缓解，保留防回归风险

描述：当前 Docker 基线已使用 Python 3.13/Debian Trixie 和 `client/dist`。后续不得回退到 EOL 基础镜像或多前端产物来源。

影响：镜像构建、安全更新和发布可复现性会退化。

缓解：

- Dockerfile 保持当前基础镜像方向。
- 静态资源来源保持 `client/dist`。
- Apple Silicon 本地验证如遇架构问题，可显式使用 `--platform linux/amd64`。

## R010 - `/api/health` 子项复验风险

状态：需目标环境复验

描述：前端发布门禁需要读取 `/api/health`，但 HTTP 200 不代表 MongoDB/GitHub 子项健康。

影响：静态资源可用但后端依赖异常，页面仍可能无法正常工作。

缓解：

- Release Gate 必须检查 `/api/health` 子项。
- 目标环境发布前按实际 MongoDB、GitHub 网络和认证配置复验。

## R011 - GitHub 账号响应回传 secret

状态：已知风险

描述：GitHub 账号写入或删除响应可能包含原始 `password` 字段。

影响：如果前端直接保存响应，PAT 可能进入页面状态、调试工具或错误采集链路。

缓解：

- `client/src/lib/api/settings.ts` 的 adapter 删除 `password` 字段。
- 页面只展示 `mask_password`、账号和配额信息。
- 后端应独立加固写入和删除响应 projection。
