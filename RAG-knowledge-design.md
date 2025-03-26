# Azure Calculator RAG知识库系统设计文档

**文档版本:** 1.2.0  
**创建日期:** 2025-03-24  
**最后更新:** 2025-03-25  
**状态:** 草案 (平衡型LlamaIndex集成方案)

## 1. 项目概述

### 1.1 背景

Azure Calculator 目前已实现了基础的LLM集成和对话管理能力，能够为用户提供简单的Azure服务推荐。然而，系统当前依赖的是有限的静态产品数据，缺乏对Azure产品全面、深入的了解，无法提供详细的定价信息、技术限制和最佳实践建议。

为了提升推荐的准确性和全面性，我们需要引入检索增强生成(RAG)系统，构建全面的Azure知识库，为LLM提供实时、精确的参考信息。

### 1.2 目标

1. 构建涵盖Azure所有服务的全面知识库
2. 有选择地利用LlamaIndex框架加速RAG系统开发
3. 实现高度优化的Azure特定检索策略和生成优化
4. 开发管理平台支持知识库维护和RAG系统调优
5. 提供透明的推荐过程，向用户展示决策依据
6. 保持架构灵活性，能够根据需求定制或替换框架组件

### 1.3 关键指标

1. **召回率:** 80%以上的相关文档能被成功检索
2. **精度:** 90%以上的推荐包含准确信息
3. **延迟:** 检索+生成总时间<3秒
4. **覆盖度:** 覆盖所有Azure核心服务(200+服务)
5. **新鲜度:** 知识库与官方文档更新延迟<24小时

## 2. 系统架构

### 2.1 总体架构

RAG知识库系统采用混合架构模式，由五个主要模块组成，有选择地集成LlamaIndex框架：

1. **知识获取系统** - 负责从多个来源收集Azure服务信息，结合LlamaIndex文档加载器与自定义爬虫
2. **内容处理与索引系统** - 处理原始内容并创建向量索引，使用LlamaIndex核心加厚自定义Azure专用处理器
3. **检索引擎** - 实现高效、精准的多策略检索，结合LlamaIndex检索器与自定义Azure查询增强
4. **增强生成系统** - 将检索内容与LLM生成结合，使用定制提示词与LlamaIndex合成器
5. **管理平台** - 提供RAG系统管理和调优功能，自主开发管理界面兼容LlamaIndex评估工具

整体架构图:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           灵活RAG架构（框架无关）                             │
├───────────────┬─────────────────┬───────────────┬────────────────┬──────────┤
│               │                 │               │                │          │
│ 知识获取系统   │  内容处理系统    │   检索引擎     │  增强生成系统   │ 管理平台  │
│               │                 │               │                │          │
└───────┬───────┴────────┬────────┴───────┬───────┴────────┬───────┴────┬─────┘
        │                │                │                │            │
        ▼                ▼                ▼                ▼            ▼
┌───────────────┬─────────────────┬───────────────┬────────────────┬──────────┐
│               │                 │               │                │          │
│ LlamaIndex    │  LlamaIndex +   │  LlamaIndex + │  LlamaIndex +  │自定义管理 │
│ 文档加载器     │  自定义处理      │  自定义策略    │  自定义提示词   │+ 评估工具 │
│               │                 │               │                │          │
└───────────────┴─────────────────┴───────────────┴────────────────┴──────────┘
```

### 2.2 与现有系统集成

RAG系统将与现有的Azure Calculator后端系统集成，通过抽象层与LlamaIndex解耦：

1. `RAGService` - 提供给对话服务的主要接口，屏蔽底层实现细节
2. `DocumentAPI` - 知识库内容查询和管理API，框架无关的接口设计
3. `ConfigAPI` - RAG参数配置API，支持框架通用参数和LlamaIndex特定参数

集成示意图:

```
┌───────────────────────────┐            ┌───────────────────────────────────────┐
│                           │            │                                       │
│   Azure Calculator 现有   │            │     RAG知识库系统 (框架无关设计)        │
│                           │            │                                       │
│ ┌─────────────────────┐   │            │ ┌─────────────────────────────────┐   │
│ │   User Service      │   │            │ │   知识获取系统                   │   │
│ └─────────────────────┘   │            │ │   (可替换的文档加载实现)          │   │
│                           │            │ └─────────────────────────────────┘   │
│ ┌─────────────────────┐   │            │ ┌─────────────────────────────────┐   │
│ │ Conversation Service│◄──┼────────────┼─┤    RAG Service                  │   │
│ └─────────────────────┘   │            │ │    (抽象接口层)                  │   │
│                           │            │ └─────────────────────────────────┘   │
│ ┌─────────────────────┐   │            │ ┌─────────────────────────────────┐   │
│ │    LLM Service      │◄──┼────────────┼─┤   增强生成系统                   │   │
│ └─────────────────────┘   │            │ │   (框架无关的接口)               │   │
│                           │            │ └─────────────────────────────────┘   │
│ ┌─────────────────────┐   │            │ ┌─────────────────────────────────┐   │
│ │   Product Service   │   │            │ │    知识库管理                    │   │
│ └─────────────────────┘   │            │ │    (自定义管理接口)              │   │
│                           │            │ └─────────────────────────────────┘   │
└───────────────────────────┘            └───────────────────────────────────────┘
```

### 2.3 框架独立性策略

为确保系统灵活性，我们设计了分层架构和模块化组件：

1. **抽象接口层**
   - 定义框架无关的RAG系统接口
   - 隔离核心业务逻辑和框架实现细节

2. **适配器模式**
   - 创建LlamaIndex适配器封装框架细节
   - 允许未来无缝切换到其他框架

3. **替换策略**
   - 明确定义可替换组件边界
   - 建立组件性能基准以评估替换价值

4. **自主实现核心差异化能力**
   - Azure特定查询理解和处理
   - 定制化检索策略
   - 针对预算和场景推荐的专用逻辑

## 3. 核心组件设计

### 3.1 知识获取系统

#### 3.1.1 文档加载与爬取

选择性地使用LlamaIndex文档加载器，同时保留自定义爬虫能力：

**框架集成方式**：
```python
from llama_index.readers.web import SimpleWebPageReader
from app.rag.crawler.azure_crawler import AzureCrawlerClient

# 定义抽象文档加载接口
class DocumentLoader(ABC):
    @abstractmethod
    async def load_documents(self, sources):
        """从数据源加载文档"""
        pass

# LlamaIndex实现
class LlamaIndexWebLoader(DocumentLoader):
    def __init__(self):
        self.reader = SimpleWebPageReader(html_to_text=True)
        
    async def load_documents(self, urls):
        """使用LlamaIndex加载Web内容"""
        return self.reader.load_data(urls)

# 自定义爬虫实现
class AzureCustomCrawler(DocumentLoader):
    def __init__(self):
        self.crawler = AzureCrawlerClient()
        
    async def load_documents(self, sources):
        """使用自定义爬虫加载内容"""
        return await self.crawler.crawl_pages(sources)

# 工厂方法创建合适的加载器
def create_document_loader(loader_type, config=None):
    if loader_type == "llama_web":
        return LlamaIndexWebLoader()
    elif loader_type == "azure_crawler":
        return AzureCustomCrawler()
    # 其他加载器类型...
```

**关键特性**:
- 抽象加载接口允许替换底层实现
- 选择性使用LlamaIndex加载器的便利性
- 保留自定义爬虫以处理复杂场景
- 工厂模式使系统配置灵活

#### 3.1.2 数据源管理

实现框架无关的数据源管理，封装LlamaIndex能力：

```python
from pydantic import BaseModel
from enum import Enum
from typing import List, Dict, Any, Optional

# 数据源类型枚举
class SourceType(str, Enum):
    PRODUCT_PAGE = "product_page"
    PRICING_PAGE = "pricing_page"
    TECHNICAL_DOC = "technical_doc"
    BEST_PRACTICE = "best_practice"
    PDF_DOCUMENT = "pdf_document"

# 数据源配置模型
class DataSourceConfig(BaseModel):
    """数据源配置"""
    source_id: str
    source_type: SourceType
    base_urls: List[str]
    crawl_frequency: str
    priority: str
    loader_type: str
    loader_params: Dict[str, Any] = {}
    processing_strategy: str
    metadata_template: Dict[str, Any] = {}

# 数据源管理器
class DataSourceManager:
    def __init__(self, config_store):
        self.config_store = config_store
        self.loader_factory = DocumentLoaderFactory()
        
    async def load_source(self, source_id):
        """加载特定数据源"""
        config = await self.config_store.get_source_config(source_id)
        if not config:
            raise ValueError(f"数据源配置不存在: {source_id}")
            
        # 创建合适的加载器
        loader = self.loader_factory.create_loader(
            config.loader_type, 
            config.loader_params
        )
        
        # 加载文档
        documents = await loader.load_documents(config.base_urls)
        
        # 添加元数据
        for doc in documents:
            doc.metadata.update(config.metadata_template)
            doc.metadata["source_id"] = source_id
            doc.metadata["source_type"] = config.source_type
            
        return documents
        
    async def list_sources(self, filters=None):
        """列出数据源"""
        return await self.config_store.list_source_configs(filters)
        
    async def add_source(self, config):
        """添加数据源"""
        return await self.config_store.add_source_config(config)
        
    async def update_source(self, source_id, config):
        """更新数据源"""
        return await self.config_store.update_source_config(source_id, config)
        
    async def delete_source(self, source_id):
        """删除数据源"""
        return await self.config_store.delete_source_config(source_id)
```

#### 3.1.3 变更检测系统

结合自定义检测逻辑与LlamaIndex的文档更新机制：

```python
from app.rag.crawler.change_detector import HashDetector, ETagDetector, ContentDiffDetector

class ChangeDetectionSystem:
    """文档变更检测系统"""
    
    def __init__(self, doc_store, index_manager):
        self.doc_store = doc_store
        self.index_manager = index_manager
        self.detectors = {
            "hash": HashDetector(),
            "etag": ETagDetector(),
            "content": ContentDiffDetector()
        }
        
    async def check_updates(self, source_id=None):
        """检查文档更新"""
        sources = await self.source_manager.list_sources(
            {"source_id": source_id} if source_id else None
        )
        
        changes = []
        for source in sources:
            detector = self.get_detector(source)
            
            # 加载当前文档
            current_docs = await self.source_manager.load_source(source.source_id)
            
            # 获取已存储文档
            stored_docs = await self.doc_store.get_documents_by_source(source.source_id)
            
            # 检测变更
            changed_docs, deleted_docs = detector.detect_changes(current_docs, stored_docs)
            
            if changed_docs or deleted_docs:
                changes.append({
                    "source_id": source.source_id,
                    "changed": len(changed_docs),
                    "deleted": len(deleted_docs),
                    "documents": {
                        "changed": changed_docs,
                        "deleted": deleted_docs
                    }
                })
                
                # 处理变更
                await self._process_changes(changed_docs, deleted_docs)
                
        return changes
        
    def get_detector(self, source):
        """根据源类型获取检测器"""
        if source.source_type == SourceType.PRICING_PAGE:
            return self.detectors["content"]  # 价格页面使用内容对比
        elif "etag_supported" in source.metadata_template and source.metadata_template["etag_supported"]:
            return self.detectors["etag"]  # 支持ETag的源
        else:
            return self.detectors["hash"]  # 默认使用哈希检测
            
    async def _process_changes(self, changed_docs, deleted_docs):
        """处理变更文档"""
        # 更新文档
        if changed_docs:
            await self.doc_store.update_documents(changed_docs)
            
            # 使用LlamaIndex更新索引
            # 或使用自定义索引更新逻辑
            if self.index_manager.get_type() == "llama_index":
                await self.index_manager.update_documents(changed_docs)
            else:
                await self.index_manager.update_custom_index(changed_docs)
                
        # 删除文档
        if deleted_docs:
            doc_ids = [doc.doc_id for doc in deleted_docs]
            await self.doc_store.delete_documents(doc_ids)
            await self.index_manager.delete_documents(doc_ids)
```

### 3.2 内容处理与索引系统

#### 3.2.1 内容处理架构

实现框架无关的内容处理架构，可选择性使用LlamaIndex组件：

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from llama_index.core.ingestion import IngestionPipeline as LlamaIndexPipeline

# 抽象处理器接口
class DocumentProcessor(ABC):
    @abstractmethod
    async def process(self, documents):
        """处理文档"""
        pass

# LlamaIndex实现
class LlamaIndexProcessor(DocumentProcessor):
    def __init__(self, transformations=None):
        self.pipeline = LlamaIndexPipeline(
            transformations=transformations or []
        )
        
    async def process(self, documents):
        """使用LlamaIndex处理文档"""
        return await self.pipeline.arun(documents=documents)

# 自定义处理器实现
class CustomAzureProcessor(DocumentProcessor):
    def __init__(self, processors=None):
        self.processors = processors or [
            HTMLCleaner(),
            TableExtractor(),
            CodeBlockFormatter(),
            AzureEntityRecognizer()
        ]
        
    async def process(self, documents):
        """使用自定义管道处理文档"""
        result = documents
        for processor in self.processors:
            result = await processor.process(result)
        return result

# 组合处理器
class CompositeProcessor(DocumentProcessor):
    def __init__(self, processors=None):
        self.processors = processors or []
        
    async def process(self, documents):
        """组合多个处理器"""
        result = documents
        for processor in self.processors:
            result = await processor.process(result)
        return result

# 处理器工厂
class ProcessorFactory:
    @staticmethod
    def create_processor(config):
        """创建处理器"""
        processor_type = config.get("type")
        
        if processor_type == "llama_index":
            return LlamaIndexProcessor(
                transformations=config.get("transformations")
            )
        elif processor_type == "azure_custom":
            return CustomAzureProcessor(
                processors=config.get("processors")
            )
        elif processor_type == "composite":
            processors = [
                ProcessorFactory.create_processor(p_config)
                for p_config in config.get("processors", [])
            ]
            return CompositeProcessor(processors=processors)
        else:
            raise ValueError(f"未知的处理器类型: {processor_type}")
```

#### 3.2.2 文档分块策略

结合LlamaIndex分块器与自定义Azure特定分块逻辑：

