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

@register_component(RAGComponentRegistry.CHUNKER, "semantic")
class SemanticChunker(ContentProcessor[Document, TextChunk]):
    """语义分块器 - 基于语义边界分割文档"""
    
    def __init__(self, min_chunk_size: int = 256, max_chunk_size: int = 1024, buffer_size: int = 50):
        """
        初始化语义分块器
        
        Args:
            min_chunk_size: 最小块大小
            max_chunk_size: 最大块大小
            buffer_size: 缓冲区大小
        """
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.buffer_size = buffer_size
        
    async def process(self, documents: List[Document], **kwargs) -> List[TextChunk]:
        """
        处理文档列表，返回文本块
        
        Args:
            documents: 要处理的文档列表
            **kwargs: 其他参数
            
        Returns:
            List[TextChunk]: 处理后的文本块列表
        """
        chunks = []
        
        try:
            for doc in documents:
                # 分割文本
                text_chunks = self._semantic_split(doc.content)
                
                # 创建块
                for i, chunk_text in enumerate(text_chunks):
                    chunk = TextChunk(
                        id=f"{doc.id}_chunk_{i+1}",
                        doc_id=doc.id,
                        content=chunk_text,
                        metadata=doc.metadata
                    )
                    chunks.append(chunk)
            
            logger.debug(f"语义分块器生成了 {len(chunks)} 个块")
            return chunks
            
        except Exception as e:
            logger.error(f"语义分块失败: {str(e)}")
            raise
            
    def _semantic_split(self, text: str) -> List[str]:
        """
        基于语义边界分割文本
        
        Args:
            text: 要分割的文本
            
        Returns:
            List[str]: 分割后的文本块
        """
        import re
        
        # 定义可能的语义边界
        boundaries = [
            r"\n## ", # Markdown 二级标题
            r"\n\n",  # 双空行
            r"\. ",   # 句号后跟空格
            r"\? ",   # 问号后跟空格
            r"\! ",   # 感叹号后跟空格
            r": ",    # 冒号后跟空格
            r"; "     # 分号后跟空格
        ]
        
        # 合并正则表达式
        pattern = "|".join([re.escape(b) for b in boundaries])
        
        # 分割文本
        splits = re.split(f"({pattern})", text)
        
        # 重新组合分割，保留分隔符
        result = []
        current_chunk = ""
        
        for i in range(0, len(splits), 2):
            part = splits[i]
            delimiter = splits[i+1] if i+1 < len(splits) else ""
            
            # 检查当前块大小
            if len(current_chunk) + len(part) + len(delimiter) <= self.max_chunk_size:
                # 添加到当前块
                current_chunk += part + delimiter
            else:
                # 当前块已满，检查是否达到最小大小
                if len(current_chunk) >= self.min_chunk_size:
                    # 存储当前块并开始新块
                    result.append(current_chunk)
                    current_chunk = part + delimiter
                else:
                    # 当前块太小，继续添加
                    current_chunk += part + delimiter
        
        # 添加最后一个块
        if current_chunk:
            result.append(current_chunk)
            
        return result

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

    def _chunk_html(self, doc: Document) -> List[TextChunk]:
        """处理HTML文档"""
        # 类似于Markdown处理，但使用HTML标签
        # 简化实现，专注于HTML标题标签

        # 提取H1-H6标题
        heading_pattern = r"<h([1-6]).*?>(.*?)</h\1>"

        content = doc.content

        # 查找所有标题
        headings = []
        for match in re.finditer(heading_pattern, content, re.IGNORECASE):
            level = int(match.group(1))  # 标题级别
            title = match.group(2)  # 标题文本
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
                            "section_title": self._clean_html(title),
                            "section_level": level,
                            "chunk_type": "html"
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
                        "section_title": self._clean_html(title),
                        "section_level": level,
                        "chunk_type": "html"
                    }
                )
                chunks.append(chunk)

        # 如果没有找到标题，使用默认分块
        if not chunks:
            return self._semantic_split(doc)

        return chunks

    def _clean_html(self, text: str) -> str:
        """清理HTML标签"""
        return re.sub(r'<[^>]+>', '', text).strip()

    def _chunk_pricing(self, doc: Document) -> List[TextChunk]:
        """处理定价文档，重点保留价格和计费模式"""
        # 价格相关模式
        price_patterns = [
            r"(^|\n)价格詳情.*?(?=\n#|\n##|$)",
            r"(^|\n)定价.*?(?=\n#|\n##|$)",
            r"(^|\n)费用.*?(?=\n#|\n##|$)",
            r"(^|\n)计费.*?(?=\n#|\n##|$)",
            r"(^|\n)Pricing.*?(?=\n#|\n##|$)",
            r"(^|\n)Billing.*?(?=\n#|\n##|$)",
            r"(^|\n)Price.*?(?=\n#|\n##|$)",
            r"(^|\n)Cost.*?(?=\n#|\n##|$)"
        ]

        content = doc.content
        chunks = []

        # 查找价格相关部分
        price_sections = []
        for pattern in price_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE | re.DOTALL):
                price_sections.append((match.start(), match.end(), match.group(0)))

        # 如果找到了价格部分，优先处理
        if price_sections:
            # 按位置排序
            price_sections.sort()

            for i, (start, end, section) in enumerate(price_sections):
                # 如果部分太大，进一步分割
                if len(section) > self.max_chunk_size:
                    sub_chunks = self._split_large_chunk(section)
                    for j, sub_content in enumerate(sub_chunks):
                        chunk = TextChunk(
                            id=f"{doc.id}_price_{i}_{j}",
                            doc_id=doc.id,
                            content=sub_content,
                            metadata={
                                **doc.metadata.dict(),
                                "section_type": "pricing",
                                "chunk_type": "pricing"
                            }
                        )
                        chunks.append(chunk)
                else:
                    # 创建价格块
                    chunk = TextChunk(
                        id=f"{doc.id}_price_{i}",
                        doc_id=doc.id,
                        content=section,
                        metadata={
                            **doc.metadata.dict(),
                            "section_type": "pricing",
                            "chunk_type": "pricing"
                        }
                    )
                    chunks.append(chunk)

        # 对于文档的其余部分，使用普通分块
        if not chunks:
            return self._semantic_split(doc)

        # 处理剩余内容
        remaining_chunks = self._semantic_split(doc)

        # 合并结果，确保价格块排在前面
        return chunks + remaining_chunks

    def _chunk_api(self, doc: Document) -> List[TextChunk]:
        """处理API文档，保留API结构"""
        # API相关模式
        api_patterns = [
            r"(^|\n)API 参考.*?(?=\n#|\n##|$)",
            r"(^|\n)API Reference.*?(?=\n#|\n##|$)",
            r"(^|\n)HTTP 请求.*?(?=\n#|\n##|$)",
            r"(^|\n)HTTP Request.*?(?=\n#|\n##|$)",
            r"(^|\n)请求参数.*?(?=\n#|\n##|$)",
            r"(^|\n)Request Parameters.*?(?=\n#|\n##|$)",
            r"(^|\n)响应.*?(?=\n#|\n##|$)",
            r"(^|\n)Response.*?(?=\n#|\n##|$)"
        ]

        content = doc.content
        chunks = []

        # 查找API相关部分
        api_sections = []
        for pattern in api_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE | re.DOTALL):
                api_sections.append((match.start(), match.end(), match.group(0)))

        # 如果找到了API部分，优先处理
        if api_sections:
            # 按位置排序
            api_sections.sort()

            for i, (start, end, section) in enumerate(api_sections):
                # 如果部分太大，进一步分割
                if len(section) > self.max_chunk_size:
                    sub_chunks = self._split_large_chunk(section)
                    for j, sub_content in enumerate(sub_chunks):
                        chunk = TextChunk(
                            id=f"{doc.id}_api_{i}_{j}",
                            doc_id=doc.id,
                            content=sub_content,
                            metadata={
                                **doc.metadata.dict(),
                                "section_type": "api",
                                "chunk_type": "api"
                            }
                        )
                        chunks.append(chunk)
                else:
                    # 创建API块
                    chunk = TextChunk(
                        id=f"{doc.id}_api_{i}",
                        doc_id=doc.id,
                        content=section,
                        metadata={
                            **doc.metadata.dict(),
                            "section_type": "api",
                            "chunk_type": "api"
                        }
                    )
                    chunks.append(chunk)

        # 对于文档的其余部分，使用普通分块
        if not chunks:
            return self._semantic_split(doc)

        # 处理剩余内容
        remaining_chunks = self._semantic_split(doc)

        # 合并结果
        return chunks + remaining_chunks

    def _chunk_structured_content(self, doc: Document, doc_type: str) -> List[TextChunk]:
        """处理结构化内容，如教程和常见问题"""
        # 根据文档类型定义模式
        patterns = []

        if doc_type == "tutorial":
            # 教程通常包含步骤、前提条件等
            patterns = [
                r"(^|\n)步骤 \d+.*?(?=\n步骤 \d+|$)",
                r"(^|\n)Step \d+.*?(?=\nStep \d+|$)",
                r"(^|\n)前提条件.*?(?=\n#|\n##|$)",
                r"(^|\n)Prerequisites.*?(?=\n#|\n##|$)",
                r"(^|\n)概述.*?(?=\n#|\n##|$)",
                r"(^|\n)Overview.*?(?=\n#|\n##|$)"
            ]
            section_type = "tutorial"
        elif doc_type == "faq":
            # 常见问题通常是问答对
            patterns = [
                r"(^|\n)Q:.*?A:.*?(?=\nQ:|$)",
                r"(^|\n)问:.*?答:.*?(?=\n问:|$)",
                r"(^|\n)问题:.*?答案:.*?(?=\n问题:|$)",
                r"(^|\n)Question:.*?Answer:.*?(?=\nQuestion:|$)"
            ]
            section_type = "faq"

        content = doc.content
        chunks = []

        # 查找结构部分
        sections = []
        for pattern in patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE | re.DOTALL):
                sections.append((match.start(), match.end(), match.group(0)))

        # 如果找到了结构部分，优先处理
        if sections:
            # 按位置排序
            sections.sort()

            for i, (start, end, section) in enumerate(sections):
                # 如果部分太大，进一步分割
                if len(section) > self.max_chunk_size:
                    sub_chunks = self._split_large_chunk(section)
                    for j, sub_content in enumerate(sub_chunks):
                        chunk = TextChunk(
                            id=f"{doc.id}_{section_type}_{i}_{j}",
                            doc_id=doc.id,
                            content=sub_content,
                            metadata={
                                **doc.metadata.dict(),
                                "section_type": section_type,
                                "chunk_type": section_type
                            }
                        )
                        chunks.append(chunk)
                else:
                    # 创建结构块
                    chunk = TextChunk(
                        id=f"{doc.id}_{section_type}_{i}",
                        doc_id=doc.id,
                        content=section,
                        metadata={
                            **doc.metadata.dict(),
                            "section_type": section_type,
                            "chunk_type": section_type
                        }
                    )
                    chunks.append(chunk)

        # 对于文档的其余部分，使用普通分块
        if not chunks:
            return self._semantic_split(doc)

        # 处理剩余内容
        remaining_chunks = self._semantic_split(doc)

        # 合并结果
        return chunks + remaining_chunks

    def _chunk_code(self, doc: Document) -> List[TextChunk]:
        """处理代码示例文档"""
        # 代码块模式
        code_patterns = [
            r"```.*?```",  # Markdown代码块
            r"<pre><code>.*?</code></pre>",  # HTML代码块
            r"(^|\n)```.*?```"  # Markdown代码块（带换行）
        ]

        content = doc.content
        chunks = []

        # 查找代码块
        code_sections = []
        for pattern in code_patterns:
            for match in re.finditer(pattern, content, re.DOTALL):
                code_sections.append((match.start(), match.end(), match.group(0)))

        # 如果找到了代码块，优先处理
        if code_sections:
            # 按位置排序
            code_sections.sort()

            # 处理每个代码块
            for i, (start, end, section) in enumerate(code_sections):
                # 创建代码块
                chunk = TextChunk(
                    id=f"{doc.id}_code_{i}",
                    doc_id=doc.id,
                    content=section,
                    metadata={
                        **doc.metadata.dict(),
                        "section_type": "code",
                        "chunk_type": "code"
                    }
                )
                chunks.append(chunk)

                # 查找代码块前后的上下文
                context_before = content[max(0, start - 500):start]
                context_after = content[end:min(len(content), end + 500)]

                # 添加上下文块
                if context_before.strip():
                    chunk_before = TextChunk(
                        id=f"{doc.id}_code_{i}_before",
                        doc_id=doc.id,
                        content=context_before,
                        metadata={
                            **doc.metadata.dict(),
                            "section_type": "code_context",
                            "chunk_type": "code_context",
                            "context_for": f"{doc.id}_code_{i}"
                        }
                    )
                    chunks.append(chunk_before)

                if context_after.strip():
                    chunk_after = TextChunk(
                        id=f"{doc.id}_code_{i}_after",
                        doc_id=doc.id,
                        content=context_after,
                        metadata={
                            **doc.metadata.dict(),
                            "section_type": "code_context",
                            "chunk_type": "code_context",
                            "context_for": f"{doc.id}_code_{i}"
                        }
                    )
                    chunks.append(chunk_after)

        # 如果没有找到代码块，使用默认分块
        if not chunks:
            return self._semantic_split(doc)

        return chunks

    def _semantic_split(self, doc: Document) -> List[TextChunk]:
        """
        基于语义边界分割文档

        Args:
            doc: 文档

        Returns:
            List[TextChunk]: 分块列表
        """
        chunks = []
        content = doc.content

        # 如果内容很小，直接作为一个块
        if len(content) <= self.max_chunk_size:
            chunk = TextChunk(
                id=f"{doc.id}_chunk_1",
                doc_id=doc.id,
                content=content,
                metadata=doc.metadata.dict()
            )
            chunks.append(chunk)
            return chunks

        # 查找所有边界位置
        boundaries = []
        for pattern in self.section_patterns:
            # 获取该模式的权重
            weight = self.boundary_weights.get(pattern, 1)

            # 查找所有匹配
            for match in re.finditer(pattern, content, re.DOTALL):
                boundaries.append((match.start(), weight))

        # 按位置排序
        boundaries.sort()

        # 如果没有找到边界，使用固定大小分块
        if not boundaries:
            return self._fixed_size_split(doc)

        # 基于边界分块
        start_pos = 0
        current_size = 0
        chunk_start = 0

        for pos, weight in boundaries:
            # 当前段落大小
            size = pos - start_pos

            # 如果添加这个段落会超出最大块大小
            if current_size + size > self.max_chunk_size:
                # 切出一个块
                chunk_text = content[chunk_start:start_pos]
                if len(chunk_text) >= self.min_chunk_size:
                    chunk = TextChunk(
                        id=f"{doc.id}_chunk_{len(chunks) + 1}",
                        doc_id=doc.id,
                        content=chunk_text,
                        metadata=doc.metadata.dict()
                    )
                    chunks.append(chunk)

                # 重置计数器
                chunk_start = start_pos
                current_size = size
            else:
                # 累加大小
                current_size += size

            # 更新起始位置
            start_pos = pos

            # 高权重边界强制截断
            if weight >= 8:
                # 切出一个块
                chunk_text = content[chunk_start:pos]
                if len(chunk_text) >= self.min_chunk_size:
                    chunk = TextChunk(
                        id=f"{doc.id}_chunk_{len(chunks) + 1}",
                        doc_id=doc.id,
                        content=chunk_text,
                        metadata=doc.metadata.dict()
                    )
                    chunks.append(chunk)

                # 重置计数器
                chunk_start = pos
                current_size = 0

        # 处理最后一个块
        if start_pos < len(content) and len(content) - chunk_start >= self.min_chunk_size:
            chunk_text = content[chunk_start:]
            chunk = TextChunk(
                id=f"{doc.id}_chunk_{len(chunks) + 1}",
                doc_id=doc.id,
                content=chunk_text,
                metadata=doc.metadata.dict()
            )
            chunks.append(chunk)

        return chunks

    def _fixed_size_split(self, doc: Document) -> List[TextChunk]:
        """固定大小分块"""
        chunks = []
        content = doc.content

        for i in range(0, len(content), self.max_chunk_size - self.overlap_size):
            # 确定块的范围
            start = i
            end = min(i + self.max_chunk_size, len(content))

            # 创建块
            chunk = TextChunk(
                id=f"{doc.id}_chunk_{len(chunks) + 1}",
                doc_id=doc.id,
                content=content[start:end],
                metadata=doc.metadata.dict()
            )
            chunks.append(chunk)

            # 如果已经处理到末尾，退出循环
            if end == len(content):
                break

        return chunks

    def _split_large_chunk(self, text: str) -> List[str]:
        """分割大块文本"""
        # 如果文本小于最大大小，直接返回
        if len(text) <= self.max_chunk_size:
            return [text]

        # 使用段落分割
        paragraphs = re.split(r"\n\n+", text)

        # 重新组合段落为合适大小的块
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            # 如果段落本身超过最大大小，进一步分割
            if len(para) > self.max_chunk_size:
                # 完成当前块
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""

                # 分割大段落
                para_chunks = self._split_paragraph(para)
                chunks.extend(para_chunks)
                continue

            # 检查添加这个段落是否会超出大小限制
            if len(current_chunk) + len(para) + 2 > self.max_chunk_size:
                # 完成当前块
                chunks.append(current_chunk)
                current_chunk = para
            else:
                # 添加段落到当前块
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para

        # 添加最后一个块
        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _split_paragraph(self, paragraph: str) -> List[str]:
        """分割大段落为句子或更小的单位"""
        # 使用句号分割
        sentences = re.split(r"(?<=[.!?])\s+", paragraph)

        # 重新组合句子为合适大小的块
        chunks = []
        current_chunk = ""

        for sentence in sentences:
            # 如果句子本身超过最大大小，按字符分割
            if len(sentence) > self.max_chunk_size:
                # 完成当前块
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""

                # 按字符分割
                for i in range(0, len(sentence), self.max_chunk_size):
                    chunks.append(sentence[i:i + self.max_chunk_size])
                continue

            # 检查添加这个句子是否会超出大小限制
            if len(current_chunk) + len(sentence) + 1 > self.max_chunk_size:
                # 完成当前块
                chunks.append(current_chunk)
                current_chunk = sentence
            else:
                # 添加句子到当前块
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence

        # 添加最后一个块
        if current_chunk:
            chunks.append(current_chunk)

        return chunks