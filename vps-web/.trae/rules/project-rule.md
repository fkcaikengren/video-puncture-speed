1.项目框架和管理：
- 这是一个基于react v19的前端项目，使用pnpm作为包管理工具。
- 安装依赖 `pnpm add xxx`
- 运行项目：`pnpm dev`
- 技术栈：
  - React v19
  - React Router v7 (Framework Mode)
  - Tailwind CSS v4
  - shadcn/ui
  - Zustand (全局状态管理)
- 安装shadcn组件： `pnpm dlx shadcn@latest add [component]`

2.命名规范：
- 文件命名：采用 kebab-case 命名规范，例如：`video-list.tsx`
- 变量命名：采用 camelCase 命名规范，例如：`videoList`，对于常量采用 UPPER_SNAKE_CASE 命名规范，例如：`VIDEO_LIST`

3.开发原则：
- **React 请求最佳实践**: 
  - 优先使用 React 19 的 `clientLoader`定义页面数据，使用 `useLoaderData` 消费clientLoader返回的promise，避免使用`useEffect`获取数据。
  - 优先使用 React 19 的 `useActionState` 处理表单提交和异步请求，避免使用 `useOptimistic`。
- **State Management**: 优先使用 RRv7 的 URL 状态和 Data Loading；全局 UI 状态使用 Zustand；避免过度使用 Context API。
- **Styling**: 
  - 严格遵循 Tailwind CSS v4 规范，组件库使用 shadcn/ui，优先考虑使用组件，而非自定义tsx/jsx。
  - 对于可复用样式，使用class-variance-authority (cva) 库。
  - 尽量避免使用 Arbitrary values，尽量使用变量名，需要考虑light/dark模式下的样式。

4.目录结构规范：
```text
app/
├── APIs/                # 使用`openapi-ts` 生成的 API 客户端
├── components/          # 复用 UI 组件 (shadcn)
│   ├── ui/             # shadcn 原始组件
│   └── component.tsx       # 业务逻辑封装组件
├── lib/                # 工具函数 (utils.ts, constants.ts)
├── routes/             # 路由页面 (RRv7 File-based routing)
│   ├── _index.tsx      # 首页
│   ├── layout.tsx      # 全局或局部布局
│   └── $.tsx           # 404
├── store/              # Zustand stores
│   └── useUIStore.ts   # 状态切片
├── types/              # TypeScript 类型定义
└── app.css             # Tailwind 注入
```
