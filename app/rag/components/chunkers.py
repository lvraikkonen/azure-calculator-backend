"""
文本分块器组件 - 将文档分割为可管理的块
"""
from typing import List, Dict, Any, Optional
from app.rag.core.registry import register_component, RAGComponentRegistry
from app.rag.core.interfaces import ContentProcessor
from app.rag.core.models import Document, TextChunk
from app.core.logging import get_logger
import uuid
import re

logger = get_logger(__name__)


@register_component(RAGComponentRegistry.CHUNKER, "sentence_window")
class SentenceWindowChunker(ContentProcessor[Document, TextChunk]):
    """句子窗口分块器 - 使用滑动窗口分割文档"""
    
    def __init__(
        self, 
        chunk_size: int = 1024, 
        chunk_overlap: int = 200,
        window_metadata_key: str = "window",
        original_text_metadata_key: str = "original_text"
    ):
        """
        初始化句子窗口分块器
        
        Args:
            chunk_size: 块大小
            chunk_overlap: 块重叠大小
            window_metadata_key: 窗口元数据键
            original_text_metadata_key: 原始文本元数据键
        """
        from llama_index.core.node_parser import SentenceWindowNodeParser
        
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.window_metadata_key = window_metadata_key
        self.original_text_metadata_key = original_text_metadata_key
        
        self.parser = SentenceWindowNodeParser.from_defaults(
            window_size=chunk_size,
            window_metadata_key=window_metadata_key,
            original_text_metadata_key=original_text_metadata_key
        )
    
    async def process(self, documents: List[Document], **kwargs) -> List[TextChunk]:
        """
        处理文档列表，返回文本块
        
        Args:
            documents: 要处理的文档列表
            **kwargs: 其他参数
            
        Returns:
            List[TextChunk]: 处理后的文本块列表
        """
        from app.rag.adapters.llama_converters import to_llama_document, from_llama_node
        
        chunks = []
        
        try:
            # 将自定义文档转换为LlamaIndex文档
            llama_docs = [to_llama_document(doc) for doc in documents]
            
            # 使用解析器获取节点
            llama_nodes = self.parser.get_nodes_from_documents(llama_docs)
            
            # 将LlamaIndex节点转换为自定义块
            for node in llama_nodes:
                # 找到对应的文档
                doc_id = node.metadata.get("doc_id", "unknown")
                
                # 创建块
                chunk = TextChunk(
                    id=str(uuid.uuid4()),
                    doc_id=doc_id,
                    content=node.text,
                    metadata=from_llama_node(node).metadata,
                    embedding=node.embedding
                )
                
                chunks.append(chunk)
                
            logger.debug(f"分块器生成了 {len(chunks)} 个块")
            return chunks
            
        except Exception as e:
            logger.error(f"文档分块失败: {str(e)}")
            raise


