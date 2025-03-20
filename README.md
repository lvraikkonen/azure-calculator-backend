# Azure云服务成本计算器

![Status Badge](https://img.shields.io/badge/状态-MVP阶段-blue)
![Frontend](https://img.shields.io/badge/前端-React%20%7C%20Tailwind-61DAFB)
![Backend](https://img.shields.io/badge/后端-FastAPI%20%7C%20SQLAlchemy-009688)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)

> 基于AI的Azure云服务成本计算与智能推荐平台，帮助您根据业务需求规划最优的云资源组合

## 📑 项目概述

Azure云服务成本计算器是一个全栈应用，旨在简化Azure云资源的规划和成本估算过程。结合AI顾问功能，系统能够理解用户的业务需求，智能推荐最合适的Azure服务组合和配置方案。

### 💼 主要场景

- **方案探索**: 基于业务需求快速获取合适的云服务组合
- **成本评估**: 实时计算各种配置的预估月度/年度费用
- **方案比较**: 对比不同配置方案的性能和成本差异
- **智能推荐**: 通过AI分析需求，提供最优化的资源配置建议

## 🚀 功能特性

### 前端功能

- **云服务选择与配置**
  - 浏览和筛选12+种Azure服务(计算/存储/数据库等)
  - 实时价格计算与月度总费用展示
  - 响应式布局，适配桌面和移动设备

- **AI顾问对话**
  - 使用自然语言描述需求
  - 实时流式AI回复
  - 智能化服务推荐
  - 基于业务场景的预设方案

### 后端功能

- **智能对话系统**
  - 基于OpenAI API的智能对话引擎
  - 上下文感知的多轮对话支持
  - 结构化云服务推荐生成
  
- **用户及权限管理**
  - JWT令牌认证
  - LDAP/Active Directory集成
  - 基于角色的访问控制

- **数据持久化**
  - 会话和方案持久存储
  - 用户偏好和设置保存
  - 方案分享与导出

## 🔧 技术架构

### 前端

```
src/
├── App.jsx              # 主入口（状态管理/路由分发）
├── data/                
│   └── azureProducts.js # 预置服务数据集
└── components/
    ├── AIAdvisor/       # 智能推荐模块（含交互式对话）
    ├── ProductCalculator/ # 手动计算器核心逻辑
    └── SummaryPanel/    # 实时费用摘要与导出
```

- **框架**: React + Hooks
- **样式**: Tailwind CSS
- **构建工具**: Vite
- **状态管理**: React Context/Redux

### 后端

```
app/
├── api/        # API路由和依赖项
├── core/       # 核心配置和工具
├── db/         # 数据库配置
├── models/     # 数据库模型
├── schemas/    # 数据验证模式
├── services/   # 业务逻辑服务
└── utils/      # 工具函数
```

- **API框架**: FastAPI
- **数据库ORM**: SQLAlchemy (异步)
- **数据验证**: Pydantic
- **认证**: JWT + LDAP支持
- **AI集成**: OpenAI API
- **数据库**: PostgreSQL (开发), MS SQL Server (生产)

## 🔌 系统集成

### 外部服务集成

- **OpenAI API**: 提供智能对话和推荐能力
- **Azure Retail Prices API**: 获取实时Azure产品定价数据 (规划中)
- **Active Directory/LDAP**: 企业用户认证

## 📦 安装与运行

### 前端

```bash
# 安装依赖
npm install

# 开发模式运行
npm run dev

# 构建生产版本
npm run build
```

### 后端

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# 安装依赖
pip install poetry
poetry install

# 配置环境变量
cp .env.example .env
# 编辑.env文件设置必要参数

# 初始化数据库
python -m app.scripts.init_db

# 启动服务
uvicorn app.main:app --reload
```

### Docker部署

```bash
# 启动所有服务
docker-compose up -d

# 仅启动后端
docker-compose up api -d
```

## 📈 开发路线图

### 近期规划 (1-3个月)

- 🔴 **P0** 产品数据API集成
  - 替换静态数据，接入[Azure Retail Prices API](https://learn.microsoft.com/en-us/rest/api/cost-management/retail-prices)
- 🔴 **P0** 用户设置持久化
  - 使用IndexedDB/localStorage保存历史方案
- 🔵 **P1** 产品详情展示
  - 点击产品卡片显示详细信息
- 🔵 **P1** 费用可视化
  - 集成图表库实现费用分布和趋势图表

### 中期规划 (3-6个月)

- 🔴 **P0** 用户账户系统
  - 添加用户注册、登录和配置文件功能
- 🔵 **P1** 方案共享功能
  - 允许用户分享方案链接给其他用户
- 🔵 **P1** 高级AI顾问
  - 增强AI顾问，支持更精确的资源推荐
- 🟢 **P2** 多货币支持
  - 支持不同货币的价格显示和转换

### 远期规划 (6-12个月+)

- 🔵 **P1** 企业级集成
  - 与企业资源规划和预算系统集成
- 🔵 **P1** 高级资源分析
  - 提供资源使用预测和优化建议
- 🟢 **P2** 多云对比
  - 支持Azure与其他云提供商的成本对比

## 🤝 贡献指南

我们欢迎各种形式的贡献，包括功能建议、问题报告和代码提交:

1. **开发流程**
   - Fork仓库并创建特性分支（`feat/feature-name`）
   - 提交遵循[Conventional Commits](https://www.conventionalcommits.org/)规范
   - 新功能需包含单元测试和文档更新

2. **代码规范**
   - 前端: ESLint + Prettier (Airbnb规范)
   - 后端: Black + isort + mypy

## 📄 许可协议

本项目采用 [MIT 许可证](LICENSE)

---

**完整技术文档**: [查看系统架构设计](./Azure-Calculator-Roadmap.md)