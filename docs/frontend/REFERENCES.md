# 设计参考

职责：本文只记录前端可参考的设计系统、文章、仓库和对 SkyRadar 的适配性结论。

职责边界：

- 本文提供外部参考和借鉴判断，不作为项目规范源。
- 已采纳的长期决策写入 `DECISIONS.md`，当前视觉和交互规范写入 `DESIGN.md`。
- 后续路线和功能矩阵只以 `PLAN.md` 为准；本文的参考启发不能单独视为承诺。
- 命令、CI、部署和测试规则不在本文维护。

## AI 前端设计 Harness

### StyleSeed

- 地址：<https://github.com/bitjaru/styleseed>
- 价值：将 AI 前端设计拆成设计规则、品牌皮肤和组件模式，避免模型随机选择颜色、间距和样式。
- 对本项目的启发：把审美要求写入持久文档，而不是只在 prompt 中说“做得好看”。

### awesome-claude-design

- 地址：<https://github.com/rohitg00/awesome-claude-design>
- 价值：收集不同 aesthetic family 的 `DESIGN.md`、设计 recipe 和 prompt。
- 对本项目的启发：用项目级 `DESIGN.md` 锚定风格，让 agent 跨会话保持一致。

### shadcn/ui React Prompt

- 地址：<https://www.shadcn.io/prompts/react-shadcn>
- 价值：强调使用 TypeScript、Radix accessibility、CVA variants 和设计系统方式生成 shadcn/ui 组件。
- 对本项目的启发：shadcn/ui 不是直接“变好看”的魔法，必须结合组件状态、可访问性和设计约束。

## 设计系统和原则

### Apple Human Interface Guidelines

- 地址：<https://developer.apple.com/design/human-interface-guidelines/>
- 价值：强调清晰层级、内容优先、控件服务任务。
- 对本项目的启发：后台系统应让内容和状态优先，而不是让装饰元素抢注意力。

### Microsoft Fluent UI Design Tokens

- 地址：<https://learn.microsoft.com/en-us/fluent-ui/web-components/design-system/design-tokens>
- 价值：解释 design token 如何作为颜色、字体、间距等设计属性的语义化变量。
- 对本项目的启发：用 `DESIGN.md` 中的设计 token 固化设计选择，减少 agent 随机发挥。

### shadcn/ui

- 地址：<https://ui.shadcn.com/>
- 价值：提供基于 Radix UI 和 Tailwind CSS 的可复制源码组件。
- 对本项目的启发：把通用 UI primitives 放在 `client/src/components/ui/`，页面逻辑放在 feature 模块。

## 产品气质参考

### GitHub

- 地址：<https://github.com/>
- 可参考点：信息密度、朴素控件、代码和仓库信息展示。

### Linear

- 地址：<https://linear.app/>
- 可参考点：克制层级、精确间距、低噪音操作界面。

### Vercel

- 地址：<https://vercel.com/>
- 可参考点：中性色、留白控制、清晰状态表达。

## 本项目适用结论

- SkyRadar 应采用安全运营后台风格，不采用营销页面风格。
- 表格、筛选、状态和处理操作优先级高于装饰性视觉。
- 设计 token、UI 审查和截图验证应成为前端维护流程的一部分。
- 每个功能切片完成后都要按 `CHECKLIST.md` 自查。