@register_component(RAGComponentRegistry.CHUNKER, "advanced_semantic")
class AdvancedSemanticChunker(ContentProcessor[Document, TextChunk]):
    """高级语义分块器 - 基于语义和结构进行智能分块"""

    def __init__(
            self,
            min_chunk_size: int = 256,
            max_chunk_size: int = 1024,
            overlap_size: int = 50,
            respect_structure: bool = True,
            azure_optimized: bool = True
    ):
        """
        初始化高级语义分块器

        Args:
            min_chunk_size: 最小块大小
            max_chunk_size: 最大块大小
            overlap_size: 重叠大小
            respect_structure: 是否尊重文档结构（标题、列表等）
            azure_optimized: 是否针对Azure文档优化
        """
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.overlap_size = overlap_size
        self.respect_structure = respect_structure
        self.azure_optimized = azure_optimized

        # 初始化边界模式
        self.section_patterns = [
            # 标题模式
            r"(^|\n)# (.+?)(?=\n)",  # Markdown一级标题
            r"(^|\n)## (.+?)(?=\n)",  # Markdown二级标题
            r"(^|\n)### (.+?)(?=\n)",  # Markdown三级标题
            r"(^|\n)<h1>(.+?)</h1>",  # HTML一级标题
            r"(^|\n)<h2>(.+?)</h2>",  # HTML二级标题
            r"(^|\n)<h3>(.+?)</h3>",  # HTML三级标题

            # Azure特定模式
            r"(^|\n)服务概述(.+?)(?=\n)",  # 服务概述
            r"(^|\n)定价详情(.+?)(?=\n)",  # 定价详情
            r"(^|\n)技术规格(.+?)(?=\n)",  # 技术规格
            r"(^|\n)常见问题(.+?)(?=\n)",  # 常见问题

            # 段落边界
            r"(\n\n+)",  # 多个换行

            # 其他结构边界
            r"(^|\n)[\*\-\+] (.+?)(?=\n)",  # 无序列表项
            r"(^|\n)\d+\. (.+?)(?=\n)",  # 有序列表项
            r"(^|\n)>\s(.+?)(?=\n)",  # 引用块
            r"(^|\n)```(.+?)```",  # 代码块

            # 句子边界
            r"\.(?=\s[A-Z])",  # 句号后跟空格和大写字母
            r"\?(?=\s[A-Z])",  # 问号后跟空格和大写字母
            r"!(?=\s[A-Z])"  # 感叹号后跟空格和大写字母
        ]

        # Azure特定边界权重 - 越高越重要
        self.boundary_weights = {
            r"(^|\n)# (.+?)(?=\n)": 10,  # 一级标题
            r"(^|\n)## (.+?)(?=\n)": 8,  # 二级标题
            r"(^|\n)### (.+?)(?=\n)": 6,  # 三级标题
            r"(^|\n)服务概述(.+?)(?=\n)": 9,  # 服务概述
            r"(^|\n)定价详情(.+?)(?=\n)": 9,  # 定价详情
            r"(\n\n+)": 5,  # 多个换行
            r"\.(?=\s[A-Z])": 3,  # 句子边界
        }

    async def process(self, documents: List[Document], **kwargs) -> List[TextChunk]:
        """
        处理文档列表，返回语义分块

        Args:
            documents: 要处理的文档列表
            **kwargs: 其他参数

        Returns:
            List[TextChunk]: 处理后的文本块列表
        """
        chunks = []

        for doc in documents:
            # 检查文档类型，选择适当的分块策略
            doc_type = self._infer_document_type(doc)

            # 获取文档分块
            doc_chunks = self._chunk_document(doc, doc_type)

            # 添加到结果
            chunks.extend(doc_chunks)

        logger.debug(f"高级语义分块器生成了 {len(chunks)} 个块")
        return chunks

    def _infer_document_type(self, doc: Document) -> str:
        """
        推断文档类型

        Args:
            doc: 文档

        Returns:
            str: 文档类型
        """
        content = doc.content.lower()
        source = doc.metadata.source.lower() if doc.metadata.source else ""

        # 检查文档内容和来源，推断类型
        if "price" in source or "pricing" in source or "定价" in source:
            return "pricing"
        elif "overview" in source or "概述" in source:
            return "overview"
        elif "api-reference" in source or "api" in source:
            return "api"
        elif "tutorial" in source or "教程" in source or "quickstart" in source:
            return "tutorial"
        elif "faq" in source or "常见问题" in source:
            return "faq"
        elif ".md" in source:
            return "markdown"
        elif ".html" in source or ".htm" in source:
            return "html"

        # 基于内容特征推断
        if "```" in content or "def " in content or "function " in content:
            return "code"
        elif "#" in content and "##" in content:
            return "markdown"
        elif "<h1>" in content or "<p>" in content:
            return "html"
        elif "价格" in content or "定价" in content or "费用" in content:
            return "pricing"
        elif "步骤" in content or "第一步" in content:
            return "tutorial"

        # 默认类型
        return "general"

    def _chunk_document(self, doc: Document, doc_type: str) -> List[TextChunk]:
        """
        根据文档类型和内容分块

        Args:
            doc: 文档
            doc_type: 文档类型

        Returns:
            List[TextChunk]: 分块列表
        """
        # 根据文档类型选择分块策略
        if doc_type == "markdown":
            chunks = self._chunk_markdown(doc)
        elif doc_type == "html":
            chunks = self._chunk_html(doc)
        elif doc_type == "pricing":
            chunks = self._chunk_pricing(doc)
        elif doc_type == "api":
            chunks = self._chunk_api(doc)
        elif doc_type in ["tutorial", "faq"]:
            chunks = self._chunk_structured_content(doc, doc_type)
        elif doc_type == "code":
            chunks = self._chunk_code(doc)
        else:
            # 默认分块策略
            chunks = self._semantic_split(doc)

        return chunks

    def _chunk_markdown(self, doc: Document) -> List[TextChunk]:
        """处理Markdown文档"""
        # 标题模式
        heading_pattern = r"(^|\n)(#+)\s+(.+?)(?=\n)"

        # 查找所有标题和内容
        content = doc.content

        # 查找所有标题
        headings = []
        for match in re.finditer(heading_pattern, content, re.MULTILINE):
            level = len(match.group(2))  # 标题级别
            title = match.group(3)  # 标题文本
            position = match.start()  # 位置
            headings.append((level, title, position))

        # 分割文档为带标题的块
        chunks = []
        for i, (level, title, pos) in enumerate(headings):
            # 块的结束位置是下一个标题的位置或文档末尾
            end_pos = headings[i + 1][2] if i + 1 < len(headings) else len(content)

            # 提取块内容
            chunk_content = content[pos:end_pos]

            # 如果块太大，进一步分割
            if len(chunk_content) > self.max_chunk_size:
                sub_chunks = self._split_large_chunk(chunk_content)
                for j, sub_content in enumerate(sub_chunks):
                    chunk = TextChunk(
                        id=f"{doc.id}_chunk_{i}_{j}",
                        doc_id=doc.id,
                        content=sub_content,
                        metadata={
                            **doc.metadata.dict(),
                            "section_title": title,
                            "section_level": level,
                            "chunk_type": "markdown"
                        }
                    )
                    chunks.append(chunk)
            else:
                # 创建块
                chunk = TextChunk(
                    id=f"{doc.id}_chunk_{i}",
                    doc_id=doc.id,
                    content=chunk_content,
                    metadata={
                        **doc.metadata.dict(),
                        "section_title": title,
                        "section_level": level,
                        "chunk_type": "markdown"
                    }
                )
                chunks.append(chunk)

        # 如果没有找到标题，使用默认分块
        if not chunks:
            return self._semantic_split(doc)

        return chunks

    # TODO list

    # _chunk_html """处理HTML文档"""
    # _clean_html """清理HTML标签"""
    # _chunk_pricing """处理定价文档，重点保留价格和计费模式"""
    # _chunk_api """处理API文档，保留API结构"""
    # _chunk_structured_content """处理结构化内容，如教程和常见问题"""
    # _chunk_code """处理代码示例文档"""
    # _semantic_split """基于语义边界分割文档"""
    # _fixed_size_split """固定大小分块"""
    # _split_large_chunk """分割大块文本"""
    # _split_paragraph """分割大段落为句子或更小的单位"""