# Azure Calculator RAG知识库系统设计文档

**文档版本:** 1.0.0  
**创建日期:** 2025-03-24  
**最后更新:** 2025-03-24  
**状态:** 草案

## 1. 项目概述

### 1.1 背景

Azure Calculator 目前已实现了基础的LLM集成和对话管理能力，能够为用户提供简单的Azure服务推荐。然而，系统当前依赖的是有限的静态产品数据，缺乏对Azure产品全面、深入的了解，无法提供详细的定价信息、技术限制和最佳实践建议。

为了提升推荐的准确性和全面性，我们需要引入检索增强生成(RAG)系统，构建全面的Azure知识库，为LLM提供实时、精确的参考信息。

### 1.2 目标

1. 构建涵盖Azure所有服务的全面知识库
2. 实现高效的文档爬取和处理系统
3. 设计优化的检索策略以提高回答准确性
4. 开发管理平台支持知识库维护和RAG系统调优
5. 提供透明的推荐过程，向用户展示决策依据

### 1.3 关键指标

1. **召回率:** 80%以上的相关文档能被成功检索
2. **精度:** 90%以上的推荐包含准确信息
3. **延迟:** 检索+生成总时间<3秒
4. **覆盖度:** 覆盖所有Azure核心服务(200+服务)
5. **新鲜度:** 知识库与官方文档更新延迟<24小时

## 2. 系统架构

### 2.1 总体架构

RAG知识库系统由五个主要模块组成:

1. **知识获取系统** - 负责从多个来源收集Azure服务信息
2. **内容处理与索引系统** - 处理原始内容并创建向量索引
3. **检索引擎** - 实现高效、精准的多策略检索
4. **增强生成系统** - 将检索内容与LLM生成结合
5. **管理平台** - 提供RAG系统管理和调优功能

整体架构图:

```
┌───────────────┐     ┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│ 知识获取系统  │────▶│ 内容处理系统  │────▶│   检索引擎    │────▶│ 增强生成系统  │
└───────────────┘     └───────────────┘     └───────────────┘     └───────────────┘
        │                     │                     │                     │
        │                     │                     │                     │
        ▼                     ▼                     ▼                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                               管理平台                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 与现有系统集成

RAG系统将与现有的Azure Calculator后端系统集成，主要通过以下接口:

1. `RAGService` - 提供给对话服务的主要接口
2. `DocumentAPI` - 知识库内容查询和管理API
3. `ConfigAPI` - RAG参数配置API

集成示意图:

```
┌───────────────────────────┐            ┌───────────────────────────┐
│                           │            │                           │
│   Azure Calculator 现有   │            │     RAG知识库系统         │
│                           │            │                           │
│ ┌─────────────────────┐   │            │ ┌─────────────────────┐   │
│ │   User Service      │   │            │ │   知识获取系统      │   │
│ └─────────────────────┘   │            │ └─────────────────────┘   │
│                           │            │                           │
│ ┌─────────────────────┐   │            │ ┌─────────────────────┐   │
│ │ Conversation Service│◄──┼────────────┼─┤    RAG Service      │   │
│ └─────────────────────┘   │            │ └─────────────────────┘   │
│                           │            │                           │
│ ┌─────────────────────┐   │            │ ┌─────────────────────┐   │
│ │    LLM Service      │◄──┼────────────┼─┤   增强生成系统      │   │
│ └─────────────────────┘   │            │ └─────────────────────┘   │
│                           │            │                           │
│ ┌─────────────────────┐   │            │ ┌─────────────────────┐   │
│ │   Product Service   │   │            │ │    知识库管理       │   │
│ └─────────────────────┘   │            │ └─────────────────────┘   │
└───────────────────────────┘            └───────────────────────────┘
```

## 3. 核心组件设计

### 3.1 知识获取系统

#### 3.1.1 文档爬虫

使用Firecrawl工具构建高效爬虫系统，爬取以下Azure内容:

- 产品文档
- 定价页面
- 限制与配额信息
- 最佳实践指南
- 架构参考

**关键特性:**
- 支持JavaScript渲染页面
- 增量爬取与更新检测
- 自动处理分页内容
- URL优先级管理
- 高效的并行处理

#### 3.1.2 数据源管理

| 数据源类型 | 爬取频率 | 优先级 | 处理方式 |
|------------|----------|--------|----------|
| 产品页面   | 每周     | 高     | 完整解析 |
| 定价页面   | 每日     | 最高   | 结构化提取 |
| 技术文档   | 每周     | 中     | 语义分块 |
| 最佳实践   | 每月     | 低     | 语义分块 |

#### 3.1.3 变更检测系统

- 基于ETag和Last-Modified标头检测
- 网页内容哈希比对
- RSS feed订阅监测
- 版本控制与历史记录

### 3.2 内容处理与索引系统

#### 3.2.1 内容清洗

- HTML解析与结构化
- 广告和导航元素过滤
- 表格和列表的结构保留
- 代码片段识别和标记

#### 3.2.2 文档分块策略

实现语义分块器 (Semantic Splitter):

```python
class SemanticSplitter:
    def __init__(self, min_size=100, max_size=2000):
        self.min_size = min_size
        self.max_size = max_size
        
    def split(self, document):
        """根据语义边界分割文档"""
        # 1. 识别章节标题
        # 2. 检测段落边界
        # 3. 处理特殊内容(表格/代码)
        # 4. 确保块大小在范围内
        pass
