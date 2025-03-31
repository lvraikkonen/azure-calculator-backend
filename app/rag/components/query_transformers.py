"""
查询转换器组件 - 增强和转换用户查询
"""
from typing import List, Dict, Any, Optional, Union
from app.rag.core.registry import register_component, RAGComponentRegistry
from app.rag.core.interfaces import QueryTransformer
from app.core.logging import get_logger
import time

logger = get_logger(__name__)

@register_component(RAGComponentRegistry.QUERY_TRANSFORMER, "query_expansion")
class QueryExpansionTransformer(QueryTransformer):
    """查询扩展转换器 - 扩展查询以提高召回率"""
    
    def __init__(self, expansion_terms: Optional[Dict[str, List[str]]] = None):
        """
        初始化查询扩展转换器
        
        Args:
            expansion_terms: 扩展术语字典，键为原始术语，值为扩展术语列表
        """
        self.expansion_terms = expansion_terms or {
            "VM": ["虚拟机", "Virtual Machine"],
            "虚拟机": ["VM", "Virtual Machine"],
            "Azure Kubernetes": ["AKS", "容器服务"],
            "Azure Storage": ["Blob", "存储账户", "存储服务"],
            "SQL": ["数据库", "关系型数据库", "Azure SQL"],
            "Cosmos DB": ["NoSQL", "文档数据库"],
            "应用服务": ["App Service", "Web应用"],
            "Functions": ["函数", "无服务器", "serverless"],
            "价格": ["定价", "成本", "费用"],
        }
    
    async def transform(self, query: str) -> str:
        """
        转换查询
        
        Args:
            query: 原始查询
            
        Returns:
            str: 转换后的查询
        """
        try:
            # 记录开始时间
            start_time = time.time()
            
            expanded_query = query
            
            # 检查每个术语是否存在于查询中
            for term, expansions in self.expansion_terms.items():
                if term.lower() in query.lower():
                    # 将扩展术语添加到查询中
                    expansion_str = " OR ".join([f'"{exp}"' for exp in expansions if exp.lower() not in query.lower()])
                    if expansion_str:
                        expanded_query += f" ({expansion_str})"
            
            # 如果查询已扩展，记录日志
            if expanded_query != query:
                # 记录性能
                elapsed = time.time() - start_time
                logger.debug(f"查询扩展耗时: {elapsed:.3f}秒, '{query}' -> '{expanded_query}'")
            
            return expanded_query
            
        except Exception as e:
            logger.error(f"查询扩展失败: {str(e)}")
            # 返回原始查询
            return query

@register_component(RAGComponentRegistry.QUERY_TRANSFORMER, "hyde")
class HyDETransformer(QueryTransformer):
    """HyDE转换器 - 假设文档扩展"""
    
    def __init__(self, llm_service: Any, template: Optional[str] = None):
        """
        初始化HyDE转换器
        
        Args:
            llm_service: LLM服务
            template: 提示词模板，用于生成假设文档
        """
        self.llm_service = llm_service
        self.template = template or """
        请生成一个简短的文档片段，该片段可能包含以下问题的答案。
        不需要直接回答问题，只需生成一个可能包含答案的文档片段。
        
        问题: {query}
        
        文档片段:
        """
    
    async def transform(self, query: str) -> str:
        """
        转换查询
        
        Args:
            query: 原始查询
            
        Returns:
            str: 转换后的查询（生成的假设文档）
        """
        try:
            # 记录开始时间
            start_time = time.time()
            
            # 替换模板中的查询
            prompt = self.template.replace("{query}", query)
            
            # 使用LLM生成假设文档
            response = await self.llm_service.chat(prompt)
            
            # 获取生成的文本
            hypothetical_doc = response.content.strip()
            
            # 记录性能
            elapsed = time.time() - start_time
            logger.debug(f"HyDE转换耗时: {elapsed:.3f}秒, 生成了 {len(hypothetical_doc)} 字符的假设文档")
            
            return hypothetical_doc
            
        except Exception as e:
            logger.error(f"HyDE转换失败: {str(e)}")
            # 返回原始查询
            return query