```python
from llama_index.core.node_parser import SentenceWindowNodeParser
from llama_index.core.node_parser import HierarchicalNodeParser

# 抽象分块器接口
class DocumentSplitter(ABC):
    @abstractmethod
    async def split(self, documents):
        """分割文档为块"""
        pass

# LlamaIndex分块器适配器
class LlamaIndexSplitter(DocumentSplitter):
    def __init__(self, splitter_type, **kwargs):
        if splitter_type == "sentence_window":
            self.splitter = SentenceWindowNodeParser.from_defaults(**kwargs)
        elif splitter_type == "hierarchical":
            self.splitter = HierarchicalNodeParser.from_defaults(**kwargs)
        else:
            raise ValueError(f"未知的LlamaIndex分块器类型: {splitter_type}")
            
    async def split(self, documents):
        """使用LlamaIndex分割文档"""
        return self.splitter.get_nodes_from_documents(documents)

# Azure特定分块器
class AzureServiceSplitter(DocumentSplitter):
    """Azure服务文档专用分块器"""
    
    def __init__(self):
        # 初始化Azure服务特定的分块规则
        self.section_patterns = [
            r"## (.*?)\n",  # Markdown二级标题
            r"<h2>(.*?)</h2>",  # HTML二级标题
            r"服务概述",  # 常见服务概述部分
            r"定价详情",  # 价格部分
            r"常见问题"   # FAQ部分
        ]
        
    async def split(self, documents):
        """基于Azure文档结构的智能分块"""
        nodes = []
        
        for doc in documents:
            # 基于特定模式分块
            chunks = self._split_by_patterns(doc.text, self.section_patterns)
            
            # 创建节点
            for i, chunk in enumerate(chunks):
                node = TextNode(
                    text=chunk["text"],
                    metadata={
                        **doc.metadata,
                        "section_title": chunk.get("title"),
                        "section_type": chunk.get("type"),
                        "chunk_id": f"{doc.doc_id}_chunk_{i}"
                    }
                )
                nodes.append(node)
                
        return nodes
        
    def _split_by_patterns(self, text, patterns):
        """根据模式分割文本"""
        # 实现基于Azure文档结构特点的分块逻辑
        # ...

# 工厂方法
def create_splitter(config):
    """创建分块器"""
    splitter_type = config.get("type")
    
    if "llama_index" in splitter_type:
        kwargs = config.get("params", {})
        splitter_name = splitter_type.replace("llama_index_", "")
        return LlamaIndexSplitter(splitter_name, **kwargs)
    elif splitter_type == "azure_service":
        return AzureServiceSplitter()
    else:
        raise ValueError(f"未知的分块器类型: {splitter_type}")
```

#### 3.2.3 元数据提取与增强

实现自定义Azure元数据提取，同时利用LlamaIndex提取器：

```python
from llama_index.core.extractors import MetadataExtractor

# 基础元数据提取器接口
class MetadataEnricher(ABC):
    @abstractmethod
    async def enrich(self, nodes):
        """为节点添加元数据"""
        pass

# LlamaIndex元数据提取器适配
class LlamaMetadataExtractor(MetadataEnricher):
    def __init__(self, extractors):
        """初始化LlamaIndex提取器"""
        self.extractor = MetadataExtractor(extractors=extractors)
        
    async def enrich(self, nodes):
        """使用LlamaIndex提取元数据"""
        return self.extractor.extract(nodes)

# Azure服务元数据提取器
class AzureServiceMetadataEnricher(MetadataEnricher):
    def __init__(self, catalog_service):
        """初始化Azure服务提取器"""
        self.catalog = catalog_service
        self.service_patterns = self._compile_patterns()
        self.region_patterns = self._compile_region_patterns()
        
    async def enrich(self, nodes):
        """提取Azure特定元数据"""
        enriched_nodes = []
        
        for node in nodes:
            # 获取节点文本和现有元数据
            text = node.text
            metadata = node.metadata
            
            # 提取服务信息
            services = self._extract_services(text)
            if services:
                metadata["azure_services"] = services
                
                # 获取主要服务详情
                primary_service = services[0]
                service_details = await self.catalog.get_service_details(primary_service)
                if service_details:
                    metadata["service_category"] = service_details.category
                    metadata["service_tier"] = service_details.tier
            
            # 提取区域信息
            regions = self._extract_regions(text)
            if regions:
                metadata["azure_regions"] = regions
                
            # 提取价格信息
            if "pricing" in text.lower() or "cost" in text.lower():
                price_data = self._extract_price_data(text)
                if price_data:
                    metadata["price_data"] = price_data
            
            # 更新节点元数据
            node.metadata = metadata
            enriched_nodes.append(node)
            
        return enriched_nodes
        
    def _extract_services(self, text):
        """提取提到的Azure服务"""
        # 实现Azure服务名称识别
        # ...
        
    def _extract_regions(self, text):
        """提取提到的Azure区域"""
        # 实现Azure区域识别
        # ...
        
    def _extract_price_data(self, text):
        """提取价格相关数据"""
        # 实现价格数据提取
        # ...
```

#### 3.2.4 索引系统架构

设计灵活的索引系统，支持LlamaIndex和自定义索引：

```python
# 抽象索引接口
class VectorIndex(ABC):
    @abstractmethod
    async def index_documents(self, documents):
        """索引文档"""
        pass
        
    @abstractmethod
    async def search(self, query, **kwargs):
        """搜索索引"""
        pass
        
    @abstractmethod
    async def update_documents(self, documents):
        """更新文档"""
        pass
        
    @abstractmethod
    async def delete_documents(self, doc_ids):
        """删除文档"""
        pass

# LlamaIndex实现
class LlamaVectorIndex(VectorIndex):
    def __init__(self, embed_model, vector_store=None):
        from llama_index.core import VectorStoreIndex
        from llama_index.vector_stores.qdrant import QdrantVectorStore
        
        self.embed_model = embed_model
        self.vector_store = vector_store or QdrantVectorStore(
            client=QdrantClient(url=QDRANT_URL),
            collection_name="azure_docs"
        )
        self.index = None
        
    async def index_documents(self, documents):
        """使用LlamaIndex索引文档"""
        self.index = VectorStoreIndex.from_documents(
            documents,
            embed_model=self.embed_model,
            vector_store=self.vector_store
        )
        return True
        
    async def search(self, query, **kwargs):
        """使用LlamaIndex搜索"""
        if not self.index:
            raise ValueError("索引尚未初始化")
            
        retriever = self.index.as_retriever(
            similarity_top_k=kwargs.get("top_k", 5)
        )
        return await retriever.aretrieve(query)
        
    async def update_documents(self, documents):
        """更新索引中的文档"""
        if not self.index:
            raise ValueError("索引尚未初始化")
            
        for doc in documents:
            # 处理文档到节点
            from llama_index.core.node_parser import SimpleNodeParser
            parser = SimpleNodeParser.from_defaults()
            nodes = parser.get_nodes_from_documents([doc])
            
            # 更新索引
            for node in nodes:
                await self.index.ainsert(node)
                
        return True
        
    async def delete_documents(self, doc_ids):
        """从索引中删除文档"""
        if not self.index:
            raise ValueError("索引尚未初始化")
            
        for doc_id in doc_ids:
            await self.index.adelete(doc_id)
            
        return True

# 自定义Azure索引
class AzureCustomVectorIndex(VectorIndex):
    def __init__(self, embedding_service, db_client):
        self.embedding_service = embedding_service
        self.db_client = db_client
        
    async def index_documents(self, documents):
        """自定义文档索引逻辑"""
        # 实现特定于Azure服务的索引创建
        # ...
    
    async def search(self, query, **kwargs):
        """自定义搜索逻辑"""
        # 实现Azure特定的检索逻辑
        # ...
        
    async def update_documents(self, documents):
        """自定义更新逻辑"""
        # ...
        
    async def delete_documents(self, doc_ids):
        """自定义删除逻辑"""
        # ...

# 索引工厂
class IndexFactory:
    @staticmethod
    def create_index(config):
        """创建索引实例"""
        index_type = config.get("type")
        
        if index_type == "llama_index":
            from llama_index.embeddings.openai import OpenAIEmbedding
            
            embed_model = OpenAIEmbedding(
                model=config.get("embed_model", "text-embedding-ada-002")
            )
            return LlamaVectorIndex(embed_model=embed_model)
        elif index_type == "azure_custom":
            from app.services.embedding import EmbeddingService
            from app.db.vector_client import VectorDBClient
            
            embedding_service = EmbeddingService()
            db_client = VectorDBClient()
            return AzureCustomVectorIndex(embedding_service, db_client)
        else:
            raise ValueError(f"未知的索引类型: {index_type}")
```

### 3.3 检索引擎

#### 3.3.1 查询理解与转换

构建强大的Azure专用查询理解，与LlamaIndex查询转换器结合：

```python
# 查询转换接口
class QueryTransformer(ABC):
    @abstractmethod
    async def transform(self, query):
        """转换原始查询"""
        pass

# LlamaIndex查询转换器
class LlamaIndexQueryTransformer(QueryTransformer):
    def __init__(self, transform_type, **kwargs):
        from llama_index.core.query_transform import HyDEQueryTransform
        from llama_index.core.query_transform import StepDecomposeQueryTransform
        
        if transform_type == "hyde":
            self.transformer = HyDEQueryTransform(**kwargs)
        elif transform_type == "decompose":
            self.transformer = StepDecomposeQueryTransform(**kwargs)
        else:
            raise ValueError(f"未知的LlamaIndex转换器类型: {transform_type}")
            
    async def transform(self, query):
        """使用LlamaIndex转换查询"""
        return self.transformer(query)

# Azure术语扩展转换器
class AzureTermExpander(QueryTransformer):
    def __init__(self, catalog_service):
        self.catalog = catalog_service
        self.term_mappings = {
            "VM": "Virtual Machine",
            "AKS": "Azure Kubernetes Service",
            "ACI": "Azure Container Instances",
            "APIM": "API Management",
            # 更多Azure特定缩写和术语
        }
        
    async def transform(self, query):
        """扩展Azure特定术语"""
        expanded_query = query
        
        # 替换缩写和术语
        for abbr, full in self.term_mappings.items():
            pattern = r'\b' + abbr + r'\b'
            expanded_query = re.sub(pattern, full, expanded_query)
            
        # 动态加载服务列表
        services = await self.catalog.list_services()
        
        # 识别查询中提到的服务
        mentioned_services = []
        for service in services:
            if service.name.lower() in query.lower():
                mentioned_services.append(service.name)
                
        # 创建增强查询
        if mentioned_services:
            expanded_query = f"{expanded_query} (关于 {', '.join(mentioned_services)})"
            
        return expanded_query

# 查询意图分类器
class AzureQueryClassifier:
    def __init__(self, llm):
        self.llm = llm
        self.intents = [
            "pricing_query",      # 定价查询
            "comparison_query",   # 服务比较
            "technical_query",    # 技术问题
            "limitation_query",   # 限制查询
            "recommendation_query" # 推荐请求
        ]
        
    async def classify(self, query):
        """识别查询意图"""
        prompt = f"""
        分析以下查询，判断它属于哪种类型：
        - pricing_query: 关于Azure服务价格的查询
        - comparison_query: 比较不同Azure服务的查询
        - technical_query: 关于Azure服务技术细节的查询
        - limitation_query: 关于Azure服务限制或配额的查询
        - recommendation_query: 请求推荐最佳Azure服务的查询
        
        查询: {query}
        
        查询类型:
        """
        
        response = await self.llm.acomplete(prompt)
        for intent in self.intents:
            if intent in response.lower():
                return intent
                
        return "general_query"  # 默认类型

# 查询引擎工厂
class QueryEngineFactory:
    def __init__(self, config, llm, catalog_service):
        self.config = config
        self.llm = llm
        self.catalog = catalog_service
        
    def create_transformer_pipeline(self, query_type):
        """创建查询转换管道"""
        transformers = []
        
        # 基础转换器
        transformers.append(AzureTermExpander(self.catalog))
        
        # 根据查询类型添加特定转换器
        if query_type == "pricing_query":
            transformers.append(
                LlamaIndexQueryTransformer("hyde", llm=self.llm)
            )
        elif query_type == "comparison_query":
            transformers.append(
                LlamaIndexQueryTransformer("decompose", llm=self.llm)
            )
        
        return transformers
        
    async def transform_query(self, query):
        """转换查询"""
        # 分类查询
        classifier = AzureQueryClassifier(self.llm)
        query_type = await classifier.classify(query)
        
        # 获取转换器
        transformers = self.create_transformer_pipeline(query_type)
        
        # 应用转换
        transformed_query = query
        for transformer in transformers:
            transformed_query = await transformer.transform(transformed_query)
            
        return {
            "original_query": query,
            "transformed_query": transformed_query,
            "query_type": query_type
        }
```

#### 3.3.2 多路径检索

实现强大的多路径检索，将LlamaIndex检索器与自定义逻辑相结合：

