# SkyRadar Frontend

SkyRadar 前端使用 React、Vite、TypeScript、Tailwind CSS 和 shadcn/ui。

## 开发

```bash
npm install
npm run dev
```

Vite dev server 已配置 `/api` 代理到 `http://127.0.0.1:8888`。

## 验证

```bash
npm run lint
npm run test
npm run build
npm run check
```

`npm run check` 会依次执行 lint、unit test 和 production build。

## 浏览器冒烟

项目内不引入 Playwright。浏览器冒烟检查使用 Camoufox reverse MCP。

当前本地 dev server 在 Camoufox 中可能无法通过 loopback 访问；可使用 production build 后的 `dist/index.html` 做静态壳检查。

## 维护约束

实现前先读取：

- `../AGENTS.md`
- `../docs/frontend/DESIGN.md`
- `../docs/frontend/IMPLEMENTATION_GUIDE.md`
- `../docs/frontend/PLAN.md`
- `../docs/frontend/CHECKLIST.md`
