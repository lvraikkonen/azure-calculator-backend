"""
重排序组件 - 对检索结果进行二次排序
"""
from typing import List, Dict, Any, Optional
from app.rag.core.registry import register_component, RAGComponentRegistry
from app.rag.core.models import TextChunk
from app.rag.core.interfaces import EmbeddingProvider
from app.core.logging import get_logger
import time
import re

logger = get_logger(__name__)

@register_component(RAGComponentRegistry.RERANKER, "cross_encoder")
class CrossEncoderReranker:
    """交叉编码器重排序器 - 使用交叉编码器模型进行高精度重排序"""
    
    def __init__(
        self, 
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        device: str = "cpu",
        batch_size: int = 8
    ):
        """
        初始化交叉编码器重排序器
        
        Args:
            model_name: 模型名称
            device: 设备，'cpu'或'cuda'
            batch_size: 批处理大小
        """
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        self.model = None
        
    def _load_model(self):
        """加载模型（延迟加载）"""
        # 目前实现需要额外安装：pip install sentence-transformers
        if self.model is None:
            try:
                from sentence_transformers import CrossEncoder
                self.model = CrossEncoder(self.model_name, device=self.device)
                logger.info(f"已加载交叉编码器模型: {self.model_name}")
            except Exception as e:
                logger.error(f"加载交叉编码器模型失败: {str(e)}")
                raise
    
    async def rerank(self, query: str, chunks: List[TextChunk], top_k: int = None) -> List[TextChunk]:
        """
        重新排序检索结果
        
        Args:
            query: 查询文本
            chunks: 检索结果
            top_k: 返回结果数量
            
        Returns:
            List[TextChunk]: 重排序后的结果
        """
        if not chunks:
            return []
            
        try:
            # 记录开始时间
            start_time = time.time()
            
            # 加载模型
            self._load_model()
            
            # 准备输入对
            pairs = [(query, chunk.content) for chunk in chunks]
            
            # 计算分数
            scores = self.model.predict(pairs)
            
            # 创建重排序的结果
            reranked_chunks = []
            for i, chunk in enumerate(chunks):
                # 创建新块，更新得分
                reranked_chunk = TextChunk(
                    id=chunk.id,
                    doc_id=chunk.doc_id,
                    content=chunk.content,
                    metadata=chunk.metadata,
                    embedding=chunk.embedding,
                    score=float(scores[i])
                )
                
                reranked_chunks.append(reranked_chunk)
            
            # 按分数排序
            reranked_chunks.sort(key=lambda x: x.score or 0, reverse=True)
            
            # 限制结果数量
            if top_k is not None:
                reranked_chunks = reranked_chunks[:top_k]
            
            # 记录性能
            elapsed = time.time() - start_time
            logger.debug(f"交叉编码器重排序耗时: {elapsed:.3f}秒, 返回 {len(reranked_chunks)} 个结果")
            
            return reranked_chunks
            
        except Exception as e:
            logger.error(f"交叉编码器重排序失败: {str(e)}")
            # 返回原始结果
            return chunks