```python
# 抽象检索器接口
class Retriever(ABC):
    @abstractmethod
    async def retrieve(self, query, **kwargs):
        """检索相关内容"""
        pass

# LlamaIndex检索器适配
class LlamaIndexRetriever(Retriever):
    def __init__(self, index, retriever_type, **kwargs):
        self.index = index
        
        if retriever_type == "vector":
            self.retriever = index.as_retriever(
                similarity_top_k=kwargs.get("top_k", 5)
            )
        elif retriever_type == "keyword":
            from llama_index.core.retrievers import KeywordTableRetriever
            
            self.retriever = KeywordTableRetriever(
                index=index,
                top_k=kwargs.get("top_k", 5)
            )
        elif retriever_type == "bm25":
            from llama_index.retrievers.bm25 import BM25Retriever
            
            self.retriever = BM25Retriever.from_defaults(
                docstore=index.docstore,
                similarity_top_k=kwargs.get("top_k", 5)
            )
        else:
            raise ValueError(f"未知的LlamaIndex检索器类型: {retriever_type}")
            
    async def retrieve(self, query, **kwargs):
        """使用LlamaIndex检索"""
        return await self.retriever.aretrieve(query)

# Azure特定检索器
class AzureServiceRetriever(Retriever):
    def __init__(self, db_client, embedding_service):
        self.db_client = db_client
        self.embedding_service = embedding_service
        
    async def retrieve(self, query, **kwargs):
        """Azure专用检索逻辑"""
        # 获取查询嵌入
        query_embedding = await self.embedding_service.get_embedding(query)
        
        # 执行向量检索
        top_k = kwargs.get("top_k", 5)
        vector_results = await self.db_client.search_by_vector(
            query_embedding, 
            top_k=top_k,
            filters=kwargs.get("filters")
        )
        
        # 应用Azure特定排序逻辑
        results = self._apply_azure_ranking(query, vector_results)
        
        return results
        
    def _apply_azure_ranking(self, query, results):
        """应用Azure特定的结果排序逻辑"""
        # 基于Azure服务知识的结果重排序
        # ...

# 多路径检索系统
class MultiPathRetriever(Retriever):
    def __init__(self, retrievers, fusion_strategy="reciprocal_rank"):
        self.retrievers = retrievers
        self.fusion_strategy = fusion_strategy
        
    async def retrieve(self, query, **kwargs):
        """执行多路径检索并融合结果"""
        # 并行执行所有检索器
        all_results = []
        for retriever in self.retrievers:
            results = await retriever.retrieve(query, **kwargs)
            all_results.append(results)
            
        # 融合结果
        if self.fusion_strategy == "reciprocal_rank":
            fused_results = self._reciprocal_rank_fusion(all_results)
        elif self.fusion_strategy == "round_robin":
            fused_results = self._round_robin_fusion(all_results)
        else:
            raise ValueError(f"未知的融合策略: {self.fusion_strategy}")
            
        return fused_results
        
    def _reciprocal_rank_fusion(self, result_lists):
        """倒数排名融合"""
        # 实现RRF融合算法
        # ...
        
    def _round_robin_fusion(self, result_lists):
        """轮询融合"""
        # 实现轮询融合算法
        # ...

# 检索系统工厂
class RetrieverFactory:
    def __init__(self, indices, db_client, embedding_service):
        self.indices = indices
        self.db_client = db_client
        self.embedding_service = embedding_service
        
    def create_retriever(self, config):
        """创建检索器"""
        retriever_type = config.get("type")
        
        if "llama_index" in retriever_type:
            # 解析具体的LlamaIndex检索器类型
            llama_type = retriever_type.replace("llama_index_", "")
            index_name = config.get("index", "default")
            
            return LlamaIndexRetriever(
                index=self.indices[index_name],
                retriever_type=llama_type,
                **config.get("params", {})
            )
        elif retriever_type == "azure_service":
            return AzureServiceRetriever(
                db_client=self.db_client,
                embedding_service=self.embedding_service
            )
        elif retriever_type == "multi_path":
            # 创建多路径检索器
            retrievers = [
                self.create_retriever(r_config)
                for r_config in config.get("retrievers", [])
            ]
            
            return MultiPathRetriever(
                retrievers=retrievers,
                fusion_strategy=config.get("fusion", "reciprocal_rank")
            )
        else:
            raise ValueError(f"未知的检索器类型: {retriever_type}")
```

#### 3.3.3 结果精炼

高级结果处理，包括自定义排序和LlamaIndex重排序器：

```python
# 节点后处理器接口
class NodePostprocessor(ABC):
    @abstractmethod
    async def process(self, nodes, query):
        """处理检索节点"""
        pass

# LlamaIndex后处理器适配
class LlamaIndexPostprocessor(NodePostprocessor):
    def __init__(self, processor_type, **kwargs):
        from llama_index.core.postprocessor import SimilarityPostprocessor
        from llama_index.core.postprocessor import KeywordNodePostprocessor
        from llama_index.core.postprocessor import LLMRerank
        
        if processor_type == "similarity":
            self.processor = SimilarityPostprocessor(**kwargs)
        elif processor_type == "keyword":
            self.processor = KeywordNodePostprocessor(**kwargs)
        elif processor_type == "rerank":
            self.processor = LLMRerank(**kwargs)
        else:
            raise ValueError(f"未知的LlamaIndex后处理器类型: {processor_type}")
            
    async def process(self, nodes, query):
        """使用LlamaIndex处理节点"""
        # 转换节点格式以符合LlamaIndex期望
        # ...
        processed = self.processor.postprocess_nodes(nodes, query)
        # 转换回我们的格式
        # ...
        return processed

# Azure特定结果精炼器
class AzureResultRefiner(NodePostprocessor):
    def __init__(self, catalog_service):
        self.catalog = catalog_service
        
    async def process(self, nodes, query):
        """Azure特定结果精炼"""
        # 识别查询中的服务
        services = self._extract_services(query)
        
        # 应用优先级规则
        if services:
            # 提升包含这些服务的节点
            nodes = self._prioritize_service_nodes(nodes, services)
            
        # 去除冗余内容
        nodes = self._remove_redundancy(nodes)
        
        # 验证内容新鲜度
        nodes = await self._verify_freshness(nodes)
        
        return nodes
        
    def _extract_services(self, query):
        """从查询中提取服务名称"""
        # ...
        
    def _prioritize_service_nodes(self, nodes, services):
        """提升包含特定服务的节点"""
        # ...
        
    def _remove_redundancy(self, nodes):
        """去除冗余内容"""
        # ...
        
    async def _verify_freshness(self, nodes):
        """验证内容新鲜度"""
        # ...

# 后处理管道
class PostprocessingPipeline:
    def __init__(self, processors=None):
        self.processors = processors or []
        
    async def process(self, nodes, query):
        """应用所有后处理器"""
        result = nodes
        for processor in self.processors:
            result = await processor.process(result, query)
        return result

# 后处理工厂
class PostprocessorFactory:
    def __init__(self, catalog_service, llm):
        self.catalog = catalog_service
        self.llm = llm
        
    def create_postprocessor(self, config):
        """创建后处理器"""
        processor_type = config.get("type")
        
        if "llama_index" in processor_type:
            llama_type = processor_type.replace("llama_index_", "")
            kwargs = config.get("params", {})
            
            # 如果需要LLM，添加它
            if llama_type == "rerank":
                kwargs["llm"] = self.llm
                
            return LlamaIndexPostprocessor(
                processor_type=llama_type,
                **kwargs
            )
        elif processor_type == "azure_refiner":
            return AzureResultRefiner(self.catalog)
        else:
            raise ValueError(f"未知的后处理器类型: {processor_type}")
            
    def create_pipeline(self, configs):
        """创建后处理管道"""
        processors = [
            self.create_postprocessor(config)
            for config in configs
        ]
        
        return PostprocessingPipeline(processors=processors)
```

### 3.4 增强生成系统

#### 3.4.1 上下文构建

高级上下文构建器，结合LlamaIndex和Azure专用上下文优化：

```python
# 上下文构建器接口
class ContextBuilder(ABC):
    @abstractmethod
    async def build(self, query, nodes, query_type=None):
        """构建LLM上下文"""
        pass

# LlamaIndex响应合成器适配
class LlamaIndexContextBuilder(ContextBuilder):
    def __init__(self, response_mode, llm):
        from llama_index.core.response_synthesizers import TreeSummarize
        from llama_index.core.response_synthesizers import RefineResponseSynthesizer
        from llama_index.core.response_synthesizers import CompactAndRefine
        
        if response_mode == "tree":
            self.synthesizer = TreeSummarize.from_args(llm=llm)
        elif response_mode == "refine":
            self.synthesizer = RefineResponseSynthesizer.from_args(llm=llm)
        elif response_mode == "compact":
            self.synthesizer = CompactAndRefine.from_args(llm=llm)
        else:
            raise ValueError(f"未知的LlamaIndex响应模式: {response_mode}")
            
    async def build(self, query, nodes, query_type=None):
        """使用LlamaIndex构建上下文"""
        # 将节点转换为LlamaIndex格式
        llama_nodes = self._convert_to_llama_nodes(nodes)
        
        # 使用LlamaIndex合成器生成响应
        response = await self.synthesizer.asynthesize(
            query=query,
            nodes=llama_nodes
        )
        
        return {
            "context": response.response,
            "source_nodes": response.source_nodes,
            "prompt": response.prompt
        }
        
    def _convert_to_llama_nodes(self, nodes):
        """转换节点为LlamaIndex格式"""
        # ...

# Azure特定上下文构建器
class AzureContextBuilder(ContextBuilder):
    def __init__(self, catalog_service):
        self.catalog = catalog_service
        self.strategies = {
            "pricing_query": self._build_pricing_context,
            "comparison_query": self._build_comparison_context,
            "technical_query": self._build_technical_context,
            "recommendation_query": self._build_recommendation_context,
            "general_query": self._build_general_context
        }
        
    async def build(self, query, nodes, query_type=None):
        """构建Azure特定上下文"""
        # 选择合适的构建策略
        strategy = self.strategies.get(
            query_type or "general_query", 
            self._build_general_context
        )
        
        # 构建上下文
        context = await strategy(query, nodes)
        
        return context
        
    async def _build_pricing_context(self, query, nodes):
        """构建价格查询上下文"""
        # 提取价格相关信息
        pricing_info = self._extract_pricing_info(nodes)
        
        # 获取服务详情
        services = self._extract_services(query)
        service_details = await self._get_service_details(services)
        
        # 组织上下文
        context = f"""
        ## 价格信息
        
        {pricing_info}
        
        ## 服务详情
        
        {service_details}
        """
        
        return {
            "context": context,
            "source_nodes": nodes,
            "context_type": "pricing"
        }
        
    async def _build_comparison_context(self, query, nodes):
        """构建比较查询上下文"""
        # ...
        
    async def _build_technical_context(self, query, nodes):
        """构建技术查询上下文"""
        # ...
        
    async def _build_recommendation_context(self, query, nodes):
        """构建推荐查询上下文"""
        # ...
        
    async def _build_general_context(self, query, nodes):
        """构建通用查询上下文"""
        # ...
        
    def _extract_pricing_info(self, nodes):
        """从节点中提取价格信息"""
        # ...
        
    def _extract_services(self, query):
        """从查询中提取服务"""
        # ...
        
    async def _get_service_details(self, services):
        """获取服务详情"""
        # ...

# 上下文构建器工厂
class ContextBuilderFactory:
    def __init__(self, catalog_service, llm):
        self.catalog = catalog_service
        self.llm = llm
        
    def create_builder(self, config):
        """创建上下文构建器"""
        builder_type = config.get("type")
        
        if "llama_index" in builder_type:
            response_mode = builder_type.replace("llama_index_", "")
            return LlamaIndexContextBuilder(
                response_mode=response_mode,
                llm=self.llm
            )
        elif builder_type == "azure":
            return AzureContextBuilder(self.catalog)
        else:
            raise ValueError(f"未知的上下文构建器类型: {builder_type}")
```

#### 3.4.2 提示词工程

构建强大的提示词模板系统，包含Azure特定模板和LlamaIndex接口：

```python
from string import Template
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from llama_index.core.prompts import PromptTemplate as LlamaPromptTemplate

# 提示词模板接口
class PromptTemplate(ABC):
    @abstractmethod
    async def format(self, **kwargs):
        """格式化提示词"""
        pass

# 简单提示词模板
class SimplePromptTemplate(PromptTemplate):
    def __init__(self, template_str):
        self.template = Template(template_str)
        
    async def format(self, **kwargs):
        """格式化简单提示词模板"""
        return self.template.safe_substitute(**kwargs)

# LlamaIndex提示词模板适配
class LlamaIndexPromptTemplate(PromptTemplate):
    def __init__(self, template_str, template_type="default"):
        if template_type == "default":
            self.template = LlamaPromptTemplate(template_str)
        else:
            # 支持其他LlamaIndex模板类型
            pass
            
    async def format(self, **kwargs):
        """使用LlamaIndex格式化提示词"""
        return self.template.format(**kwargs)

# Azure服务助手提示词模板
class AzureAdvisorPrompt(PromptTemplate):
    def __init__(self, template_type="general"):
        self.template_type = template_type
        self.templates = {
            "general": self._get_general_template(),
            "pricing": self._get_pricing_template(),
            "comparison": self._get_comparison_template(),
            "technical": self._get_technical_template(),
            "recommendation": self._get_recommendation_template()
        }
        self.template = self.templates.get(template_type, self.templates["general"])
        
    async def format(self, **kwargs):
        """格式化Azure助手提示词"""
        # 添加当前日期
        from datetime import datetime
        kwargs["current_date"] = datetime.now().strftime("%Y-%m-%d")
        
        # 检查是否包含必要参数
        required_params = ["context", "query"]
        for param in required_params:
            if param not in kwargs:
                raise ValueError(f"缺少必要参数: {param}")
                
        return self.template.safe_substitute(**kwargs)
        
    def _get_general_template(self):
        """通用Azure助手模板"""
        return Template("""
        你是一名Azure云服务专家助手，擅长提供关于Azure服务的准确、最新信息。
        今天是 ${current_date}。
        基于以下提供的信息来回答问题。保持专业和有帮助的态度。
        
        背景信息:
        ${context}
        
        用户问题: ${query}
        
        在回答时：
        1. 提供准确、最新的信息
        2. 引用相关的Azure文档
        3. 如果信息不足，明确说明
        4. 保持回答简洁和有条理
        """)
        
    def _get_pricing_template(self):
        """价格查询模板"""
        return Template("""
        你是一名Azure云服务定价专家，擅长解释Azure服务的价格模型和成本优化。
        今天是 ${current_date}。
        
        基于以下价格信息回答用户的Azure定价问题：
        
        ${context}
        
        用户的价格查询: ${query}
        
        在回答时：
        1. 提供准确的价格信息，包括所有相关定价模型（即用即付、预留实例等）
        2. 解释可能影响价格的因素（区域、层级、选项等）
        3. 在适当时提供成本优化建议
        4. 说明价格可能随时间变化，并建议查看官方定价页面获取最新信息
        """)
        
    def _get_comparison_template(self):
        """比较查询模板"""
        return Template("""
        你是一名Azure云服务对比分析专家，擅长比较不同Azure服务的优缺点。
        今天是 ${current_date}。
        
        基于以下信息比较这些Azure服务：
        
        ${context}
        
        用户的比较请求: ${query}
        
        在回答时：
        1. 公平客观地比较服务的关键特性
        2. 使用表格清晰展示主要差异点（功能、性能、价格、限制等）
        3. 说明每种服务的最佳使用场景
        4. 给出基于用户需求的建议，但避免过度倾向某一服务
        """)
        
    def _get_technical_template(self):
        # 技术查询模板
        # ...
        
    def _get_recommendation_template(self):
        # 推荐查询模板
        # ...

# 提示词模板工厂
class PromptTemplateFactory:
    @staticmethod
    def create_template(config):
        """创建提示词模板"""
        template_type = config.get("type")
        
        if template_type == "simple":
            return SimplePromptTemplate(config.get("template"))
        elif "llama_index" in template_type:
            llama_type = template_type.replace("llama_index_", "")
            return LlamaIndexPromptTemplate(
                template_str=config.get("template"),
                template_type=llama_type
            )
        elif template_type == "azure_advisor":
            return AzureAdvisorPrompt(
                template_type=config.get("advisor_type", "general")
            )
        else:
            raise ValueError(f"未知的提示词模板类型: {template_type}")
```