```

**分块处理流程:**
1. 初步按章节分割
2. 大块进一步按段落分割
3. 尊重表格等结构完整性
4. 为每个块添加上下文元数据

#### 3.2.3 元数据提取

为每个文档和块提取以下元数据:

- 服务名称与类别
- 文档类型 (概述/定价/技术规格)
- 最后更新时间
- URL和来源
- 适用区域
- 相关服务引用

#### 3.2.4 向量化与索引

- 使用Azure OpenAI嵌入模型
- 多级索引结构实现
- 支持混合检索 (向量+关键词)
- 元数据过滤能力

#### 3.2.5 数据管道

```
原始HTML 
  → 内容提取 
    → 语义分块 
      → 元数据增强 
        → 嵌入生成 
          → 向量索引
```

### 3.3 检索引擎

#### 3.3.1 查询理解与转换

实现以下查询处理技术:

1. **查询分解** - 将复杂查询拆分为子查询
2. **查询扩展** - 添加Azure特定术语和同义词
3. **HyDE技术** - 生成假设文档增强检索
4. **意图识别** - 识别查询类型以选择检索策略

#### 3.3.2 多路径检索

支持多种检索策略并融合结果:

```python
class MultiPathRetriever:
    async def retrieve(self, query, user_context=None):
        """执行多路径检索并融合结果"""
        # 并行执行多种检索
        vector_results = await self.vector_search(query)
        keyword_results = await self.keyword_search(query)
        hybrid_results = await self.hybrid_search(query)
        
        # 融合结果
        final_results = self.fusion_strategy.merge(
            [vector_results, keyword_results, hybrid_results],
            query=query,
            context=user_context
        )
        
        return final_results
```

#### 3.3.3 结果精炼

1. **重排序** - 使用交叉编码器模型重新评分
2. **结果去重** - 去除冗余内容
3. **动态选择** - 根据查询特征调整结果数量
4. **结果解释** - 为每个检索结果添加关联度说明

### 3.4 增强生成系统

#### 3.4.1 上下文构建

将检索结果组织为结构化上下文:

```python
def build_context(query, retrieval_results, strategy="relevance_first"):
    """构建给LLM的上下文"""
    
    # 根据不同策略组织内容
    if strategy == "relevance_first":
        # 按相关性排序
        context = organize_by_relevance(retrieval_results)
    elif strategy == "category_grouped":
        # 按服务类别分组
        context = organize_by_category(retrieval_results)
    elif strategy == "comparison_focused":
        # 着重于对比信息
        context = organize_for_comparison(retrieval_results)
        
    # 添加源信息
    context = add_source_information(context)
    
    return context
```

#### 3.4.2 提示词工程

为RAG设计特殊的提示词模板:

```
系统提示: 你是Azure服务顾问助手，基于提供的信息回答问题。始终引用提供的信息，不要编造内容。

背景知识: {{context}}

用户问题: {{query}}

