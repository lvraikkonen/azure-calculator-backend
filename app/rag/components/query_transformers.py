"""
查询转换器组件 - 增强和转换用户查询
"""
from typing import List, Dict, Any, Optional, Union
from app.rag.core.registry import register_component, RAGComponentRegistry
from app.rag.core.interfaces import QueryTransformer
from app.core.logging import get_logger
import time
import json

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

@register_component(RAGComponentRegistry.QUERY_TRANSFORMER, "advanced_hyde")
class AdvancedHyDETransformer(QueryTransformer):
    """高级假设文档扩展转换器 - 使用LLM创建富格式假设文档"""

    def __init__(self, llm_service: Any, template: Optional[str] = None):
        """
        初始化高级HyDE转换器

        Args:
            llm_service: LLM服务
            template: 提示词模板，用于生成假设文档
        """
        self.llm_service = llm_service
        self.template = template or """
        请生成一个详细的文档片段，该片段可能包含以下问题的答案。
        考虑这是一个关于Azure云服务的专业文档，包含技术细节、定价信息和配置指南。
        生成的文档应该格式清晰，包含标题、子标题、要点和关键数据。
        不需要直接回答问题，只需生成一个包含相关信息的文档片段。

        问题: {query}

        请生成一个结构化的Azure文档片段:
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

            # 分析查询类型，调整提示词
            query_type = self._analyze_query_type(query)
            adjusted_template = self._get_template_for_type(query_type)

            # 替换模板中的查询
            prompt = adjusted_template.replace("{query}", query)

            # 使用LLM生成假设文档
            response = await self.llm_service.chat(prompt)

            # 获取生成的文本
            hypothetical_doc = response.content.strip()

            # 记录性能
            elapsed = time.time() - start_time
            logger.debug(f"高级HyDE转换耗时: {elapsed:.3f}秒, 生成了 {len(hypothetical_doc)} 字符的假设文档")

            return hypothetical_doc

        except Exception as e:
            logger.error(f"高级HyDE转换失败: {str(e)}")
            # 返回原始查询
            return query

    def _analyze_query_type(self, query: str) -> str:
        """分析查询类型"""
        query_lower = query.lower()

        if any(term in query_lower for term in ["价格", "定价", "成本", "费用"]):
            return "pricing"
        elif any(term in query_lower for term in ["比较", "对比", "vs", "versus"]):
            return "comparison"
        elif any(term in query_lower for term in ["配置", "设置", "部署", "创建"]):
            return "configuration"
        else:
            return "general"

    def _get_template_for_type(self, query_type: str) -> str:
        """获取特定类型的模板"""
        templates = {
            "pricing": """
            请生成一个详细的Azure定价文档片段，可能包含以下价格查询的答案。
            文档应该包含具体的价格表、计费模式、折扣选项和计费示例。
            包含数字、表格和具体的价格点。

            价格查询: {query}

            请生成一个结构化的Azure价格文档片段:
            """,
            "comparison": """
            请生成一个详细的Azure服务比较文档片段，对比相关服务的优缺点。
            文档应该包含功能对比表、性能指标对比、适用场景和价格比较。
            使用表格形式呈现关键差异点。

            比较查询: {query}

            请生成一个结构化的Azure服务比较文档片段:
            """,
            "configuration": """
            请生成一个详细的Azure配置指南片段，说明如何设置或部署相关服务。
            文档应该包含步骤指南、配置参数说明、示例配置和最佳实践。
            包含具体的参数名称、值范围和CLI命令或Portal操作流程。

            配置查询: {query}

            请生成一个结构化的Azure配置文档片段:
            """
        }

        return templates.get(query_type, self.template)

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

@register_component(RAGComponentRegistry.QUERY_TRANSFORMER, "advanced_decomposition")
class AdvancedQueryDecompositionTransformer(QueryTransformer):
    """高级查询分解转换器 - 智能分解复杂查询并指定检索策略"""

    def __init__(self, llm_service: Any, combine_results: bool = False):
        """
        初始化查询分解转换器

        Args:
            llm_service: LLM服务
            combine_results: 是否合并结果
        """
        self.llm_service = llm_service
        self.combine_results = combine_results
        self.sub_queries = []
        self.search_strategies = {}

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
            请分析以下关于Azure云服务的复杂查询，并将其分解为多个子查询以便更有效地检索信息。
            对于每个子查询，请指定最适合的检索策略（向量检索、关键词检索或混合）。

            复杂查询: {query}

            请以JSON格式返回以下内容:
            ```json
            {{
                "sub_queries": [
                    {{
                        "query": "子查询1文本",
                        "focus": "该子查询的重点",
                        "strategy": "vector|keyword|hybrid"
                    }},
                    {{
                        "query": "子查询2文本",
                        "focus": "该子查询的重点",
                        "strategy": "vector|keyword|hybrid"
                    }}
                ],
                "reasoning": "简要说明为什么这样分解查询"
            }}
            ```

            只返回JSON，不要添加其他说明。
            """

            # 使用LLM生成子查询
            response = await self.llm_service.chat(prompt)

            # 解析JSON响应
            try:
                # 提取JSON内容
                import re
                json_match = re.search(r'```json\s*(.*?)\s*```', response.content, re.DOTALL)
                json_str = json_match.group(1) if json_match else response.content

                # 解析JSON
                decomposition = json.loads(json_str)

                # 提取子查询和策略
                self.sub_queries = [item["query"] for item in decomposition.get("sub_queries", [])]
                self.search_strategies = {
                    item["query"]: item["strategy"]
                    for item in decomposition.get("sub_queries", [])
                }

                # 记录分解结果
                logger.debug(f"查询分解: '{query}' -> {len(self.sub_queries)} 个子查询")
                for i, sq in enumerate(self.sub_queries):
                    logger.debug(f"  子查询 {i + 1}: '{sq}' (策略: {self.search_strategies.get(sq, 'default')})")

            except Exception as e:
                logger.error(f"解析查询分解响应失败: {str(e)}")
                # 回退到基本分解
                self.sub_queries = [query]
                self.search_strategies = {query: "hybrid"}

            # 记录性能
            elapsed = time.time() - start_time
            logger.debug(f"高级查询分解耗时: {elapsed:.3f}秒")

            # 如果合并结果，返回所有子查询的组合
            if self.combine_results and self.sub_queries:
                combined_query = " ".join(self.sub_queries)
                return combined_query
            else:
                # 否则，返回原始查询，子查询将在检索阶段使用
                return query

        except Exception as e:
            logger.error(f"高级查询分解失败: {str(e)}")
            # 返回原始查询
            return query

    async def get_sub_queries_with_strategies(self) -> List[Dict[str, str]]:
        """
        获取子查询及其对应的检索策略

        Returns:
            List[Dict[str, str]]: 子查询和策略的列表
        """
        return [
            {"query": query, "strategy": self.search_strategies.get(query, "hybrid")}
            for query in self.sub_queries
        ]

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