#### 3.4.3 透明度与引用

实现高质量引用系统，包括LlamaIndex引用与自定义Azure引用：

```python
# 引用处理器接口
class ReferenceProcessor(ABC):
    @abstractmethod
    async def process_references(self, response, source_nodes):
        """处理引用"""
        pass

# LlamaIndex引用处理器
class LlamaIndexReferenceProcessor(ReferenceProcessor):
    def __init__(self):
        pass
        
    async def process_references(self, response, source_nodes):
        """使用LlamaIndex处理引用"""
        from llama_index.core.response.notebook_utils import display_source_node
        
        references = []
        for i, node in enumerate(source_nodes):
            ref = {
                "id": f"[{i+1}]",
                "text": node.text[:200] + "..." if len(node.text) > 200 else node.text,
                "metadata": node.metadata
            }
            references.append(ref)
            
        return {
            "response": response,
            "references": references
        }

# Azure文档引用处理器
class AzureReferenceProcessor(ReferenceProcessor):
    def __init__(self, catalog_service):
        self.catalog = catalog_service
        
    async def process_references(self, response, source_nodes):
        """处理Azure文档引用"""
        # 提取引用
        references = []
        for i, node in enumerate(source_nodes):
            # 获取基本引用信息
            metadata = node.metadata
            
            # 构建引用对象
            ref = {
                "id": f"[{i+1}]",
                "title": metadata.get("title", "Azure文档"),
                "url": metadata.get("url", ""),
                "service": metadata.get("service", ""),
                "doc_type": metadata.get("doc_type", ""),
                "last_updated": metadata.get("last_updated", ""),
                "section": metadata.get("section", ""),
                "preview": node.text[:200] + "..." if len(node.text) > 200 else node.text
            }
            
            # 尝试获取更完整的服务信息
            if ref["service"]:
                service_info = await self.catalog.get_service_info(ref["service"])
                if service_info:
                    ref["service_display_name"] = service_info.display_name
                    ref["service_category"] = service_info.category
            
            references.append(ref)
            
        # 在回答中标记引用
        marked_response = self._mark_references_in_text(response, references)
            
        return {
            "response": marked_response,
            "references": references
        }
        
    def _mark_references_in_text(self, response, references):
        """在文本中标记引用"""
        marked_text = response
        
        # 为引用中提到的服务添加引用标记
        for ref in references:
            if ref["service"]:
                # 在文本中查找服务名称
                service_name = ref["service_display_name"] or ref["service"]
                pattern = r'\b' + re.escape(service_name) + r'\b(?!\[\d+\])'
                replacement = f"{service_name} {ref['id']}"
                marked_text = re.sub(pattern, replacement, marked_text)
                
        return marked_text

# 引用处理器工厂
class ReferenceProcessorFactory:
    def __init__(self, catalog_service):
        self.catalog = catalog_service
        
    def create_processor(self, processor_type):
        """创建引用处理器"""
        if processor_type == "llama_index":
            return LlamaIndexReferenceProcessor()
        elif processor_type == "azure":
            return AzureReferenceProcessor(self.catalog)
        else:
            raise ValueError(f"未知的引用处理器类型: {processor_type}")
```

#### 3.4.4 自评估与修正

构建高级自评估系统，结合LlamaIndex评估器与Azure特定检查：

```python
# 自评估器接口
class SelfEvaluator(ABC):
    @abstractmethod
    async def evaluate(self, query, response, context, source_nodes):
        """评估回答质量"""
        pass
        
    @abstractmethod
    async def improve(self, query, response, evaluation, context):
        """改进回答"""
        pass

# LlamaIndex评估器适配
class LlamaIndexEvaluator(SelfEvaluator):
    def __init__(self, llm):
        from llama_index.core.evaluation import FaithfulnessEvaluator
        from llama_index.core.evaluation import RelevancyEvaluator
        
        self.llm = llm
        self.evaluators = {
            "faithfulness": FaithfulnessEvaluator.from_args(llm=llm),
            "relevancy": RelevancyEvaluator.from_args(llm=llm)
        }
        
    async def evaluate(self, query, response, context, source_nodes):
        """使用LlamaIndex评估回答"""
        results = {}
        
        # 转换为LlamaIndex格式
        llama_context = self._to_llama_format(context, source_nodes)
        
        # 评估忠实度
        faith_result = await self.evaluators["faithfulness"].aevaluate_response(
            query=query,
            response=response,
            contexts=[llama_context]
        )
        results["faithfulness"] = {
            "score": faith_result.score,
            "feedback": faith_result.feedback
        }
        
        # 评估相关性
        rel_result = await self.evaluators["relevancy"].aevaluate_response(
            query=query,
            response=response
        )
        results["relevancy"] = {
            "score": rel_result.score,
            "feedback": rel_result.feedback
        }
        
        # 确定是否需要修正
        needs_correction = any(
            result["score"] < 0.7 for result in results.values()
        )
        
        return {
            "results": results,
            "needs_correction": needs_correction
        }
        
    async def improve(self, query, response, evaluation, context):
        """使用LlamaIndex改进回答"""
        if not evaluation["needs_correction"]:
            return response
            
        # 准备修正提示词
        correction_feedback = "\n".join(
            f"{name}: 评分 {result['score']}, 反馈: {result['feedback']}"
            for name, result in evaluation["results"].items()
        )
        
        prompt = f"""
        原始回答:
        {response}
        
        评估反馈:
        {correction_feedback}
        
        原始问题:
        {query}
        
        背景信息:
        {context}
        
        请根据上述反馈修正回答，确保回答忠实于提供的信息并与问题高度相关。
        """
        
        # 生成修正回答
        corrected_response = await self.llm.acomplete(prompt)
        
        return corrected_response
        
    def _to_llama_format(self, context, source_nodes):
        """转换为LlamaIndex格式"""
        # ...

# Azure特定评估器
class AzureResponseEvaluator(SelfEvaluator):
    def __init__(self, llm, catalog_service):
        self.llm = llm
        self.catalog = catalog_service
        
    async def evaluate(self, query, response, context, source_nodes):
        """评估Azure响应质量"""
        # 执行各种Azure特定检查
        results = {}
        
        # 1. 价格准确性检查
        if self._is_pricing_query(query):
            price_check = await self._check_pricing_accuracy(response, source_nodes)
            results["price_accuracy"] = price_check
            
        # 2. 服务兼容性检查
        compatibility_check = await self._check_service_compatibility(response)
        results["service_compatibility"] = compatibility_check
        
        # 3. 最新性检查
        freshness_check = await self._check_freshness(response, source_nodes)
        results["freshness"] = freshness_check
        
        # 4. 建议质量检查
        if self._is_recommendation_query(query):
            recommendation_check = await self._check_recommendation_quality(response, query)
            results["recommendation_quality"] = recommendation_check
            
        # 5. 整体质量 (使用LLM)
        overall_quality = await self._assess_overall_quality(query, response, context)
        results["overall_quality"] = overall_quality
        
        # 确定是否需要修正
        major_issues = [
            r for r in results.values() 
            if r.get("score", 1.0) < 0.6 or r.get("critical_issue", False)
        ]
        needs_correction = len(major_issues) > 0
        
        return {
            "results": results,
            "needs_correction": needs_correction,
            "critical_issues": major_issues
        }
        
    async def improve(self, query, response, evaluation, context):
        """改进Azure响应"""
        if not evaluation["needs_correction"]:
            return response
            
        # 准备修正提示词
        critical_issues = "\n".join(
            f"- {issue.get('name', 'Issue')}: {issue.get('feedback', '')}"
            for issue in evaluation.get("critical_issues", [])
        )
        
        # 获取服务特定信息
        services = self._extract_services(query)
        service_info = ""
        for service in services:
            details = await self.catalog.get_service_info(service)
            if details:
                service_info += f"- {details.display_name}: {details.short_description}\n"
        
        prompt = f"""
        作为Azure专家，请修正以下回答中的问题:
        
        原始问题:
        {query}
        
        原始回答:
        {response}
        
        需要修正的关键问题:
        {critical_issues}
        
        相关服务信息:
        {service_info}
        
        背景信息:
        {context}
        
        请提供修正后的回答，确保解决上述所有问题。保持专业口吻并注意回答的准确性。
        """
        
        # 生成修正回答
        corrected_response = await self.llm.acomplete(prompt)
        
        return corrected_response
        
    def _is_pricing_query(self, query):
        """判断是否为价格查询"""
        # ...
        
    def _is_recommendation_query(self, query):
        """判断是否为推荐查询"""
        # ...
        
    async def _check_pricing_accuracy(self, response, source_nodes):
        """检查价格准确性"""
        # ...
        
    async def _check_service_compatibility(self, response):
        """检查服务兼容性"""
        # ...
        
    async def _check_freshness(self, response, source_nodes):
        """检查内容新鲜度"""
        # ...
        
    async def _check_recommendation_quality(self, response, query):
        """检查推荐质量"""
        # ...
        
    async def _assess_overall_quality(self, query, response, context):
        """评估整体质量"""
        # ...
        
    def _extract_services(self, query):
        """提取查询中的服务"""
        # ...

# 评估器工厂
class EvaluatorFactory:
    def __init__(self, llm, catalog_service):
        self.llm = llm
        self.catalog = catalog_service
        
    def create_evaluator(self, evaluator_type):
        """创建评估器"""
        if evaluator_type == "llama_index":
            return LlamaIndexEvaluator(self.llm)
        elif evaluator_type == "azure":
            return AzureResponseEvaluator(self.llm, self.catalog)
        else:
            raise ValueError(f"未知的评估器类型: {evaluator_type}")
```

### 3.5 RAG调优管理平台

对不同业务需求的专业RAG系统来说，持续调优是实现卓越性能的关键。本节介绍RAG调优管理平台，这是一个专为AI工程师和知识库管理员设计的工具，用于精确调优和优化Azure Calculator RAG系统。

#### 3.5.1 平台概述与目标

RAG调优管理平台旨在提供全方位的调优能力，帮助团队:
- 监控和分析RAG系统性能
- 执行复杂的调优实验和A/B测试
- 精确调整系统参数和组件
- 持续改进知识库质量和检索性能

#### 3.5.2 核心功能模块

平台包含五个主要功能模块:

1. **Embedding调优实验室**
   - Embedding模型评估与对比
   - 领域适应微调和自定义训练
   - 语义空间可视化与分析
   - Azure专业词汇增强

2. **高级检索调优实验室**
   - 多检索策略实验与对比
   - 参数灵敏度分析与优化
   - 查询类型适应性测试
   - 自动超参数优化

3. **提示词工程实验室**
   - 提示词模板测试与优化
   - Chain-of-Thought设计工作台
   - A/B测试与策略对比
   - 特定查询类型的模板库

4. **数据质量管理实验室**
   - 内容审核与质量分析
   - 知识缺口识别与自动填补
   - 内容新鲜度监控
   - 自动内容生成与验证

5. **性能监控与分析平台**
   - 实时系统性能仪表板
   - 用户查询与反馈分析
   - 瓶颈识别与自动建议
   - 优化效果追踪与报告

#### 3.5.3 与核心系统集成

调优平台通过以下方式与RAG核心系统集成:

```
┌───────────────────────────────────────────────────────────────────────────┐
│                           Azure Calculator RAG系统                        │
├───────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│   ┌───────────────┐     ┌───────────────┐     ┌───────────────┐          │
│   │               │     │               │     │               │          │
│   │ 知识获取系统   │───▶ │ 内容处理系统   │────▶│   检索引擎    │──┐       │
│   │               │     │               │     │               │  │       │
│   └───────┬───────┘     └───────┬───────┘     └───────┬───────┘  │       │
│           │                     │                     │          │       │
│           │                     │                     │          │       │
│           ▼                     ▼                     ▼          ▼       │
│   ┌───────────────────────────────────────────────────────────────────┐  │
│   │                         调优管理平台                               │  │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────┐  │  │
│   │  │Embedding │  │检索调优   │  │提示词工程 │  │数据质量  │  │性能 │  │  │
│   │  │实验室    │  │实验室     │  │实验室     │  │管理      │  │监控 │  │  │
│   │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └─────┘  │  │
│   └───────────────────────────────────────────────────────────────────┘  │
│                                     │                                     │
│                                     ▼                                     │
│   ┌───────────────────────────────────────────────────────────────────┐  │
│   │                         增强生成系统                               │  │
│   └───────────────────────────────────────────────────────────────────┘  │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
```

调优平台与各核心组件的主要集成点:

1. **知识获取系统**
   - 监控爬虫性能
   - 优化数据源配置
   - 管理变更检测参数

2. **内容处理系统**
   - 调整分块策略
   - 优化元数据提取
   - 监控处理质量

3. **检索引擎**
   - 测试与优化检索策略
   - 微调向量索引参数
   - 调整查询处理逻辑

4. **增强生成系统**
   - 优化提示词模板
   - 调整评估与修正参数
   - 管理引用策略

#### 3.5.4 评估与优化流程

调优平台支持完整的RAG评估与优化流程:

1. **监控** - 持续收集系统性能数据和用户反馈
2. **分析** - 识别性能瓶颈和改进机会
3. **实验** - 设计和执行对照实验
4. **评估** - 量化不同配置的效果差异
5. **部署** - 将优化配置应用到生产环境
6. **验证** - 确认性能改进并持续监控