请提供详细回答，并明确指出信息来源。如果提供的信息不足以回答问题，请明确说明。
```

#### 3.4.3 透明度与引用

- 在回答中包含信息来源
- 突出显示关键决策点
- 提供置信度指标
- 支持交互式证据查看

#### 3.4.4 自评估与修正

实现Self-RAG机制:

```python
async def self_rag_generate(query, context):
    """实现自评估RAG生成"""
    
    # 初始生成
    initial_response = await llm_service.generate(
        prompt=build_prompt(query, context)
    )
    
    # 自我评估
    eval_result = await evaluate_response(
        query, initial_response, context
    )
    
    # 如需修正，重新生成
    if eval_result['needs_correction']:
        corrected_response = await llm_service.generate(
            prompt=build_correction_prompt(
                query, context, initial_response, eval_result
            )
        )
        return corrected_response
    
    return initial_response
```

### 3.5 管理平台

#### 3.5.1 知识库管理

- 文档浏览与搜索
- 手动内容编辑
- 质量评估仪表板
- 覆盖度分析工具

#### 3.5.2 Playground

实验性RAG测试环境:

```
+--------------------------------+
|                                |
|  查询: [输入框]      [提交]     |
|                                |
+--------------------------------+
|                                |
|  参数配置                      |
|  检索策略: [ 下拉选择 ]        |
|  结果数量: [ 滑块 ]            |
|  重排序方式: [ 下拉选择 ]      |
|                                |
+--------------------------------+
|         |                      |
| 检索结果 |      生成回答        |
|         |                      |
|         |                      |
|         |                      |
+--------------------------------+
|                                |
|       性能指标与分析            |
|                                |
+--------------------------------+
```

#### 3.5.3 配置管理

- RAG参数配置保存与版本控制
- A/B测试设置
- 部署环境管理 (开发/测试/生产)
- 配置模板库

#### 3.5.4 监控与分析

- 查询日志与统计
- 性能指标跟踪
- 用户反馈分析
- 异常检测与告警

## 4. 数据模型

### 4.1 文档模型

```python
class Document:
    id: UUID
    title: str
    content: str
    url: str
    source: str  # 来源，如"azure-docs"
    service: str  # 相关Azure服务
    doc_type: str  # 文档类型(概述,定价,最佳实践等)
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]  # 其他元数据
```

### 4.2 块模型

```python
class Chunk:
    id: UUID
    document_id: UUID  # 所属文档
    content: str
    position: int  # 在文档中的位置
    embedding_id: str  # 向量数据库中的ID
    metadata: Dict[str, Any]  # 块级元数据
```

### 4.3 配置模型

```python
class RAGConfig:
    id: UUID
    name: str
    description: str
    created_at: datetime
    updated_at: datetime
    
    # 检索配置
    retrieval_strategy: str
    top_k: int
    reranking_enabled: bool
    reranking_model: str
    
    # 嵌入配置
    embedding_model: str
    chunk_size: int
    chunk_overlap: int
    
    # 生成配置
    prompt_template: str
    context_strategy: str
    reference_strategy: str
```

## 5. 实施计划

### 5.1 阶段划分

| 阶段 | 时间 | 主要目标 | 交付物 |
|------|------|---------|--------|
| 0 | 2周 | 评估与准备 | 详细设计文档，环境搭建 |
| 1 | 4-6周 | 基础RAG实现 | 基础爬虫，文档处理，简单检索 |
| 2 | 6-8周 | RAG增强与优化 | 高级检索策略，结果重排序 |
| 3 | 8-10周 | 管理平台开发 | 管理界面，参数配置系统 |
| 4 | 10-12周 | 高级功能实现 | 自适应RAG，Self-RAG |
| 5 | 持续 | 生产化与扩展 | 性能优化，扩展应用 |

### 5.2 阶段0详细计划

| 周 | 任务 | 责任人 | 预期产出 |
|----|------|--------|---------|
| 1 | 项目架构审查 | 架构师 | 架构评估报告 |
| 1 | 环境准备 | 开发团队 | 开发环境配置 |
| 2 | RAG架构扩展设计 | 架构师 | 详细设计文档 |
| 2 | 技术选型评估 | 开发团队 | 技术选型报告 |

### 5.3 阶段1详细计划

| 周 | 任务 | 责任人 | 预期产出 |
|----|------|--------|---------|
| 1-2 | 基础文档爬虫实现 | 爬虫开发 | 可爬取主要Azure产品页面 |
| 1-2 | 简单文档处理器 | 内容处理 | 基础分块和格式化 |
| 3-4 | 向量存储集成 | 检索开发 | 基础向量检索功能 |
| 3-4 | 基础RAG服务 | RAG集成 | 初步RAG查询流程 |
| 5-6 | API端点实现 | API开发 | RAG查询API |
| 5-6 | 初步集成与测试 | 测试团队 | 集成测试报告 |

## 6. API设计

### 6.1 RAG服务API

#### 查询API

```
POST /api/v1/rag/query