@register_component(RAGComponentRegistry.QUERY_TRANSFORMER, "step_back")
class StepBackTransformer(QueryTransformer):
    """StepBack转换器 - 步退思考，将问题分解为更基础的子问题"""
    
    def __init__(self, llm_service: Any):
        """
        初始化StepBack转换器
        
        Args:
            llm_service: LLM服务
        """
        self.llm_service = llm_service
    
    async def transform(self, query: str) -> str:
        """
        转换查询
        
        Args:
            query: 原始查询
            
        Returns:
            str: 转换后的查询（更基础的问题）
        """
        try:
            # 记录开始时间
            start_time = time.time()
            
            # 构建提示词
            prompt = f"""
            对于以下问题，请思考回答这个问题需要了解的更基础、更一般性的概念或知识。
            然后，将原问题改写为一个更基础的问题，这个基础问题能帮助理解和回答原问题。
            
            原问题: {query}
            
            思考:
            1. 回答原问题需要理解哪些概念？
            2. 哪些基础知识是理解这个问题的关键？
            3. 用户可能缺乏哪些背景信息？
            
            请只返回改写后的基础问题，不要返回思考过程。
            """
            
            # 使用LLM生成基础问题
            response = await self.llm_service.chat(prompt)
            
            # 获取生成的文本
            basic_query = response.content.strip()
            
            # 记录性能
            elapsed = time.time() - start_time
            logger.debug(f"StepBack转换耗时: {elapsed:.3f}秒, '{query}' -> '{basic_query}'")
            
            # 组合原问题和基础问题
            combined_query = f"{basic_query} {query}"
            
            return combined_query
            
        except Exception as e:
            logger.error(f"StepBack转换失败: {str(e)}")
            # 返回原始查询
            return query

@register_component(RAGComponentRegistry.QUERY_TRANSFORMER, "decomposition")
class QueryDecompositionTransformer(QueryTransformer):
    """查询分解转换器 - 将复杂查询分解为多个子查询"""
    
    def __init__(self, llm_service: Any, combine_results: bool = False):
        """
        初始化查询分解转换器
        
        Args:
            llm_service: LLM服务
            combine_results: 是否合并结果，如果为True，查询字符串将包含所有子查询
        """
        self.llm_service = llm_service
        self.combine_results = combine_results
        self.sub_queries = []  # 存储生成的子查询
    
    async def transform(self, query: str) -> str:
        """
        转换查询
        
        Args:
            query: 原始查询
            
        Returns:
            str: 转换后的查询
        """
        try:
            # 记录开始时间
            start_time = time.time()
            
            # 构建提示词
            prompt = f"""
            请将以下复杂查询分解为2-3个更简单的子查询，每个子查询关注原问题的一个方面。
            这些子查询将用于检索相关信息，共同回答原问题。
            
            复杂查询: {query}
            
            请按以下格式返回子查询:
            子查询1: [简单查询1]
            子查询2: [简单查询2]
            子查询3: [简单查询3]（如果需要）
            """
            
            # 使用LLM生成子查询
            response = await self.llm_service.chat(prompt)
            
            # 解析子查询
            import re
            sub_query_matches = re.findall(r'子查询\d+:\s*(.*?)(?=子查询\d+:|$)', response.content, re.DOTALL)
            
            # 清理子查询
            self.sub_queries = [sq.strip() for sq in sub_query_matches if sq.strip()]
            
            # 记录性能
            elapsed = time.time() - start_time
            logger.debug(f"查询分解耗时: {elapsed:.3f}秒, 生成了 {len(self.sub_queries)} 个子查询")
            
            # 如果合并结果，返回所有子查询的组合
            if self.combine_results and self.sub_queries:
                combined_query = " ".join(self.sub_queries)
                return combined_query
            else:
                # 否则，返回原始查询，子查询将在检索阶段使用
                return query
            
        except Exception as e:
            logger.error(f"查询分解失败: {str(e)}")
            # 返回原始查询
            return query
    
    async def get_sub_queries(self) -> List[str]:
        """
        获取生成的子查询列表
        
        Returns:
            List[str]: 子查询列表
        """
        return self.sub_queries

@register_component(RAGComponentRegistry.QUERY_TRANSFORMER, "pipeline")
class TransformerPipeline(QueryTransformer):
    """转换器管道 - 将多个转换器串联起来"""
    
    def __init__(self, transformers: List[QueryTransformer]):
        """
        初始化转换器管道
        
        Args:
            transformers: 转换器列表
        """
        self.transformers = transformers
    
    async def transform(self, query: str) -> str:
        """
        转换查询
        
        Args:
            query: 原始查询
            
        Returns:
            str: 转换后的查询
        """
        try:
            # 记录开始时间
            start_time = time.time()
            
            transformed_query = query
            
            # 依次应用每个转换器
            for transformer in self.transformers:
                transformed_query = await transformer.transform(transformed_query)
            
            # 记录性能
            elapsed = time.time() - start_time
            logger.debug(f"转换器管道耗时: {elapsed:.3f}秒, '{query}' -> '{transformed_query}'")
            
            return transformed_query
            
        except Exception as e:
            logger.error(f"转换器管道失败: {str(e)}")
            # 返回原始查询
            return query