通过这一系统化流程，调优平台能够帮助团队持续优化RAG系统的性能，提高响应质量，提升用户满意度。

> **注意**: 完整的RAG调优管理平台设计与实现细节可参阅单独的详细设计文档。

### 3.6 管理平台

#### 3.5.1 知识库管理界面

设计灵活的知识库管理系统，结合自定义管理与LlamaIndex工具：

```python
# 知识库管理系统接口 (后端API)
class KnowledgeBaseManager:
    def __init__(self, doc_store, index_manager, source_manager, embedding_service):
        self.doc_store = doc_store
        self.index_manager = index_manager
        self.source_manager = source_manager
        self.embedding_service = embedding_service
        
    async def search_documents(self, query=None, filters=None, limit=50, offset=0):
        """搜索文档"""
        if query:
            # 基于语义搜索
            query_embedding = await self.embedding_service.get_embedding(query)
            results = await self.doc_store.search_by_vector(
                query_embedding,
                filters=filters,
                limit=limit,
                offset=offset
            )
        else:
            # 基于过滤器搜索
            results = await self.doc_store.search_by_filters(
                filters=filters,
                limit=limit,
                offset=offset
            )
            
        return results
        
    async def get_document(self, doc_id):
        """获取文档详情"""
        return await self.doc_store.get_document(doc_id)
        
    async def update_document(self, doc_id, updates):
        """更新文档"""
        # 获取原始文档
        doc = await self.doc_store.get_document(doc_id)
        if not doc:
            return {"success": False, "error": "文档不存在"}
            
        # 更新文档
        for key, value in updates.items():
            if key == "text":
                doc.text = value
            elif key == "metadata":
                doc.metadata.update(value)
                
        # 保存更新
        success = await self.doc_store.update_document(doc)
        
        # 如果更新成功，更新索引
        if success:
            await self.index_manager.update_document(doc)
            
        return {"success": success}
        
    async def delete_document(self, doc_id):
        """删除文档"""
        # 从文档存储中删除
        success = await self.doc_store.delete_document(doc_id)
        
        # 如果删除成功，从索引中也删除
        if success:
            await self.index_manager.delete_document(doc_id)
            
        return {"success": success}
        
    async def add_document(self, document_data):
        """添加新文档"""
        # 创建文档对象
        from app.schemas.document import Document
        
        doc = Document(
            text=document_data["text"],
            metadata=document_data.get("metadata", {})
        )
        
        # 添加到文档存储
        success = await self.doc_store.add_document(doc)
        
        # 如果添加成功，更新索引
        if success:
            await self.index_manager.add_document(doc)
            
        return {"success": success, "document_id": doc.doc_id}
        
    async def get_statistics(self):
        """获取知识库统计信息"""
        # 基本统计
        stats = await self.doc_store.get_statistics()
        
        # 添加服务覆盖统计
        service_coverage = await self._analyze_service_coverage()
        stats["service_coverage"] = service_coverage
        
        # 添加文档类型统计
        doc_types = await self._analyze_document_types()
        stats["document_types"] = doc_types
        
        # 添加最新更新时间
        latest_update = await self.doc_store.get_latest_update()
        stats["latest_update"] = latest_update
        
        return stats
        
    async def _analyze_service_coverage(self):
        """分析服务覆盖情况"""
        # ...
        
    async def _analyze_document_types(self):
        """分析文档类型分布"""
        # ...
```

#### 3.5.2 查询调试与优化工具

创建强大的调试平台，包括LlamaIndex实验和自定义优化：

```python
# 查询测试平台
class RAGTestingPlatform:
    def __init__(self, query_engines, retrievers, evaluators, embedding_service):
        self.query_engines = query_engines
        self.retrievers = retrievers
        self.evaluators = evaluators
        self.embedding_service = embedding_service
        
    async def test_query(self, query, config=None):
        """测试单个查询"""
        config = config or {}
        
        # 使用默认或指定查询引擎
        engine_name = config.get("engine", "default")
        engine = self.query_engines.get(engine_name)
        if not engine:
            return {"error": f"查询引擎不存在: {engine_name}"}
            
        # 记录开始时间
        import time
        start_time = time.time()
        
        # 执行查询
        response = await engine.query(query)
        
        # 计算耗时
        elapsed = time.time() - start_time
        
        # 如果需要评估，执行评估
        evaluation = None
        if config.get("evaluate", False):
            evaluator_name = config.get("evaluator", "default")
            evaluator = self.evaluators.get(evaluator_name)
            
            if evaluator:
                evaluation = await evaluator.evaluate(
                    query=query, 
                    response=response.response,
                    context=response.context,
                    source_nodes=response.source_nodes
                )
                
        # 构建结果
        result = {
            "query": query,
            "response": response.response,
            "performance": {
                "total_time_ms": round(elapsed * 1000, 2),
                "retrieval_time_ms": getattr(response, "retrieval_time_ms", None),
                "generation_time_ms": getattr(response, "generation_time_ms", None)
            },
            "source_nodes": [
                {
                    "text": node.text[:300] + "..." if len(node.text) > 300 else node.text,
                    "score": getattr(node, "score", None),
                    "metadata": node.metadata
                }
                for node in getattr(response, "source_nodes", [])
            ]
        }
        
        # 添加评估结果
        if evaluation:
            result["evaluation"] = evaluation
            
        return result
        
    async def compare_retrievers(self, query, retriever_configs=None):
        """比较不同检索器"""
        retriever_configs = retriever_configs or {}
        
        # 准备测试的检索器
        retrievers_to_test = {}
        for name, config in retriever_configs.items():
            if name in self.retrievers:
                retrievers_to_test[name] = self.retrievers[name]
            else:
                # 警告但继续
                logger.warning(f"检索器不存在: {name}")
                
        if not retrievers_to_test:
            # 使用所有可用检索器
            retrievers_to_test = self.retrievers
            
        # 并行执行检索测试
        results = {}
        for name, retriever in retrievers_to_test.items():
            # 记录开始时间
            import time
            start_time = time.time()
            
            # 执行检索
            nodes = await retriever.retrieve(query)
            
            # 计算耗时
            elapsed = time.time() - start_time
            
            # 构建结果
            results[name] = {
                "retrieval_time_ms": round(elapsed * 1000, 2),
                "node_count": len(nodes),
                "nodes": [
                    {
                        "text": node.text[:200] + "..." if len(node.text) > 200 else node.text,
                        "score": getattr(node, "score", None),
                        "metadata": node.metadata
                    }
                    for node in nodes[:5]  # 只显示前5个结果
                ]
            }
            
        return {
            "query": query,
            "results": results
        }
        
    async def run_benchmark(self, queries, config=None):
        """运行基准测试"""
        config = config or {}
        
        # 确定使用的查询引擎
        engine_name = config.get("engine", "default")
        engine = self.query_engines.get(engine_name)
        if not engine:
            return {"error": f"查询引擎不存在: {engine_name}"}
            
        # 确定使用的评估器
        evaluator_name = config.get("evaluator", "default")
        evaluator = self.evaluators.get(evaluator_name)
        if not evaluator and config.get("evaluate", False):
            return {"error": f"评估器不存在: {evaluator_name}"}
            
        # 运行测试
        results = []
        for query in queries:
            result = await self.test_query(
                query=query, 
                config={
                    "engine": engine_name,
                    "evaluate": config.get("evaluate", False),
                    "evaluator": evaluator_name
                }
            )
            results.append(result)
            
        # 汇总结果
        summary = self._summarize_benchmark(results)
            
        return {
            "config": config,
            "summary": summary,
            "results": results
        }
        
    def _summarize_benchmark(self, results):
        """汇总基准测试结果"""
        # ...
```

#### 3.5.3 RAG配置管理

实现强大的配置管理系统，支持LlamaIndex特定配置和自定义配置：

```python
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import os

# RAG配置模型
class RAGConfig(BaseModel):
    """RAG系统配置"""
    
    # 基本信息
    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_by: Optional[str] = None
    
    # 检索配置
    retriever: Dict[str, Any] = Field(
        default_factory=lambda: {
            "type": "multi_path",
            "retrievers": [
                {
                    "type": "vector",
                    "params": {
                        "top_k": 5,
                        "similarity_threshold": 0.7
                    }
                },
                {
                    "type": "keyword",
                    "params": {
                        "top_k": 3
                    }
                }
            ],
            "fusion": "reciprocal_rank"
        }
    )
    
    # 处理配置
    processor: Dict[str, Any] = Field(
        default_factory=lambda: {
            "type": "azure_custom",
            "splitter": {
                "type": "hierarchical",
                "params": {
                    "chunk_sizes": [2048, 1024, 512],
                    "chunk_overlap": 20
                }
            },
            "metadata_extractors": [
                {"type": "azure_service"},
                {"type": "summary"}
            ]
        }
    )
    
    # 生成配置
    generator: Dict[str, Any] = Field(
        default_factory=lambda: {
            "type": "azure_custom",
            "context_builder": {
                "type": "azure"
            },
            "prompt_template": {
                "type": "azure_advisor",
                "advisor_type": "general"
            },
            "llm_params": {
                "temperature": 0.7,
                "max_tokens": 1024
            }
        }
    )
    
    # LlamaIndex特定配置
    llama_index: Optional[Dict[str, Any]] = Field(
        default_factory=lambda: {
            "enabled": False,
            "settings": {
                "embed_model": "text-embedding-ada-002",
                "chunk_size": 1024,
                "chunk_overlap": 20
            },
            "response_mode": "compact"
        }
    )
    
    # 评估配置
    evaluation: Optional[Dict[str, Any]] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# 配置管理器
class ConfigManager:
    def __init__(self, storage_path="./configs"):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
        
    async def list_configs(self):
        """列出所有配置"""
        configs = []
        for filename in os.listdir(self.storage_path):
            if filename.endswith(".json"):
                try:
                    config_path = os.path.join(self.storage_path, filename)
                    with open(config_path, "r") as f:
                        data = json.load(f)
                        
                    # 只返回基本信息
                    configs.append({
                        "id": data.get("id"),
                        "name": data.get("name"),
                        "description": data.get("description"),
                        "created_at": data.get("created_at"),
                        "updated_at": data.get("updated_at"),
                        "created_by": data.get("created_by")
                    })
                except Exception as e:
                    # 记录错误但继续
                    logger.error(f"读取配置文件失败: {filename}, 错误: {str(e)}")
                    
        return configs
        
    async def get_config(self, config_id):
        """获取配置详情"""
        config_path = os.path.join(self.storage_path, f"{config_id}.json")
        if not os.path.exists(config_path):
            return None
            
        try:
            with open(config_path, "r") as f:
                data = json.load(f)
                
            return RAGConfig(**data)
        except Exception as e:
            logger.error(f"读取配置失败: {config_id}, 错误: {str(e)}")
            return None
            
    async def save_config(self, config):
        """保存配置"""
        # 更新时间戳
        config.updated_at = datetime.now()
        
        # 保存配置
        config_path = os.path.join(self.storage_path, f"{config.id}.json")
        try:
            with open(config_path, "w") as f:
                f.write(config.json(indent=2))
                
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {config.id}, 错误: {str(e)}")
            return False
            
    async def delete_config(self, config_id):
        """删除配置"""
        config_path = os.path.join(self.storage_path, f"{config_id}.json")
        if not os.path.exists(config_path):
            return False
            
        try:
            os.remove(config_path)
            return True
        except Exception as e:
            logger.error(f"删除配置失败: {config_id}, 错误: {str(e)}")
            return False
            
    async def create_config(self, config_data):
        """创建新配置"""
        # 生成ID
        import uuid
        config_id = str(uuid.uuid4())
        
        # 创建配置对象
        config = RAGConfig(
            id=config_id,
            **config_data
        )
        
        # 保存配置
        success = await self.save_config(config)
        
        if success:
            return config
        else:
            return None
            
    async def apply_config(self, config, rag_service):
        """应用配置到RAG服务"""
        # 检查是否使用LlamaIndex
        if config.llama_index and config.llama_index.get("enabled", False):
            return await self._apply_llama_config(config, rag_service)
        else:
            return await self._apply_custom_config(config, rag_service)
            
    async def _apply_llama_config(self, config, rag_service):
        """应用LlamaIndex配置"""
        # ...
        
    async def _apply_custom_config(self, config, rag_service):
        """应用自定义配置"""
        # ...
```

#### 3.5.4 监控与分析

构建强大的监控系统，结合LlamaIndex和自定义工具：