Request:
{
  "query": "Azure虚拟机的定价方案有哪些?",
  "options": {
    "top_k": 5,
    "strategy": "hybrid",
    "include_sources": true
  }
}

Response:
{
  "answer": "Azure虚拟机提供多种定价方案，包括...",
  "sources": [
    {
      "title": "Azure虚拟机定价",
      "url": "https://azure.microsoft.com/pricing/details/virtual-machines/",
      "relevance": 0.92
    },
    ...
  ],
  "metadata": {
    "total_chunks": 8,
    "processing_time_ms": 320
  }
}
```

#### 反馈API

```
POST /api/v1/rag/feedback

Request:
{
  "query_id": "550e8400-e29b-41d4-a716-446655440000",
  "rating": 4,
  "feedback": "回答很准确，但缺少了最新的Dev/Test优惠信息",
  "improvement_tags": ["missing_info", "needs_update"]
}

Response:
{
  "status": "success",
  "message": "感谢您的反馈"
}
```

### 6.2 管理API

#### 知识库统计API

```
GET /api/v1/rag/admin/stats

Response:
{
  "total_documents": 2543,
  "total_chunks": 45289,
  "services_covered": 187,
  "last_update": "2025-03-22T14:32:45Z",
  "coverage_stats": {
    "pricing": 98.2,
    "technical": 87.5,
    "best_practices": 76.3
  }
}
```

#### 配置管理API

```
GET /api/v1/rag/admin/configs
POST /api/v1/rag/admin/configs
PUT /api/v1/rag/admin/configs/{config_id}
```

#### 实验API

```
POST /api/v1/rag/admin/experiments

Request:
{
  "name": "混合检索测试",
  "query_set": ["查询1", "查询2", ...],
  "config_variants": [
    {
      "name": "向量优先",
      "config": {...}
    },
    {
      "name": "混合均衡",
      "config": {...}
    }
  ]
}

