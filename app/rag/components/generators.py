"""
生成器组件 - 基于检索内容生成回答
"""
from typing import List, Dict, Any, Optional
from app.rag.core.registry import register_component, RAGComponentRegistry
from app.rag.core.interfaces import Generator
from app.rag.core.models import TextChunk
from app.core.logging import get_logger
import time

logger = get_logger(__name__)

@register_component(RAGComponentRegistry.GENERATOR, "default")
class DefaultGenerator(Generator):
    """默认生成器 - 基于简单提示词生成回答"""
    
    def __init__(self, llm_service: Any, prompt_template: Optional[str] = None):
        """
        初始化默认生成器
        
        Args:
            llm_service: LLM服务
            prompt_template: 提示词模板
        """
        self.llm_service = llm_service
        self.prompt_template = prompt_template or """
        请基于以下内容回答用户的问题。如果提供的内容中没有相关信息，请说明无法回答，不要编造信息。
        
        内容:
        {context}
        
        用户问题: {query}
        
        在回答中，请引用内容的编号，例如"根据内容2..."。确保你的回答准确且基于提供的内容。特别注意Azure云服务的价格、特性和使用场景。
        """
    
    async def generate(self, query: str, chunks: List[TextChunk], **kwargs) -> str:
        """
        生成回答
        
        Args:
            query: 查询文本
            chunks: 检索结果
            **kwargs: 其他参数
            
        Returns:
            str: 生成的回答
        """
        if not chunks:
            return "抱歉，我没有找到相关信息来回答您的问题。请尝试使用不同的关键词或提供更多上下文。"
            
        try:
            # 记录开始时间
            start_time = time.time()
            
            # 准备上下文
            context = self._prepare_context(chunks)
            
            # 替换模板变量
            prompt = self.prompt_template.replace("{context}", context).replace("{query}", query)
            
            # 使用LLM生成回答
            response = await self.llm_service.chat(prompt, conversation_history=[])
            
            # 记录性能
            elapsed = time.time() - start_time
            logger.debug(f"生成耗时: {elapsed:.3f}秒, 生成了 {len(response.content)} 字符的回答")
            
            return response.content
            
        except Exception as e:
            logger.error(f"生成回答失败: {str(e)}")
            return "抱歉，在处理您的问题时出现了错误。请稍后再试。"
    
    def _prepare_context(self, chunks: List[TextChunk]) -> str:
        """
        准备上下文
        
        Args:
            chunks: 检索结果
            
        Returns:
            str: 格式化的上下文
        """
        context_parts = []
        
        for i, chunk in enumerate(chunks):
            context_parts.append(f"内容 {i+1}:\n{chunk.content}")
        
        return "\n\n".join(context_parts)

@register_component(RAGComponentRegistry.GENERATOR, "contextual")
class ContextualGenerator(Generator):
    """上下文生成器 - 根据查询类型选择不同的提示词模板"""
    
    def __init__(
        self, 
        llm_service: Any,
        prompt_templates: Optional[Dict[str, str]] = None
    ):
        """
        初始化上下文生成器
        
        Args:
            llm_service: LLM服务
            prompt_templates: 提示词模板字典，键为查询类型，值为模板
        """
        self.llm_service = llm_service
        self.prompt_templates = prompt_templates or {
            "default": """
            请基于以下内容回答用户的问题。如果提供的内容中没有相关信息，请说明无法回答，不要编造信息。
            
            内容:
            {context}
            
            用户问题: {query}
            
            在回答中，请引用内容的编号，例如"根据内容2..."。确保你的回答准确且基于提供的内容。特别注意Azure云服务的特性和使用场景。
            """,
            "comparison": """
            请基于以下内容比较用户询问的Azure服务。如果提供的内容中没有足够的信息进行比较，请说明无法完整比较，不要编造信息。
            
            内容:
            {context}
            
            用户比较请求: {query}
            
            在回答中：
            1. 清晰地比较这些服务的主要特点、优势和局限性
            2. 使用表格形式展示关键差异（如适用）
            3. 针对不同场景给出选择建议
            4. 引用具体内容来源，例如"根据内容2..."
            
            确保比较公正客观，基于提供的内容。
            """,
            "pricing": """
            请基于以下内容回答用户关于Azure定价的问题。如果提供的内容中没有足够的价格信息，请说明无法完整回答，不要编造价格。
            
            内容:
            {context}
            
            用户价格问题: {query}
            
            在回答中：
            1. 清晰列出相关的价格信息，包括不同定价模型（如即用即付、预留实例等）
            2. 说明影响价格的因素（如区域、层级、性能级别等）
            3. 如适用，提供成本优化建议
            4. 引用具体内容来源，例如"根据内容2..."
            
            价格信息可能会随时间变化，请提醒用户查看官方价格页面以获取最新信息。
            """
        }
    
    async def generate(self, query: str, chunks: List[TextChunk], **kwargs) -> str:
        """
        生成回答
        
        Args:
            query: 查询文本
            chunks: 检索结果
            **kwargs: 其他参数
            
        Returns:
            str: 生成的回答
        """
        if not chunks:
            return "抱歉，我没有找到相关信息来回答您的问题。请尝试使用不同的关键词或提供更多上下文。"
            
        try:
            # 记录开始时间
            start_time = time.time()
            
            # 准备上下文
            context = self._prepare_context(chunks)
            
            # 确定查询类型
            query_type = kwargs.get("query_type", self._determine_query_type(query))
            
            # 选择模板
            template = self.prompt_templates.get(query_type, self.prompt_templates["default"])
            
            # 替换模板变量
            prompt = template.replace("{context}", context).replace("{query}", query)
            
            # 使用LLM生成回答
            response = await self.llm_service.chat(prompt, conversation_history=[])
            
            # 记录性能
            elapsed = time.time() - start_time
            logger.debug(f"上下文生成耗时: {elapsed:.3f}秒, 生成了 {len(response.content)} 字符的回答, 查询类型: {query_type}")
            
            return response.content
            
        except Exception as e:
            logger.error(f"生成回答失败: {str(e)}")
            return "抱歉，在处理您的问题时出现了错误。请稍后再试。"
    
    def _prepare_context(self, chunks: List[TextChunk]) -> str:
        """
        准备上下文
        
        Args:
            chunks: 检索结果
            
        Returns:
            str: 格式化的上下文
        """
        context_parts = []
        
        for i, chunk in enumerate(chunks):
            context_parts.append(f"内容 {i+1}:\n{chunk.content}")
        
        return "\n\n".join(context_parts)
    
    def _determine_query_type(self, query: str) -> str:
        """
        确定查询类型
        
        Args:
            query: 查询文本
            
        Returns:
            str: 查询类型
        """
        query_lower = query.lower()
        
        # 比较查询
        if any(term in query_lower for term in ["比较", "对比", "区别", "差异", "优缺点", "vs", "versus", "哪个更好"]):
            return "comparison"
            
        # 定价查询
        if any(term in query_lower for term in ["价格", "定价", "成本", "费用", "多少钱", "报价", "价格表"]):
            return "pricing"
            
        # 默认类型
        return "default"