```python
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# 基础回调接口
class RAGCallback(ABC):
    @abstractmethod
    async def on_query_start(self, query_id, query):
        """查询开始"""
        pass
        
    @abstractmethod
    async def on_retrieval_start(self, query_id):
        """检索开始"""
        pass
        
    @abstractmethod
    async def on_retrieval_end(self, query_id, nodes):
        """检索结束"""
        pass
        
    @abstractmethod
    async def on_generation_start(self, query_id):
        """生成开始"""
        pass
        
    @abstractmethod
    async def on_generation_end(self, query_id, response):
        """生成结束"""
        pass
        
    @abstractmethod
    async def on_query_end(self, query_id, total_time_ms):
        """查询结束"""
        pass

# LlamaIndex回调适配
class LlamaIndexCallbackAdapter(RAGCallback):
    def __init__(self):
        from llama_index.core.callbacks import CallbackManager
        from llama_index.core.callbacks import CBEventType
        
        self.event_types = CBEventType
        self.queries = {}
        
        # 创建内部回调处理器
        class LlamaCallbackHandler(BaseCallbackHandler):
            def __init__(self, adapter):
                self.adapter = adapter
                
            def on_event_start(self, event_type, payload, id_info):
                """LlamaIndex事件开始回调"""
                event_id = id_info.get("event_id", "unknown")
                parent_id = id_info.get("parent_id", event_id)
                
                if event_type == self.adapter.event_types.QUERY:
                    asyncio.create_task(
                        self.adapter.on_query_start(
                            parent_id, 
                            payload.get("query_str", "")
                        )
                    )
                elif event_type == self.adapter.event_types.RETRIEVE:
                    asyncio.create_task(
                        self.adapter.on_retrieval_start(parent_id)
                    )
                elif event_type == self.adapter.event_types.LLM:
                    asyncio.create_task(
                        self.adapter.on_generation_start(parent_id)
                    )
                    
            def on_event_end(self, event_type, payload, id_info):
                """LlamaIndex事件结束回调"""
                event_id = id_info.get("event_id", "unknown")
                parent_id = id_info.get("parent_id", event_id)
                
                if event_type == self.adapter.event_types.RETRIEVE:
                    asyncio.create_task(
                        self.adapter.on_retrieval_end(
                            parent_id,
                            payload.get("nodes", [])
                        )
                    )
                elif event_type == self.adapter.event_types.LLM:
                    asyncio.create_task(
                        self.adapter.on_generation_end(
                            parent_id,
                            payload.get("response", "")
                        )
                    )
                elif event_type == self.adapter.event_types.QUERY:
                    # 计算总时间
                    query_info = self.adapter.queries.get(parent_id, {})
                    start_time = query_info.get("start_time", 0)
                    total_time_ms = round((time.time() - start_time) * 1000, 2)
                    
                    asyncio.create_task(
                        self.adapter.on_query_end(
                            parent_id,
                            total_time_ms
                        )
                    )
                    
        # 创建回调管理器
        self.handler = LlamaCallbackHandler(self)
        self.callback_manager = CallbackManager([self.handler])
        
    async def on_query_start(self, query_id, query):
        """查询开始"""
        self.queries[query_id] = {
            "query": query,
            "start_time": time.time(),
            "stages": {}
        }
        
    async def on_retrieval_start(self, query_id):
        """检索开始"""
        if query_id in self.queries:
            self.queries[query_id]["stages"]["retrieval"] = {
                "start_time": time.time()
            }
        
    async def on_retrieval_end(self, query_id, nodes):
        """检索结束"""
        if query_id in self.queries and "retrieval" in self.queries[query_id]["stages"]:
            stage = self.queries[query_id]["stages"]["retrieval"]
            stage["end_time"] = time.time()
            stage["duration_ms"] = round((stage["end_time"] - stage["start_time"]) * 1000, 2)
            stage["node_count"] = len(nodes)
        
    async def on_generation_start(self, query_id):
        """生成开始"""
        if query_id in self.queries:
            self.queries[query_id]["stages"]["generation"] = {
                "start_time": time.time()
            }
        
    async def on_generation_end(self, query_id, response):
        """生成结束"""
        if query_id in self.queries and "generation" in self.queries[query_id]["stages"]:
            stage = self.queries[query_id]["stages"]["generation"]
            stage["end_time"] = time.time()
            stage["duration_ms"] = round((stage["end_time"] - stage["start_time"]) * 1000, 2)
        
    async def on_query_end(self, query_id, total_time_ms):
        """查询结束"""
        if query_id in self.queries:
            self.queries[query_id]["end_time"] = time.time()
            self.queries[query_id]["total_duration_ms"] = total_time_ms
            
            # 记录日志
            log_data = self.queries[query_id]
            logger.info(f"查询完成: {query_id}, 耗时: {total_time_ms}ms")
            
            # 清理缓存
            del self.queries[query_id]

# Azure监控收集器
class AzureMonitoringCollector(RAGCallback):
    def __init__(self, collection_service):
        self.collection_service = collection_service
        self.queries = {}
        
    async def on_query_start(self, query_id, query):
        """查询开始"""
        self.queries[query_id] = {
            "query_id": query_id,
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "stages": {},
            "metrics": {}
        }
        
    async def on_retrieval_start(self, query_id):
        """检索开始"""
        if query_id in self.queries:
            self.queries[query_id]["stages"]["retrieval_start"] = datetime.now().isoformat()
        
    async def on_retrieval_end(self, query_id, nodes):
        """检索结束"""
        if query_id in self.queries:
            query_data = self.queries[query_id]
            query_data["stages"]["retrieval_end"] = datetime.now().isoformat()
            
            # 计算检索指标
            start = datetime.fromisoformat(query_data["stages"].get("retrieval_start", query_data["timestamp"]))
            end = datetime.fromisoformat(query_data["stages"]["retrieval_end"])
            retrieval_time = (end - start).total_seconds() * 1000
            
            # 记录指标
            query_data["metrics"]["retrieval_time_ms"] = round(retrieval_time, 2)
            query_data["metrics"]["node_count"] = len(nodes)
            
            # 记录服务类别覆盖
            services = set()
            for node in nodes:
                if "service" in node.metadata:
                    services.add(node.metadata["service"])
            
            query_data["metrics"]["service_coverage"] = list(services)
        
    async def on_generation_start(self, query_id):
        """生成开始"""
        if query_id in self.queries:
            self.queries[query_id]["stages"]["generation_start"] = datetime.now().isoformat()
        
    async def on_generation_end(self, query_id, response):
        """生成结束"""
        if query_id in self.queries:
            query_data = self.queries[query_id]
            query_data["stages"]["generation_end"] = datetime.now().isoformat()
            
            # 计算生成指标
            start = datetime.fromisoformat(query_data["stages"].get("generation_start", query_data["timestamp"]))
            end = datetime.fromisoformat(query_data["stages"]["generation_end"])
            generation_time = (end - start).total_seconds() * 1000
            
            # 记录指标
            query_data["metrics"]["generation_time_ms"] = round(generation_time, 2)
            query_data["metrics"]["response_length"] = len(response)
        
    async def on_query_end(self, query_id, total_time_ms):
        """查询结束"""
        if query_id in self.queries:
            query_data = self.queries[query_id]
            query_data["stages"]["query_end"] = datetime.now().isoformat()
            query_data["metrics"]["total_time_ms"] = total_time_ms
            
            # 存储完整日志
            await self.collection_service.store_rag_log(query_data)
            
            # 清理缓存
            del self.queries[query_id]

# 分析服务
class RAGAnalyticsService:
    def __init__(self, db_client):
        self.db = db_client
        
    async def get_performance_metrics(self, time_range=None, filters=None):
        """获取性能指标"""
        # 默认时间范围为过去7天
        if not time_range:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            time_range = {"start": start_date, "end": end_date}
            
        # 构建查询
        query = {"timestamp": {"$gte": time_range["start"], "$lte": time_range["end"]}}
        
        # 添加额外过滤条件
        if filters:
            query.update(filters)
            
        # 聚合查询
        pipeline = [
            {"$match": query},
            {"$group": {
                "_id": None,
                "avg_total_time": {"$avg": "$metrics.total_time_ms"},
                "avg_retrieval_time": {"$avg": "$metrics.retrieval_time_ms"},
                "avg_generation_time": {"$avg": "$metrics.generation_time_ms"},
                "avg_node_count": {"$avg": "$metrics.node_count"},
                "total_queries": {"$sum": 1},
                "max_total_time": {"$max": "$metrics.total_time_ms"},
                "min_total_time": {"$min": "$metrics.total_time_ms"}
            }}
        ]
        
        result = await self.db.aggregate("rag_logs", pipeline)
        
        # 如果没有结果，返回默认值
        if not result:
            return {
                "avg_total_time_ms": 0,
                "avg_retrieval_time_ms": 0,
                "avg_generation_time_ms": 0,
                "avg_node_count": 0,
                "total_queries": 0,
                "max_total_time_ms": 0,
                "min_total_time_ms": 0
            }
            
        return {
            "avg_total_time_ms": round(result[0]["avg_total_time"], 2),
            "avg_retrieval_time_ms": round(result[0]["avg_retrieval_time"], 2),
            "avg_generation_time_ms": round(result[0]["avg_generation_time"], 2),
            "avg_node_count": round(result[0]["avg_node_count"], 2),
            "total_queries": result[0]["total_queries"],
            "max_total_time_ms": round(result[0]["max_total_time"], 2),
            "min_total_time_ms": round(result[0]["min_total_time"], 2)
        }
        
    async def get_top_queries(self, limit=10):
        """获取热门查询"""
        pipeline = [
            {"$group": {
                "_id": "$query",
                "count": {"$sum": 1},
                "avg_time": {"$avg": "$metrics.total_time_ms"}
            }},
            {"$sort": {"count": -1}},
            {"$limit": limit}
        ]
        
        results = await self.db.aggregate("rag_logs", pipeline)
        
        return [
            {
                "query": item["_id"],
                "count": item["count"],
                "avg_time_ms": round(item["avg_time"], 2)
            }
            for item in results
        ]
        
    async def get_service_coverage(self):
        """获取服务覆盖分析"""
        pipeline = [
            {"$unwind": "$metrics.service_coverage"},
            {"$group": {
                "_id": "$metrics.service_coverage",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}}
        ]
        
        results = await self.db.aggregate("rag_logs", pipeline)
        
        return [
            {
                "service": item["_id"],
                "query_count": item["count"]
            }
            for item in results
        ]
        
    async def get_time_series_metrics(self, metric, interval="day", time_range=None):
        """获取时间序列指标"""
        # 默认时间范围为过去30天
        if not time_range:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            time_range = {"start": start_date, "end": end_date}
            
        # 确定日期分组格式
        date_format = "%Y-%m-%d"
        if interval == "hour":
            date_format = "%Y-%m-%d %H:00"
        elif interval == "week":
            date_format = "%Y-W%W"
        elif interval == "month":
            date_format = "%Y-%m"
            
        # 构建查询
        pipeline = [
            {"$match": {
                "timestamp": {"$gte": time_range["start"], "$lte": time_range["end"]}
            }},
            {"$project": {
                "date": {"$dateToString": {"format": date_format, "date": "$timestamp"}},
                "metric": f"$metrics.{metric}"
            }},
            {"$group": {
                "_id": "$date",
                "avg_value": {"$avg": "$metric"},
                "count": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}}
        ]
        
        results = await self.db.aggregate("rag_logs", pipeline)
        
        return [
            {
                "date": item["_id"],
                "avg_value": round(item["avg_value"], 2),
                "count": item["count"]
            }
            for item in results
        ]
```

## 4. 数据模型

我们设计的数据模型需要同时满足自定义需求和与LlamaIndex的互操作性：

### 4.1 文档模型

```python
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

# 基础文档模型
class Document(BaseModel):
    """文档模型，设计为与LlamaIndex兼容"""
    
    doc_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # 将文档转换为LlamaIndex格式
    def to_llama_format(self):
        """转换为LlamaIndex文档"""
        from llama_index.core.schema import Document as LlamaDocument
        
        return LlamaDocument(
            text=self.text,
            metadata=self.metadata,
            doc_id=self.doc_id
        )
    
    # 从LlamaIndex格式创建
    @classmethod
    def from_llama_document(cls, llama_doc):
        """从LlamaIndex文档创建"""
        return cls(
            doc_id=llama_doc.doc_id,
            text=llama_doc.text,
            metadata=llama_doc.metadata
        )

# 节点模型
class Node(BaseModel):
    """节点模型，文档分块后的基本单位"""
    
    node_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    doc_id: str
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding_id: Optional[str] = None
    embedding: Optional[List[float]] = None
    
    # 将节点转换为LlamaIndex格式
    def to_llama_format(self):
        """转换为LlamaIndex节点"""
        from llama_index.core.schema import TextNode
        
        return TextNode(
            text=self.text,
            metadata=self.metadata,
            id_=self.node_id,
            embedding=self.embedding
        )
    
    # 从LlamaIndex格式创建
    @classmethod
    def from_llama_node(cls, llama_node):
        """从LlamaIndex节点创建"""
        return cls(
            node_id=llama_node.id_,
            doc_id=llama_node.metadata.get("doc_id", ""),
            text=llama_node.text,
            metadata=llama_node.metadata,
            embedding=llama_node.embedding
        )

# 服务模型
class AzureService(BaseModel):
    """Azure服务信息模型"""
    
    id: str
    name: str
    display_name: str
    description: str
    category: str
    tier: str
    url: str
    pricing_url: Optional[str] = None
    documentation_url: Optional[str] = None
    regions: List[str] = Field(default_factory=list)
    related_services: List[str] = Field(default_factory=list)

# 检索结果模型
class RetrievalResult(BaseModel):
    """检索结果模型"""
    
    node: Node
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)

# 查询响应模型
class QueryResponse(BaseModel):
    """查询响应模型"""
    
    query_id: str
    query: str
    response: str
    context: Optional[str] = None
    source_nodes: List[RetrievalResult] = Field(default_factory=list)
    references: List[Dict[str, Any]] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
```

### 4.2 配置和管理模型

```python
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

# RAG配置模型
class RAGConfig(BaseModel):
    """RAG系统配置"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_by: Optional[str] = None
    
    # 系统组件配置
    retriever_config: Dict[str, Any] = Field(default_factory=dict)
    processor_config: Dict[str, Any] = Field(default_factory=dict)
    generator_config: Dict[str, Any] = Field(default_factory=dict)
    
    # 是否使用LlamaIndex
    use_llama_index: bool = False
    llama_index_config: Optional[Dict[str, Any]] = None
    
    # 辅助字段，不存储到数据库
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        extra = "allow"

# 实验配置模型
class ExperimentConfig(BaseModel):
    """实验配置"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    
    # 实验参数
    queries: List[str]
    config_variants: List[Dict[str, Any]]
    evaluator: Optional[str] = None
    metrics: List[str] = Field(default_factory=list)
    
    # 实验结果
    status: str = "pending"  # pending, running, completed, failed
    results: Optional[Dict[str, Any]] = None
    completed_at: Optional[datetime] = None

# 数据源配置模型
class DataSourceConfig(BaseModel):
    """数据源配置"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    source_type: str  # web, pdf, api, etc.
    base_urls: List[str]
    crawl_frequency: str  # hourly, daily, weekly, monthly
    priority: str  # highest, high, medium, low
    loader_type: str
    loader_params: Dict[str, Any] = Field(default_factory=dict)
    processing_strategy: str
    metadata_template: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_crawled: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

### 4.3 监控和分析模型

```python
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

