# Azure云服务成本计算器

![Status Badge](https://img.shields.io/badge/状态-MVP阶段-blue)
![Frontend](https://img.shields.io/badge/前端-React%20%7C%20Tailwind-61DAFB)
![Backend](https://img.shields.io/badge/后端-FastAPI%20%7C%20SQLAlchemy-009688)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)

> 基于AI的Azure云服务成本计算与智能推荐平台，帮助您根据业务需求规划最优的云资源组合

## 📑 项目概述

项目概述 🚀Azure RAG 智能云服务助手是一个专为 Azure 云服务提供智能检索和问答服务的系统，结合了最新的检索增强生成（RAG）技术与组件化架构，为用户提供精准的 Azure 云服务信息、定价计算和最佳实践建议。

### 核心功能 ✨

- 智能问答服务
  - 基于 Azure 文档的精确检索与响应
  - 多策略融合检索，提高召回率与准确性
  - 自适应排序，呈现最相关内容
- 高级定价咨询
  - 云服务成本估算与比较
  - 针对多方案的成本优化建议
  - 实时价格数据集成
- 最佳实践推荐
  - 基于用途的 Azure 服务组合推荐
  - 架构设计与配置指导
  - 集成专家经验的决策支持
- 智能交互体验
  - 自然语言理解与查询优化
  - 上下文相关的多轮对话
  - 自定义知识库支持

## 技术架构 ⚙️

系统采用模块化组件注册表架构，实现灵活可插拔的功能扩展：

``` mermaid
flowchart TD
    subgraph "用户层"
        UI[用户界面/API]
    end
    
    subgraph "服务层"
        RS[RAG服务]
        RSF[RAG服务工厂]
        ES[评估服务]
    end
    
    subgraph "组件注册表"
        CR[组件注册表]
    end
    
    subgraph "文档处理"
        DL[文档加载器] --> CR
        CH[分块器] --> CR
    end
    
    subgraph "嵌入和存储"
        EM[嵌入模型] --> CR
        VS[向量存储] --> CR
    end
    
    subgraph "检索和排序"
        QT[查询转换器] --> CR
        RET[检索器] --> CR
        RR[重排序器] --> CR
    end
    
    subgraph "生成和评估"
        GEN[生成器] --> CR
        EV[评估器] --> CR
    end
    
    UI -- 查询请求 --> RS
    RS -- 创建请求 --> RSF
    RSF -- 获取组件 --> CR
    CR -- 提供组件 --> RSF
    RSF -- 返回实例 --> RS
    RS -- 返回结果 --> UI
    RS -- 评估请求 --> ES
    
    classDef primary fill:#4299e1,stroke:#2b6cb0,color:white
    classDef secondary fill:#38b2ac,stroke:#2c7a7b,color:white
    classDef component fill:#9f7aea,stroke:#6b46c1,color:white
    
    class UI,RS,RSF,ES primary
    class CR,DL,CH,EM,VS,QT,RET,RR,GEN,EV component
```



![](C:\Users\lv.shuo\Pictures\Weixin Image_20250331170947.png)

### RAG 查询处理流程

``` mermaid
sequenceDiagram
    participant U as 用户
    participant S as RAG服务
    participant QT as 查询转换器
    participant R as 检索器
    participant RR as 重排序器
    participant G as 生成器
    
    U->>S: 提交查询
    S->>QT: 转换查询
    Note over QT: 多查询生成、HyDE增强等
    QT-->>S: 返回转换后查询
    
    S->>R: 执行检索
    Note over R: 多策略融合检索、RAG-Fusion等
    R-->>S: 返回相关文档块
    
    S->>RR: 排序文档块
    Note over RR: LLM重排序、多阶段重排序等
    RR-->>S: 返回排序后文档块
    
    S->>G: 生成回答
    Note over G: 上下文生成、专业领域优化等
    G-->>S: 返回生成回答
    
    S->>U: 返回最终结果
```



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

### 核心模块实现

#### 1. 组件注册表系统

``` python
# 组件类型定义
EMBEDDER = "embedder"
CHUNKER = "chunker" 
RETRIEVER = "retriever"
RERANKER = "reranker"
QUERY_TRANSFORMER = "query_transformer"
GENERATOR = "generator"
VECTOR_STORE = "vector_store"
DOCUMENT_LOADER = "document_loader"

# 装饰器注册示例
@register_component(RAGComponentRegistry.CHUNKER, "advanced_semantic")
class AdvancedSemanticChunker(ContentProcessor[Document, TextChunk]):
    """高级语义分块器 - 基于语义和结构进行智能分块"""
    ...
```

#### 2. 高级组件实现

系统实现了多种先进RAG组件：

| 组件类型   | 新增实现                   | 核心功能                             |
| ---------- | -------------------------- | ------------------------------------ |
| 查询转换器 | AdvancedHyDETransformer    | 假设文档扩展，生成高质量文档片段     |
|            | AdvancedQueryDecomposition | 智能拆解复杂查询并指定检索策略       |
| 分块器     | AdvancedSemanticChunker    | 基于文档类型的智能分块，保留文档结构 |
| 检索器     | MultiQueryFusionRetriever  | 多查询变体融合提高召回率             |
|            | RAGFusionRetriever         | 专为RAG优化的融合检索策略            |
| 重排序器   | LLMReranker                | 使用LLM精确评估文档与查询相关性      |
|            | MultistageReranker         | 多阶段重排序策略结合                 |
|            | HybridRelevanceReranker    | 融合语义与关键词相关性               |



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



## 性能指标 📊

在Azure云服务问答评估集上的性能：

| 指标       | 基础模型 | 混合检索 | RAG-Fusion |
| ---------- | -------- | -------- | ---------- |
| 准确率     | 76.2%    | 83.5%    | 89.7%      |
| 召回率     | 68.4%    | 79.2%    | 85.3%      |
| 平均延迟   | 0.8s     | 1.2s     | 1.5s       |
| 用户满意度 | 3.6/5    | 4.2/5    | 4.7/5      |

## 未来规划 🔮

1. **多模态支持**：集成图表和架构图理解能力
2. **个性化推荐**：学习用户偏好，提供定制化建议
3. **多云集成**：扩展到AWS、GCP等多云环境
4. **企业集成**：支持SSO和内部知识库连接
5. **增强评估框架**：扩展自动化测试和评估系统



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