@register_component(RAGComponentRegistry.GENERATOR, "self_critique")
class SelfCritiqueGenerator(Generator):
    """自我批评生成器 - 生成初步回答，然后自我批评并改进"""
    
    def __init__(self, llm_service: Any, base_generator: Generator):
        """
        初始化自我批评生成器
        
        Args:
            llm_service: LLM服务
            base_generator: 基础生成器，用于生成初步回答
        """
        self.llm_service = llm_service
        self.base_generator = base_generator
    
    async def generate(self, query: str, chunks: List[TextChunk], **kwargs) -> str:
        """
        生成回答
        
        Args:
            query: 查询文本
            chunks: 检索结果
            **kwargs: 其他参数
            
        Returns:
            str: 生成的回答
        """
        if not chunks:
            return "抱歉，我没有找到相关信息来回答您的问题。请尝试使用不同的关键词或提供更多上下文。"
            
        try:
            # 记录开始时间
            start_time = time.time()
            
            # 使用基础生成器生成初步回答
            initial_answer = await self.base_generator.generate(query, chunks, **kwargs)
            
            # 准备批评提示词
            critique_prompt = f"""
            我将对以下回答进行批评和改进。回答是针对用户问题的，基于提供的检索内容。
            
            用户问题: {query}
            
            回答:
            {initial_answer}
            
            请分析这个回答，找出以下问题:
            1. 事实错误或不一致
            2. 未充分回答问题的方面
            3. 逻辑或结构问题
            4. 遗漏的重要信息
            5. 可能的改进点
            
            批评:
            """
            
            # 使用LLM生成批评
            critique_response = await self.llm_service.chat(critique_prompt, conversation_history=[])
            critique = critique_response.content
            
            # 准备改进提示词
            improvement_prompt = f"""
            我需要改进以下回答，解决批评中指出的问题。
            
            用户问题: {query}
            
            原始回答:
            {initial_answer}
            
            批评:
            {critique}
            
            请提供改进后的回答，解决上述问题。确保回答准确、全面且直接回应用户问题。
            
            改进后的回答:
            """
            
            # 使用LLM生成改进后的回答
            improvement_response = await self.llm_service.chat(improvement_prompt, conversation_history=[])
            
            # 记录性能
            elapsed = time.time() - start_time
            logger.debug(f"自我批评生成耗时: {elapsed:.3f}秒, 生成了 {len(improvement_response.content)} 字符的回答")
            
            return improvement_response.content
            
        except Exception as e:
            logger.error(f"自我批评生成失败: {str(e)}")
            # 如果自我批评失败，返回初步回答
            try:
                return await self.base_generator.generate(query, chunks, **kwargs)
            except:
                return "抱歉，在处理您的问题时出现了错误。请稍后再试。"