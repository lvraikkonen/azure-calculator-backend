# AI智能对话系统 - 前端

基于 Vue 3 + TypeScript + Vite 构建的企业级AI对话系统前端应用。

## 🚀 快速开始

### 环境要求

- Node.js >= 18.0.0
- npm >= 9.0.0

### 安装依赖

```bash
npm install
```

### 开发模式

```bash
npm run dev
```

应用将在 http://localhost:3000 启动

### 构建生产版本

```bash
npm run build
```

### 预览生产构建

```bash
npm run preview
```

## 🛠️ 开发工具

### 代码检查

```bash
npm run lint
```

### 代码格式化

```bash
npm run format
```

### 类型检查

```bash
npm run type-check
```

### 运行测试

```bash
npm run test
```

## 📁 项目结构

```
src/
├── components/     # 组件库
├── views/         # 页面视图
├── stores/        # 状态管理
├── services/      # API服务
├── types/         # 类型定义
├── utils/         # 工具函数
├── assets/        # 静态资源
└── router/        # 路由配置
```

## 🔧 技术栈

- **框架**: Vue 3.4+ + TypeScript 5.3+
- **构建工具**: Vite 5.0+
- **状态管理**: Pinia 2.1+
- **路由**: Vue Router 4.2+
- **UI框架**: Element Plus 2.4+
- **样式**: UnoCSS 0.58+
- **HTTP客户端**: Axios 1.6+
- **工具库**: VueUse 10.7+

## 🌐 API集成

前端通过代理连接到后端API：
- 开发环境: http://localhost:8000/api/v1
- API文档: http://localhost:8000/docs

## 📝 开发规范

- 使用 Composition API + `<script setup>` 语法
- 严格的 TypeScript 类型检查
- ESLint + Prettier 代码规范
- 组件化开发模式
- 响应式设计支持

## ⚠️ 注意事项

- 本项目为子目录项目，Git hooks由根目录管理
- 确保后端服务在 http://localhost:8000 运行以测试API连接
- 开发时请遵循TypeScript严格模式

## 🔗 相关链接

- [Vue 3 文档](https://vuejs.org/)
- [Element Plus 文档](https://element-plus.org/)
- [UnoCSS 文档](https://unocss.dev/)
- [Vite 文档](https://vitejs.dev/)