Response:
{
  "experiment_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "status": "running",
  "estimated_completion": "2025-03-24T16:30:00Z"
}
```

## 7. 评估与优化

### 7.1 评估指标

1. **检索质量指标**
   - 召回率 (Recall)
   - 精确度 (Precision)
   - 归一化折损累积增益 (NDCG)
   - 平均倒数排名 (MRR)

2. **生成质量指标**
   - 相关性评分
   - 事实准确性
   - 覆盖度
   - ROUGE/BLEU分数

3. **系统性能指标**
   - 端到端延迟
   - 检索时间
   - 生成时间
   - 索引大小

### 7.2 评估数据集

创建以下评估数据集:

1. **Azure服务问答集** - 200个问题，涵盖所有主要服务类别
2. **价格计算案例** - 50个复杂价格计算场景
3. **服务对比问题** - 30个服务对比查询
4. **技术限制查询** - 40个关于技术限制和配额的问题

### 7.3 A/B测试

设计自动化A/B测试系统:

1. 配置不同RAG参数变体
2. 随机分配查询到不同配置
3. 收集性能指标和用户反馈
4. 统计分析结果差异
5. 自动识别最优配置

### 7.4 持续优化策略

1. **知识库优化**
   - 基于用户查询分析识别知识空缺
   - 优先填充高频查询的相关内容
   - 主动监控文档更新

2. **检索优化**
   - 查询日志分析辅助检索策略调整
   - 失败案例回顾改进检索参数
   - 按服务类别调整检索策略

3. **生成优化**
   - 提示词模板迭代改进
   - 用户反馈驱动的生成策略调整
   - 自动化评估确保生成质量

## 8. 技术栈与依赖

### 8.1 核心技术

| 组件 | 技术选择 | 备选方案 |
|------|----------|---------|
| 爬虫框架 | Firecrawl | Scrapy, Playwright |
| 文档处理 | BeautifulSoup, Trafilatura | LXML, html5lib |
| 向量数据库 | Qdrant | FAISS, Pinecone, Weaviate |
| 嵌入模型 | OpenAI ada-002 | Azure OpenAI Embeddings |
| LLM | OpenAI GPT-4 | Azure OpenAI, Anthropic Claude |
| 后端框架 | FastAPI (现有) | - |
| 管理前端 | React | Vue, Svelte |

### 8.2 主要依赖项

```python
# pyproject.toml 新增依赖
dependencies = [
    # 现有依赖
    # ...
    
    # RAG系统依赖
    "firecrawl>=1.0.0",         # 网页爬虫
    "beautifulsoup4>=4.12.0",   # HTML解析
    "trafilatura>=1.6.0",       # 内容提取
    "qdrant-client>=1.7.0",     # 向量数据库客户端
    "sentence-transformers>=2.5.0", # 备用嵌入模型
    "rank-bm25>=0.2.2",         # 关键词检索
    "networkx>=3.2.0",          # 知识图谱构建
    "numpy>=1.26.0",            # 向量操作
    "scikit-learn>=1.4.0",      # 向量处理与评估
    "aiofiles>=23.2.0",         # 异步文件操作
    "tiktoken>=0.5.2",          # Token计数
    "pydantic>=2.5.0",          # 数据验证
]
```

## 9. 风险与缓解

| 风险 | 影响 | 可能性 | 缓解策略 |
|------|------|-------|----------|
| Azure文档结构变化 | 爬虫失效 | 中 | 模块化爬虫设计，监控系统，自动告警 |
| 检索性能问题 | 响应延迟 | 低 | 性能测试，索引优化，缓存机制 |
| 内容准确性问题 | 错误建议 | 中 | 内容审核流程，用户反馈循环 |
| 知识库覆盖不足 | 回答不全面 | 高 | 优先覆盖核心服务，缺口分析填充 |
| API成本超支 | 运营成本增加 | 中 | 批处理嵌入，结果缓存，成本监控 |

## 10. 未来扩展

### 短期扩展 (3-6个月)

1. 多语言支持 - 添加中文等主要语言的文档
2. 个性化检索 - 基于用户历史和偏好优化检索
3. 时间感知RAG - 处理历史价格变化和服务演变

### 中期扩展 (6-12个月)

1. 多模态内容 - 处理架构图和流程图
2. 自适应提示词 - 动态构建最优提示词模板
3. 社区知识集成 - 集成Azure社区内容

### 长期愿景 (1年+)

1. 自主学习RAG - 基于用户交互自动改进
2. 多云比较系统 - 扩展到其他云服务对比
3. 规划助手集成 - 与系统设计和架构建议集成

---

## 附录

### A. 参考资料

1. [Azure文档中心](https://learn.microsoft.com/azure/)
2. [Azure REST API参考](https://learn.microsoft.com/rest/api/azure/)
3. [RAG架构最佳实践](https://example.com/rag-best-practices)
4. [向量数据库比较](https://example.com/vector-db-comparison)

### B. 术语表

| 术语 | 定义 |
|------|------|
| RAG | 检索增强生成 (Retrieval-Augmented Generation) |
| LLM | 大型语言模型 (Large Language Model) |
| 向量嵌入 | 将文本转换为数值向量表示的过程 |
| 语义分块 | 基于语义边界分割文档的技术 |
| 混合检索 | 结合向量和关键词的检索方法 |
| HyDE | 假设文档增强 (Hypothetical Document Embeddings) |
| Self-RAG | 自评估检索增强生成 |

### C. 文档爬取URL示例

```
# Azure虚拟机
https://learn.microsoft.com/azure/virtual-machines/
https://azure.microsoft.com/pricing/details/virtual-machines/

# Azure存储
https://learn.microsoft.com/azure/storage/
https://azure.microsoft.com/pricing/details/storage/

# 完整URL列表附在项目代码库中...
```