@register_component(RAGComponentRegistry.RERANKER, "llm_reranker")
class LLMReranker:
    """LLM重排序器 - 使用LLM评估文档与查询的相关性"""

    def __init__(
            self,
            llm_service: Any,
            batch_size: int = 5,
            max_input_tokens: int = 4000,
            detailed_scoring: bool = False
    ):
        """
        初始化LLM重排序器

        Args:
            llm_service: LLM服务
            batch_size: 批处理大小，一次评估多少个块
            max_input_tokens: 最大输入令牌数
            detailed_scoring: 是否返回详细评分
        """
        self.llm_service = llm_service
        self.batch_size = batch_size
        self.max_input_tokens = max_input_tokens
        self.detailed_scoring = detailed_scoring

    async def rerank(self, query: str, chunks: List[TextChunk], top_k: int = None) -> List[TextChunk]:
        """
        重新排序检索结果

        Args:
            query: 查询文本
            chunks: 检索结果
            top_k: 返回结果数量

        Returns:
            List[TextChunk]: 重排序后的结果
        """
        if not chunks:
            return []

        try:
            # 记录开始时间
            start_time = time.time()

            # 如果结果很少，无需批处理
            if len(chunks) <= self.batch_size:
                reranked_chunks = await self._rerank_batch(query, chunks)
            else:
                # 分批处理
                all_reranked = []
                for i in range(0, len(chunks), self.batch_size):
                    batch = chunks[i:i + self.batch_size]
                    reranked_batch = await self._rerank_batch(query, batch)
                    all_reranked.extend(reranked_batch)

                # 再次排序以确保一致性
                reranked_chunks = sorted(all_reranked, key=lambda x: x.score or 0, reverse=True)

            # 限制结果数量
            if top_k is not None:
                reranked_chunks = reranked_chunks[:top_k]

            # 记录性能
            elapsed = time.time() - start_time
            logger.debug(f"LLM重排序耗时: {elapsed:.3f}秒, 返回 {len(reranked_chunks)} 个结果")

            return reranked_chunks

        except Exception as e:
            logger.error(f"LLM重排序失败: {str(e)}")
            # 返回原始结果
            return chunks[:top_k] if top_k is not None else chunks

    async def _rerank_batch(self, query: str, chunks: List[TextChunk]) -> List[TextChunk]:
        """
        重排序单个批次

        Args:
            query: 查询文本
            chunks: 检索结果批次

        Returns:
            List[TextChunk]: 重排序后的结果
        """
        # 准备提示词
        prompt = self._prepare_scoring_prompt(query, chunks)

        # 调用LLM
        response = await self.llm_service.chat(prompt)

        # 解析分数
        chunk_scores = self._parse_scores(response.content, chunks)

        # 创建重排序后的块
        reranked_chunks = []
        for chunk, new_score in zip(chunks, chunk_scores):
            # 仅当新分数有效时更新
            if new_score is not None:
                # 创建新块，更新得分
                reranked_chunk = TextChunk(
                    id=chunk.id,
                    doc_id=chunk.doc_id,
                    content=chunk.content,
                    metadata=chunk.metadata,
                    embedding=chunk.embedding,
                    score=new_score
                )

                reranked_chunks.append(reranked_chunk)
            else:
                # 使用原始块
                reranked_chunks.append(chunk)

        # 按分数排序
        reranked_chunks.sort(key=lambda x: x.score or 0, reverse=True)

        return reranked_chunks

    def _prepare_scoring_prompt(self, query: str, chunks: List[TextChunk]) -> str:
        """
        准备评分提示词

        Args:
            query: 查询文本
            chunks: 检索结果批次

        Returns:
            str: 评分提示词
        """
        prompt = f"""
        请评估以下文本段落与查询的相关性。

        查询: {query}

        文本段落:
        """

        # 添加每个块
        for i, chunk in enumerate(chunks):
            # 截断过长的内容
            content = chunk.content
            if len(content) > self.max_input_tokens // len(chunks):
                content = content[:self.max_input_tokens // len(chunks)] + "..."

            prompt += f"\n[{i + 1}] {content}\n"

        # 添加评分指南
        if self.detailed_scoring:
            prompt += """
            为每个段落评分，打分范围为0-10，并解释评分理由。包括以下方面的评估:
            - 相关性：内容与查询的直接相关程度
            - 信息质量：信息的深度、准确性和专业性
            - 完整性：回答问题所需的信息完整度

            请使用以下格式返回分数:

            段落[1]: 分数=X.X
            理由：...

            段落[2]: 分数=X.X
            理由：...

            ...
            """
        else:
            prompt += """
            为每个段落的相关性评分，打分范围为0-10。

            请使用以下格式返回分数:

            段落[1]: X.X
            段落[2]: X.X
            ...
            """

        return prompt

    def _parse_scores(self, response: str, chunks: List[TextChunk]) -> List[float]:
        """
        解析LLM响应中的分数

        Args:
            response: LLM响应文本
            chunks: 原始块列表

        Returns:
            List[float]: 分数列表
        """
        # 初始化返回值
        scores = [None] * len(chunks)

        # 解析LLM评分
        import re

        if self.detailed_scoring:
            pattern = r'段落\[(\d+)\]:\s*分数=(\d+(?:\.\d+)?)'
        else:
            pattern = r'段落\[(\d+)\]:\s*(\d+(?:\.\d+)?)'

        # 查找所有匹配
        for match in re.finditer(pattern, response):
            idx = int(match.group(1)) - 1  # 段落编号从1开始
            score = float(match.group(2))

            # 确保索引有效
            if 0 <= idx < len(chunks):
                # 将0-10分转换为0-1分
                scores[idx] = score / 10.0

        # 处理未找到分数的情况
        for i, score in enumerate(scores):
            if score is None:
                # 使用现有的分数或默认值
                scores[i] = chunks[i].score or 0.5

        return scores

@register_component(RAGComponentRegistry.RERANKER, "azure_specialized_reranker")
class AzureSpecializedReranker:
    """Azure专用重排序器 - 针对Azure文档的特定重排序逻辑"""

    def __init__(
            self,
            base_reranker: Any,
            pricing_keywords: List[str] = None,
            comparison_keywords: List[str] = None,
            service_mappings: Dict[str, List[str]] = None,
            boost_recent: bool = True,
            top_k: int = 5
    ):
        """
        初始化Azure专用重排序器

        Args:
            base_reranker: 基础重排序器
            pricing_keywords: 定价相关关键词
            comparison_keywords: 比较相关关键词
            service_mappings: 服务映射，用于标准化服务名称
            boost_recent: 是否提升最近文档
            top_k: 返回结果数量
        """
        self.base_reranker = base_reranker
        self.pricing_keywords = pricing_keywords or [
            "价格", "定价", "费用", "成本", "计费", "价格表",
            "price", "pricing", "cost", "billing", "expense", "charge"
        ]
        self.comparison_keywords = comparison_keywords or [
            "比较", "对比", "区别", "差异", "优缺点", "何时使用",
            "compare", "comparison", "difference", "versus", "vs", "pros and cons"
        ]
        self.service_mappings = service_mappings or {
            "vm": ["虚拟机", "virtual machine", "azure vm", "compute", "计算实例"],
            "storage": ["存储", "blob", "文件", "file", "table", "queue", "数据存储"],
            "database": ["数据库", "sql", "cosmos", "mysql", "postgresql", "nosql"],
            "kubernetes": ["容器", "container", "aks", "k8s"],
            "app service": ["应用服务", "网站", "web app", "webapp"],
            "functions": ["函数", "function app", "无服务器", "serverless"]
        }
        self.boost_recent = boost_recent
        self.top_k = top_k

    async def rerank(self, query: str, chunks: List[TextChunk], top_k: int = None, **kwargs) -> List[TextChunk]:
        """
        重新排序检索结果

        Args:
            query: 查询文本
            chunks: 检索结果
            top_k: 返回结果数量
            **kwargs: 其他参数

        Returns:
            List[TextChunk]: 重排序后的结果
        """
        if not chunks:
            return []

        try:
            # 记录开始时间
            start_time = time.time()

            # 使用传入的top_k或默认值
            k = top_k if top_k is not None else self.top_k

            # 使用基础重排序器获取初始排序
            reranked_chunks = await self.base_reranker.rerank(query, chunks, k, **kwargs)

            # 分析查询类型
            query_type = self._analyze_query_type(query)

            # 应用Azure特定的调整
            final_chunks = self._apply_azure_adjustments(reranked_chunks, query, query_type)

            # 限制结果数量
            final_results = final_chunks[:k]

            # 记录性能
            elapsed = time.time() - start_time
            logger.debug(
                f"Azure专用重排序耗时: {elapsed:.3f}秒, 返回 {len(final_results)} 个结果, 查询类型: {query_type}")

            return final_results

        except Exception as e:
            logger.error(f"Azure专用重排序失败: {str(e)}")
            # 如果基础重排序器成功，返回其结果
            if self.base_reranker:
                try:
                    return await self.base_reranker.rerank(query, chunks, top_k)
                except:
                    pass
            # 否则返回原始结果
            return chunks[:top_k] if top_k is not None else chunks

    def _analyze_query_type(self, query: str) -> str:
        """
        分析查询类型

        Args:
            query: 查询文本

        Returns:
            str: 查询类型
        """
        query_lower = query.lower()

        # 检查是否为定价查询
        if any(keyword in query_lower for keyword in self.pricing_keywords):
            return "pricing"

        # 检查是否为比较查询
        if any(keyword in query_lower for keyword in self.comparison_keywords):
            return "comparison"

        # 检查是否为配置查询
        if any(term in query_lower for term in
               ["如何", "怎么", "配置", "设置", "创建", "部署", "how to", "setup", "configure"]):
            return "configuration"

        # 默认为一般查询
        return "general"

    def _apply_azure_adjustments(self, chunks: List[TextChunk], query: str, query_type: str) -> List[TextChunk]:
        """
        应用Azure特定的重排序调整

        Args:
            chunks: 重排序块
            query: 查询文本
            query_type: 查询类型

        Returns:
            List[TextChunk]: 调整后的块
        """
        adjusted_chunks = []

        # 提取查询中的服务引用
        referenced_services = self._extract_services(query)

        for chunk in chunks:
            # 基础分数
            score = chunk.score or 0.5

            # 获取调整后的分数
            adjusted_score = self._adjust_score_by_type(
                score,
                chunk,
                query_type,
                referenced_services
            )

            # 创建新块，更新得分
            adjusted_chunk = TextChunk(
                id=chunk.id,
                doc_id=chunk.doc_id,
                content=chunk.content,
                metadata=chunk.metadata,
                embedding=chunk.embedding,
                score=adjusted_score
            )

            adjusted_chunks.append(adjusted_chunk)

        # 按调整后的分数排序
        adjusted_chunks.sort(key=lambda x: x.score or 0, reverse=True)

        return adjusted_chunks

    def _extract_services(self, query: str) -> List[str]:
        """
        从查询中提取服务引用

        Args:
            query: 查询文本

        Returns:
            List[str]: 引用的服务列表
        """
        query_lower = query.lower()
        referenced = []

        # 检查每个服务和其别名
        for service, aliases in self.service_mappings.items():
            if service in query_lower:
                referenced.append(service)
            else:
                # 检查别名
                for alias in aliases:
                    if alias in query_lower:
                        referenced.append(service)
                        break

        return referenced

    def _adjust_score_by_type(
            self,
            score: float,
            chunk: TextChunk,
            query_type: str,
            referenced_services: List[str]
    ) -> float:
        """
        根据查询类型调整分数

        Args:
            score: 原始分数
            chunk: 文本块
            query_type: 查询类型
            referenced_services: 引用的服务

        Returns:
            float: 调整后的分数
        """
        # 检查内容类型
        content_lower = chunk.content.lower()

        # 基于查询类型进行调整
        if query_type == "pricing":
            # 如果内容包含价格相关关键词，提升分数
            if any(keyword in content_lower for keyword in self.pricing_keywords):
                score *= 1.3

            # 如果包含具体数字（可能是价格），提升分数
            if re.search(r'\$\d+|\d+\s*(元|美元|欧元)', content_lower):
                score *= 1.2

        elif query_type == "comparison":
            # 如果内容包含比较关键词，提升分数
            if any(keyword in content_lower for keyword in self.comparison_keywords):
                score *= 1.25

            # 如果内容同时包含多个被引用的服务，大幅提升分数
            mentioned_services = 0
            for service in referenced_services:
                if service in content_lower or any(
                        alias in content_lower for alias in self.service_mappings.get(service, [])):
                    mentioned_services += 1

            if mentioned_services >= 2:
                score *= 1.3
            elif mentioned_services == 1 and len(referenced_services) >= 2:
                # 包含部分被引用的服务，适度提升
                score *= 1.1

        elif query_type == "configuration":
            # 如果内容包含步骤指南特征，提升分数
            if re.search(r'步骤|第.步|首先|然后|接下来|最后|步骤|step|first|then|next|finally', content_lower):
                score *= 1.2

            # 如果包含代码或命令样例，提升分数
            if re.search(r'```|az\s+|azcli|powershell|cmd|bash', content_lower):
                score *= 1.15

        # 通用调整：提升包含引用服务的结果
        if referenced_services:
            for service in referenced_services:
                if service in content_lower or any(
                        alias in content_lower for alias in self.service_mappings.get(service, [])):
                    score *= 1.1
                    break

        # 如果启用了时效性提升
        if self.boost_recent and hasattr(chunk.metadata, "created_at"):
            import datetime

            # 获取创建日期
            created_at = chunk.metadata.created_at
            modified_at = chunk.metadata.modified_at or created_at

            if modified_at:
                # 计算天数差异
                now = datetime.datetime.now()
                try:
                    # 日期可能是字符串
                    if isinstance(modified_at, str):
                        modified_at = datetime.datetime.fromisoformat(modified_at.replace('Z', '+00:00'))

                    delta = now - modified_at
                    days = delta.days

                    # 根据时效性调整分数
                    if days <= 30:  # 一个月内
                        score *= 1.15
                    elif days <= 90:  # 三个月内
                        score *= 1.08
                    elif days <= 180:  # 六个月内
                        score *= 1.04
                except:
                    # 忽略解析错误
                    pass

        return score