# 查询日志模型
class QueryLog(BaseModel):
    """查询日志模型"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query_id: str
    query: str
    response: str
    user_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # 阶段时间
    stages: Dict[str, datetime] = Field(default_factory=dict)
    
    # 性能指标
    metrics: Dict[str, Any] = Field(default_factory=dict)
    
    # 检索信息
    retrieval_info: Optional[Dict[str, Any]] = None
    
    # 生成信息
    generation_info: Optional[Dict[str, Any]] = None
    
    # 用户反馈
    feedback: Optional[Dict[str, Any]] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# 性能指标模型
class PerformanceMetrics(BaseModel):
    """性能指标汇总"""
    
    period_start: datetime
    period_end: datetime
    total_queries: int
    
    # 时间指标
    avg_total_time_ms: float
    avg_retrieval_time_ms: float
    avg_generation_time_ms: float
    min_total_time_ms: float
    max_total_time_ms: float
    
    # 检索指标
    avg_node_count: float
    avg_relevance_score: Optional[float] = None
    
    # 服务覆盖
    service_coverage: Dict[str, int] = Field(default_factory=dict)
    
    # 热门查询
    top_queries: List[Dict[str, Any]] = Field(default_factory=list)
    
    # 错误统计
    error_count: int = 0
    error_types: Dict[str, int] = Field(default_factory=dict)

# 用户反馈模型
class UserFeedback(BaseModel):
    """用户反馈"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query_id: str
    user_id: Optional[str] = None
    rating: int  # 1-5
    feedback_type: str  # relevance, accuracy, helpfulness, etc.
    comment: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
```

## 5. 实施计划

### 5.1 阶段划分

采用灵活的实施策略，有选择地利用LlamaIndex加速开发流程：

| 阶段 | 时间 | 主要目标 | 交付物 |
|------|------|---------|--------|
| 0 | 1-2周 | 评估与准备 | 框架评估，环境搭建，接口设计 |
| 1 | 3-4周 | 核心框架与接口 | 抽象接口层，LlamaIndex集成，数据模型 |
| 2 | 4-6周 | 基础RAG功能 | 文档处理，检索与生成，简单管理界面 |
| 3 | 6-8周 | Azure特定优化 | Azure服务理解，领域特定提示词，检索优化 |
| 4 | 8-10周 | 高级功能开发 | 自评估，多路径检索，实验平台 |
| 5 | 10-12周 | 生产就绪与扩展 | 性能优化，监控系统，全面测试 |

### 5.2 第0阶段：评估与准备

| 周 | 任务 | 责任人 | 预期产出 |
|----|------|--------|---------|
| 1 | 框架评估 | 首席工程师 | 框架评估报告（LlamaIndex vs 自定义） |
| 1 | 接口设计 | 架构师 | 抽象接口定义与互操作性设计 |
| 1-2 | 环境搭建 | 开发团队 | 开发环境配置，测试框架 |
| 2 | 原型验证 | 开发团队 | LlamaIndex + 自定义逻辑混合原型 |

### 5.3 第1阶段：核心框架与接口

| 周 | 任务 | 责任人 | 预期产出 |
|----|------|--------|---------|
| 1 | 抽象接口层设计与实现 | 架构师 + 后端开发 | 核心接口与适配器 |
| 1-2 | 数据模型实现 | 后端开发 | 文档和节点模型，LlamaIndex兼容层 |
| 2 | 基础文档加载接口 | 爬虫开发 | 文档加载器与LlamaIndex集成 |
| 2-3 | 基础存储层 | 后端开发 | 文档存储与向量存储接口 |
| 3-4 | 核心RAG流程 | 全栈开发 | 基础RAG流程，使用抽象接口 |

### 5.4 第2阶段：基础RAG功能

| 周 | 任务 | 责任人 | 预期产出 |
|----|------|--------|---------|
| 1-2 | 文档处理流水线 | 后端开发 | 完整文档处理流程，自定义与LlamaIndex集成 |
| 2-3 | 检索引擎实现 | 搜索开发 | 向量检索与关键词检索，LlamaIndex适配 |
| 3-4 | 生成引擎实现 | AI开发 | 提示词系统与生成优化 |
| 4 | 简单管理界面 | 前端开发 | 文档管理与RAG配置界面 |

### 5.5 第3阶段：Azure特定优化

| 周 | 任务 | 责任人 | 预期产出 |
|----|------|--------|---------|
| 1-2 | Azure服务目录 | 领域专家 + 后端开发 | Azure服务数据库与关系图 |
| 2-3 | Azure文档爬虫优化 | 爬虫开发 | 专用于Azure文档的爬虫与处理器 |
| 3-4 | 价格提取器 | 后端开发 | Azure价格提取和结构化组件 |
| 4-5 | Azure特定提示词 | AI开发 | 领域特定提示词模板与优化 |
| 5-6 | 服务推荐引擎 | AI开发 + 领域专家 | Azure服务推荐组件与评估 |

## 6. API设计

### 6.1 RAG服务API

```
# 查询API
POST /api/v1/rag/query

Request:
{
  "query": "Azure虚拟机的定价方案有哪些?",
  "options": {
    "config_id": "default",           // 使用的RAG配置
    "stream": false,                  // 是否使用流式响应
    "include_sources": true,          // 是否包含来源
    "parameters": {                   // 附加参数，可覆盖配置
      "top_k": 5,
      "temperature": 0.7
    }
  }
}

Response:
{
  "query_id": "550e8400-e29b-41d4-a716-446655440000",
  "query": "Azure虚拟机的定价方案有哪些?",
  "response": "Azure虚拟机提供多种定价方案，包括...",
  "sources": [
    {
      "title": "Azure虚拟机定价",
      "url": "https://azure.microsoft.com/pricing/details/virtual-machines/",
      "service": "Virtual Machines",
      "relevance": 0.92,
      "id": "[1]"
    },
    ...
  ],
  "metrics": {
    "total_time_ms": 1250,
    "retrieval_time_ms": 320,
    "generation_time_ms": 930,
    "token_usage": {
      "prompt_tokens": 1250,
      "completion_tokens": 350,
      "total_tokens": 1600
    }
  }
}

# 流式查询API
POST /api/v1/rag/stream-query

Request:
{
  "query": "比较Azure SQL Database和Cosmos DB的定价和性能特点",
  "options": {
    "config_id": "default",
    "parameters": {
      "top_k": 8,
      "stream_mode": "token"  // token 或 chunk
    }
  }
}

Response: (Server-Sent Events)
event: token
data: "Azure"

event: token
data: " SQL"

...

event: sources
data: [{"title": "Azure SQL定价", "url": "..."}, ...]

event: done
data: {"processing_time_ms": 3450, "token_count": 520}

# 反馈API
POST /api/v1/rag/feedback

Request:
{
  "query_id": "550e8400-e29b-41d4-a716-446655440000",
  "rating": 4,
  "feedback_type": "relevance",  // relevance, accuracy, helpfulness
  "comment": "回答很准确，但缺少了最新的Dev/Test优惠信息",
  "tags": ["missing_info", "needs_update"]
}

Response:
{
  "status": "success",
  "feedback_id": "7ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "message": "感谢您的反馈"
}
```

### 6.2 知识库管理API

```
# 搜索文档
GET /api/v1/rag/admin/documents?query=Azure%20VM&document_type=pricing&limit=20&offset=0

Response:
{
  "total": 156,
  "documents": [
    {
      "doc_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
      "title": "Azure虚拟机定价概述",
      "source": "azure-docs",
      "url": "https://azure.microsoft.com/pricing/details/virtual-machines/",
      "updated_at": "2025-02-15T10:30:45Z",
      "preview": "Azure虚拟机提供多种定价选项..."
    },
    ...
  ]
}

# 获取文档详情
GET /api/v1/rag/admin/documents/{doc_id}

Response:
{
  "doc_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "text": "完整文档内容...",
  "metadata": {
    "title": "Azure虚拟机定价概述",
    "source": "azure-docs",
    "url": "https://azure.microsoft.com/pricing/details/virtual-machines/",
    "service": "Virtual Machines",
    "document_type": "pricing",
    "created_at": "2025-01-20T14:32:45Z",
    "updated_at": "2025-02-15T10:30:45Z"
  },
  "chunks": [
    {
      "node_id": "7ba7b810-9dad-11d1-80b4-00c04fd430c8",
      "text": "按需定价：Azure虚拟机的按需定价（即用即付）...",
      "metadata": {
        "section": "按需定价"
      }
    },
    ...
  ]
}

# 更新文档
PATCH /api/v1/rag/admin/documents/{doc_id}

Request:
{
  "text": "更新的文档内容...",
  "metadata": {
    "title": "更新的标题"
  }
}

Response:
{
  "status": "success",
  "message": "文档已更新",
  "updated_at": "2025-03-25T15:30:22Z"
}

# 删除文档
DELETE /api/v1/rag/admin/documents/{doc_id}

Response:
{
  "status": "success",
  "message": "文档已删除"
}

# 获取知识库统计
GET /api/v1/rag/admin/stats

Response:
{
  "total_documents": 2543,
  "total_chunks": 45289,
  "services_covered": 187,
  "last_update": "2025-03-22T14:32:45Z",
  "storage_size_mb": 256.8,
  "index_type": "vector",
  "coverage_stats": {
    "pricing": 98.2,
    "technical": 87.5,
    "best_practices": 76.3
  }
}
```

### 6.3 RAG配置管理API

```
# 获取配置列表
GET /api/v1/rag/admin/configs

Response:
{
  "configs": [
    {
      "id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
      "name": "生产配置",
      "description": "默认生产环境配置",
      "created_at": "2025-02-10T10:00:00Z",
      "updated_at": "2025-03-20T14:30:22Z",
      "created_by": "admin@example.com",
      "use_llama_index": true
    },
    ...
  ]
}

# 获取配置详情
GET /api/v1/rag/admin/configs/{config_id}

Response:
{
  "id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "name": "生产配置",
  "description": "默认生产环境配置",
  "created_at": "2025-02-10T10:00:00Z",
  "updated_at": "2025-03-20T14:30:22Z",
  "created_by": "admin@example.com",
  
  "retriever_config": {
    "type": "multi_path",
    "retrievers": [
      {
        "type": "vector",
        "params": {
          "top_k": 5,
          "similarity_threshold": 0.7
        }
      },
      ...
    ],
    "fusion": "reciprocal_rank"
  },
  
  "processor_config": {...},
  "generator_config": {...},
  
  "use_llama_index": true,
  "llama_index_config": {
    "embed_model": "text-embedding-ada-002",
    "chunk_size": 1024,
    "response_mode": "compact"
  }
}

# 创建配置
POST /api/v1/rag/admin/configs

Request:
{
  "name": "新配置",
  "description": "测试新特性的配置",
  "retriever_config": {...},
  "processor_config": {...},
  "generator_config": {...},
  "use_llama_index": false
}

Response:
{
  "status": "success",
  "config_id": "7ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "message": "配置已创建"
}

# 更新配置
PUT /api/v1/rag/admin/configs/{config_id}

Request:
{
  "name": "更新的配置名称",
  "retriever_config": {
    "type": "multi_path",
    "retrievers": [...]
  }
}

Response:
{
  "status": "success",
  "message": "配置已更新",
  "updated_at": "2025-03-25T16:30:22Z"
}

# 删除配置
DELETE /api/v1/rag/admin/configs/{config_id}

Response:
{
  "status": "success",
  "message": "配置已删除"
}
```

### 6.4 测试与实验API

```
# 测试查询
POST /api/v1/rag/admin/test-query

Request:
{
  "query": "Azure虚拟机的定价方案有哪些?",
  "config_id": "test_config",
  "options": {
    "include_retrieval_details": true,
    "evaluate": true
  }
}

Response:
{
  "query": "Azure虚拟机的定价方案有哪些?",
  "response": "Azure虚拟机提供多种定价方案，包括...",
  "retrieval_details": {
    "strategy": "multi_path",
    "retrievers": [
      {
        "name": "vector",
        "nodes": [...],
        "time_ms": 120
      },
      {
        "name": "keyword",
        "nodes": [...],
        "time_ms": 30
      }
    ],
    "fusion": {
      "strategy": "reciprocal_rank",
      "time_ms": 15
    }
  },
  "generation_details": {
    "context_building": {
      "strategy": "azure",
      "time_ms": 25
    },
    "completion": {
      "time_ms": 850,
      "prompt_tokens": 1250,
      "completion_tokens": 350
    }
  },
  "evaluation": {
    "relevance": {
      "score": 0.92,
      "feedback": "回答直接解决了用户询问的问题，包含了所有主要的定价方案。"
    },
    "accuracy": {
      "score": 0.95,
      "feedback": "回答中的定价信息正确，引用了可靠的来源。"
    }
  },
  "performance": {
    "total_time_ms": 1040,
    "retrieval_time_ms": 165,
    "generation_time_ms": 875
  }
}

# 创建实验
POST /api/v1/rag/admin/experiments

Request:
{
  "name": "检索策略比较实验",
  "description": "比较向量检索与混合检索的效果",
  "queries": [
    "Azure虚拟机的定价方案有哪些?",
    "如何选择合适的Azure存储服务?",
    "比较Azure Cosmos DB与Azure SQL Database的性能特点"
  ],
  "config_variants": [
    {
      "name": "向量检索",
      "config": {
        "retriever_config": {
          "type": "vector",
          "params": {
            "top_k": 5
          }
        }
      }
    },
    {
      "name": "混合检索",
      "config": {
        "retriever_config": {
          "type": "multi_path",
          "retrievers": [
            {"type": "vector", "params": {"top_k": 3}},
            {"type": "keyword", "params": {"top_k": 3}}
          ],
          "fusion": "reciprocal_rank"
        }
      }
    }
  ],
  "evaluator": "azure",
  "metrics": ["relevance", "accuracy", "retrieval_time"]
}

Response:
{
  "experiment_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "status": "created",
  "message": "实验已创建并加入队列"
}

# 获取实验状态
GET /api/v1/rag/admin/experiments/{experiment_id}

Response:
{
  "id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "name": "检索策略比较实验",
  "status": "running",
  "progress": {
    "total_queries": 3,
    "completed_queries": 1,
    "percentage": 33
  },
  "created_at": "2025-03-25T14:30:00Z",
  "estimated_completion": "2025-03-25T14:35:00Z"
}

# 获取实验结果
GET /api/v1/rag/admin/experiments/{experiment_id}/results

Response:
{
  "id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "name": "检索策略比较实验",
  "status": "completed",
  "created_at": "2025-03-25T14:30:00Z",
  "completed_at": "2025-03-25T14:35:22Z",
  
  "summary": {
    "向量检索": {
      "relevance": 0.84,
      "accuracy": 0.89,
      "retrieval_time": 138.5
    },
    "混合检索": {
      "relevance": 0.92,
      "accuracy": 0.91,
      "retrieval_time": 187.3
    },
    "comparison": {
      "winner": "混合检索",
      "improvement": {
        "relevance": "+9.5%",
        "accuracy": "+2.2%",
        "retrieval_time": "+35.2%"
      }
    }
  },
  
  "query_results": [
    {
      "query": "Azure虚拟机的定价方案有哪些?",
      "variants": {
        "向量检索": {
          "response": "...",
          "metrics": {
            "relevance": 0.88,
            "accuracy": 0.92,
            "retrieval_time": 125.3
          }
        },
        "混合检索": {
          "response": "...",
          "metrics": {
            "relevance": 0.94,
            "accuracy": 0.93,
            "retrieval_time": 172.8
          }
        }
      }
    },
    ...
  ]
}
```

## 7. 评估与优化

### 7.1 评估指标与方法

| 指标类别 | 指标 | 评估方法 | 目标值 |
|---------|------|---------|-------|
| **检索质量** | 召回率 | 黄金标准数据集，专家评估 | ≥ 80% |
|  | 精确度 | 黄金标准数据集，专家评估 | ≥ 85% |
|  | 归一化折损累积增益 (NDCG) | 排序质量评估 | ≥ 0.8 |
| **回答质量** | 事实准确性 | LLM评估 + 专家抽查 | ≥ 90% |
|  | 相关性 | LLM评估 + 用户反馈 | ≥ 4.5/5 |
|  | 完整性 | 专家评估，覆盖度分析 | ≥ 85% |
|  | 新鲜度 | 最新信息审核 | ≥ 95% |
| **性能指标** | 端到端延迟 | 自动化测试 | ≤ 3秒 |
|  | 检索时间 | 性能日志 | ≤ 500ms |
|  | 生成时间 | 性能日志 | ≤ 2.5秒 |
|  | 每次查询成本 | Token使用统计 | ≤ ¥2.5元 |

### 7.2 评估方法

我们将使用混合评估方法，结合自动化评估和专家评审：

1. **自动化评估**
   - LLM评估器：使用专门训练的评估模型对回答进行评分
   - 黄金数据集：使用预先标注的问答对进行自动测试
   - 性能测试：自动化负载测试和性能监控

2. **专家评估**
   - 领域专家审查：Azure专家审查回答的准确性和完整性
   - 盲测：与纯LLM和现有解决方案进行盲测比较

3. **用户反馈**
   - 用户评分：收集真实用户的评分和反馈
   - A/B测试：在不同用户组测试不同配置

### 7.3 持续优化策略

1. **知识库优化循环**
   - 收集未覆盖查询：记录无法良好回答的问题
   - 自动识别知识差距：分析用户查询与索引内容的差距
   - 优先补充内容：基于用户需求填补知识库空白

2. **检索优化循环**
   - 失败案例分析：分析检索失败的查询特征
   - 参数调优：基于实验结果，定期调整检索参数
   - 策略优化：根据不同查询类型调整最佳检索策略

3. **生成优化循环**
   - 提示词迭代：基于用户反馈优化提示词模板
   - 上下文优化：改进上下文构建策略
   - 参数调整：根据不同查询类型优化温度等参数

4. **性能优化循环**
   - 瓶颈分析：识别并解决系统瓶颈
   - 缓存策略：优化缓存命中率
   - 批处理优化：合并类似请求提高吞吐量

## 8. 技术栈与依赖

### 8.1 核心技术栈

| 组件 | 主要技术选择 | 备选方案 | 决策理由 |
|------|----------|---------|---------|
| RAG框架 | 抽象接口 + LlamaIndex | LangChain, Haystack | 保持灵活性的同时利用LlamaIndex成熟组件 |
| 抓取框架 | Firecrawl | Scrapy, Playwright | 专为文档抓取优化，支持JS渲染 |
| 数据处理 | 自定义处理器 + LlamaIndex | Trafilatura, BeautifulSoup | 针对Azure文档特性定制，利用LlamaIndex基础设施 |
| 向量数据库 | Qdrant | Milvus, FAISS, Pinecone | 开源、性能良好、支持过滤查询 |
| 嵌入模型 | Azure OpenAI Ada-002 | BAAI/bge-large-zh, GanymedeNil/text2vec-large-chinese | 性能优秀，与Azure生态集成 |
| LLM | Azure OpenAI gpt-4 | Anthropic Claude | 强大的上下文理解能力，与Azure生态集成 |
| 后端框架 | FastAPI | Express, Flask | 高性能异步支持，类型提示，良好文档 |
| 前端框架 | React + TypeScript | Vue, Svelte | 生态成熟，团队熟悉 |
| 监控系统 | Prometheus + Grafana | ELK, Datadog | 开源，可扩展，丰富可视化 |

### 8.2 主要依赖项

```python
# 核心依赖
fastapi>=0.100.0                 # Web框架
pydantic>=2.3.0                  # 数据验证
uvicorn>=0.23.0                  # ASGI服务器
motor>=3.3.0                     # 异步MongoDB客户端
qdrant-client>=1.6.0             # Qdrant向量数据库客户端
redis>=5.0.0                     # Redis客户端
httpx>=0.25.0                    # 异步HTTP客户端

# RAG框架
llama-index-core>=0.10.0         # LlamaIndex核心
llama-index-readers-web>=0.1.0   # Web加载器
llama-index-llms-openai>=0.1.0   # OpenAI集成
llama-index-embeddings-openai>=0.1.0  # OpenAI嵌入
llama-index-vector-stores-qdrant>=0.1.0  # Qdrant集成
llama-index-retrievers-bm25>=0.1.0  # BM25检索器

# 爬虫与内容处理
firecrawl>=1.0.0                 # 高级爬虫框架
beautifulsoup4>=4.12.0           # HTML解析
trafilatura>=1.6.0               # 内容提取
lxml>=4.9.3                      # XML/HTML处理

# AI与嵌入
openai>=1.3.0                    # OpenAI API
tiktoken>=0.5.1                  # Token计数
numpy>=1.24.0                    # 数值计算
scikit-learn>=1.3.0              # 向量处理

# 监控与日志
prometheus-client>=0.17.0        # Prometheus指标
structlog>=23.1.0                # 结构化日志
pythonjsonlogger>=2.0.0          # JSON日志格式化

# 开发工具
pytest>=7.4.0                    # 单元测试
pytest-asyncio>=0.21.0           # 异步测试
black>=23.7.0                    # 代码格式化
isort>=5.12.0                    # 导入排序
mypy>=1.5.0                      # 类型检查
```

### 8.3 环境需求

* **开发环境**
  * Python 3.10+
  * Node.js 18+
  * Docker
  * Git

* **生产环境**
  * Azure容器实例或AKS
  * Azure存储（用于文档和索引备份）
  * Azure Cosmos DB（或MongoDB）
  * Azure Cache for Redis
  * Azure OpenAI服务

## 9. 风险和缓解策略

| 风险 | 影响 | 可能性 | 缓解策略 |
|------|------|-------|---------|
| LlamaIndex API变更 | 功能中断 | 中 | 使用适配器模式隔离，版本锁定，自动化测试 |
| Azure文档结构变更 | 爬虫故障 | 中 | 模块化爬虫设计，异常监控，适配器模式 |
| 检索性能下降 | 响应延迟 | 低 | 性能基准测试，缓存策略，降级机制 |
| Azure服务更新过快 | 知识过时 | 高 | 增量更新机制，新鲜度检测，重要服务监控 |
| LLM API成本超支 | 运营成本增加 | 中 | Token预算控制，缓存热门查询，批处理优化 |
| 用户期望与实际能力差距 | 用户失望 | 中 | 明确能力范围，透明引用，连续反馈 |
| 框架冲突 | 开发延迟 | 低 | 清晰架构边界，组件隔离，持续集成 |

### 风险缓解细节

1. **LlamaIndex API变更风险**
   * 实施策略：所有LlamaIndex调用通过适配器层，提供统一接口
   * 监控指标：自动化测试覆盖率，依赖更新警报
   * 应急计划：版本回滚机制，关键组件自主实现备份

2. **Azure文档结构变更风险**
   * 实施策略：页面结构变更检测，爬虫健康监控
   * 监控指标：抓取成功率，文档结构一致性
   * 应急计划：手动抓取流程，临时内容更新

3. **知识更新风险**
   * 实施策略：重要服务自动监控更新，变更检测算法
   * 监控指标：内容新鲜度分数，更新频率统计
   * 应急计划：紧急内容更新流程，重要更新优先级

## 10. 未来扩展

### 10.1 短期扩展计划 (3-6个月)

1. **多语言支持** 
   * 添加中文等主要语言的Azure文档支持
   * 实现语言感知检索和生成

2. **用户个性化** 
   * 基于用户历史和偏好的个性化推荐
   * 用户特定配置和存储的查询历史

3. **代码生成增强** 
   * Azure ARM模板和Terraform配置生成
   * Azure CLI和PowerShell命令生成

### 10.2 中期扩展计划 (6-12个月)

1. **多模态内容处理** 
   * 解析和理解架构图和流程图
   * 生成架构图和可视化推荐

2. **集成调试器** 
   * 与Azure资源分析集成
   * 基于实际资源配置提供建议

3. **企业整合** 
   * 与SSO和企业权限系统集成
   * 团队协作功能和知识共享

### 10.3 长期愿景 (1年+)

1. **自适应RAG引擎** 
   * 基于用户交互自动调整检索策略
   * 持续学习型提示词优化

2. **多云比较系统** 
   * 扩展到AWS、GCP等其他云服务比较
   * 跨云迁移建议和成本分析

3. **预测分析集成** 
   * 资源使用预测和成本预估
   * 主动式优化建议

## 附录

### A. 接口定义

```python
# 核心RAG接口 (抽象基类)
class RAGService(ABC):
    @abstractmethod
    async def query(self, query_text, options=None):
        """执行RAG查询"""
        pass
        
    @abstractmethod
    async def stream_query(self, query_text, options=None):
        """执行流式RAG查询"""
        pass
        
    @abstractmethod
    async def feedback(self, query_id, feedback_data):
        """提交查询反馈"""
        pass

# 文档加载器接口
class DocumentLoader(ABC):
    @abstractmethod
    async def load_documents(self, sources):
        """加载文档"""
        pass

# 索引器接口
class Indexer(ABC):
    @abstractmethod
    async def index_documents(self, documents):
        """索引文档"""
        pass
        
    @abstractmethod
    async def update_documents(self, documents):
        """更新文档"""
        pass
        
    @abstractmethod
    async def delete_documents(self, doc_ids):
        """删除文档"""
        pass

# 检索器接口
class Retriever(ABC):
    @abstractmethod
    async def retrieve(self, query, **kwargs):
        """检索相关内容"""
        pass

# 生成器接口
class Generator(ABC):
    @abstractmethod
    async def generate(self, query, context, **kwargs):
        """生成回答"""
        pass
        
    @abstractmethod
    async def stream_generate(self, query, context, **kwargs):
        """流式生成回答"""
        pass
```

### B. 架构图

```
┌───────────────────────────────────────────────────────────────────────────┐
│                           Azure Calculator RAG系统                        │
├───────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│   ┌───────────────┐     ┌───────────────┐     ┌───────────────┐           │
│   │               │     │               │     │               │           │
│   │ 知识获取系统   │───▶ │ 内容处理系统   │───▶│   检索引擎     │──┐        │
│   │               │     │               │     │               │  │        │
│   └───────────────┘     └───────────────┘     └───────────────┘  │        │
│           │                     │                     │           │       │
│           ▼                     ▼                     ▼           ▼       │
│   ┌───────────────────────────────────────────────────────────────────┐   │
│   │                           抽象接口层                               │   │
│   └───────────────────────────────────────────────────────────────────┘   │
│           │                     │                     │           │       │
│           ▼                     ▼                     ▼           ▼       │
│   ┌───────────────┐     ┌───────────────┐     ┌───────────────┐   │       │
│   │               │     │               │     │               │   │       │
│   │ LlamaIndex    │     │ 自定义处理器   │     │ LlamaIndex    │   │       │
│   │ 文档加载器     │     │               │     │ 检索组件       │   │       │
│   │               │     │               │     │               │   │       │
│   └───────────────┘     └───────────────┘     └───────────────┘   │       │
│                                                                   ▼       │
│                                                         ┌───────────────┐ │
│                                                         │               │ │
│                                                         │ 增强生成系统   │ │
│                                                         │               │ │
│                                                         └───────────────┘ │
│                                                                   │       │
│                                                                   ▼       │
│                                                         ┌───────────────┐ │
│                                                         │               │ │
│                                                         │ 管理平台       │ │
│                                                         │               │ │
│                                                         └───────────────┘ │
└───────────────────────────────────────────────────────────────────────────┘
```

### C. 术语表

| 术语 | 定义 |
|------|------|
| RAG | 检索增强生成 (Retrieval-Augmented Generation) |
| LLM | 大型语言模型 (Large Language Model) |
| 向量嵌入 | 将文本转换为数值向量的过程 |
| 向量索引 | 高效存储和检索向量的数据结构 |
| LlamaIndex | 开源RAG框架，提供文档处理和检索功能 |
| 语义分块 | 基于语义边界分割文档的方法 |
| 混合检索 | 结合向量搜索和关键词搜索的检索方法 |
| 多路径检索 | 使用多种检索策略并融合结果的方法 |
| 重排序 | 对初步检索结果进行二次排序的过程 |
| 适配器模式 | 允许不兼容接口协同工作的设计模式 |
| 结果融合 | 合并多个检索器结果的技术 |
| 自评估 | 系统自我检查回答质量的过程 |

### D. 参考资料

1. [Azure文档中心](https://learn.microsoft.com/azure/)
2. [LlamaIndex文档](https://docs.llamaindex.ai/)
3. [Qdrant向量数据库文档](https://qdrant.tech/documentation/)
4. [Azure OpenAI服务文档](https://learn.microsoft.com/azure/cognitive-services/openai/)
5. [RAG架构最佳实践](https://arxiv.org/abs/2312.10997)