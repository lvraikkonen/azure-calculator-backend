"""
RAG评估指标实现
"""
from typing import Dict, Any, List, Optional
from app.rag.core.models import QueryResult
from app.rag.evaluation.base import Metric
from app.core.logging import get_logger
from app.services.llm_service import LLMService

logger = get_logger(__name__)

class RelevanceMetric(Metric):
    """相关性评估指标 - 评估检索内容与查询的相关性"""
    
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
    
    async def calculate(self, query_result: QueryResult, **kwargs) -> float:
        """计算相关性分数"""
        try:
            # 使用LLM评估检索内容的相关性
            if not query_result.chunks:
                return 0.0
                
            prompt = f"""
            请评估以下检索内容与查询问题的相关性。
            
            查询问题: {query_result.query}
            
            检索内容:
            """
            
            # 添加检索内容
            for i, chunk in enumerate(query_result.chunks):
                prompt += f"\n内容 {i+1}: {chunk.content[:300]}..." if len(chunk.content) > 300 else f"\n内容 {i+1}: {chunk.content}"
            
            prompt += """
            
            请根据检索内容与查询问题的相关程度打分:
            - 0.0: 完全不相关，内容与问题毫无关系
            - 0.3: 轻微相关，内容含有问题领域的一般信息
            - 0.5: 部分相关，内容包含部分问题需要的信息
            - 0.7: 较为相关，内容大部分能回答问题
            - 1.0: 高度相关，内容完全能回答问题
            
            仅返回一个0.0到1.0之间的浮点数作为相关性评分。
            """
            
            # 调用LLM
            response = await self.llm_service.chat(prompt)
            
            # 解析分数
            content = response.content.strip()
            
            # 提取数字
            import re
            score_match = re.search(r'(\d+\.\d+|\d+)', content)
            if score_match:
                score = float(score_match.group(1))
                
                # 确保分数在有效范围内
                score = max(0.0, min(1.0, score))
                
                return score
            
            # 如果无法提取数字，返回默认值
            logger.warning(f"无法从LLM响应中提取相关性分数: {content}")
            return 0.5
            
        except Exception as e:
            logger.error(f"计算相关性分数失败: {str(e)}")
            return 0.0
    
    @property
    def name(self) -> str:
        return "relevance"
    
    @property
    def description(self) -> str:
        return "评估检索内容与查询的相关性"

class FaithfulnessMetric(Metric):
    """忠实度评估指标 - 评估生成内容与检索内容的一致性"""
    
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
    
    async def calculate(self, query_result: QueryResult, **kwargs) -> float:
        """计算忠实度分数"""
        try:
            # 使用LLM评估生成内容的忠实度
            if not query_result.chunks or not query_result.answer:
                return 0.0
                
            prompt = f"""
            请评估生成答案与检索内容的忠实度。忠实度指生成答案中的信息是否都能在检索内容中找到支持。
            
            检索内容:
            """
            
            # 添加检索内容
            for i, chunk in enumerate(query_result.chunks):
                prompt += f"\n内容 {i+1}: {chunk.content[:300]}..." if len(chunk.content) > 300 else f"\n内容 {i+1}: {chunk.content}"
            
            prompt += f"""
            
            生成答案:
            {query_result.answer}
            
            请根据生成答案与检索内容的忠实程度打分:
            - 0.0: 完全不忠实，答案中的关键信息在检索内容中找不到
            - 0.3: 低度忠实，答案中大部分信息在检索内容中找不到
            - 0.5: 部分忠实，答案中约一半信息能在检索内容中找到
            - 0.7: 较为忠实，答案中大部分信息能在检索内容中找到
            - 1.0: 完全忠实，答案中的所有信息都能在检索内容中找到
            
            仅返回一个0.0到1.0之间的浮点数作为忠实度评分。
            """
            
            # 调用LLM
            response = await self.llm_service.chat(prompt)
            
            # 解析分数
            content = response.content.strip()
            
            # 提取数字
            import re
            score_match = re.search(r'(\d+\.\d+|\d+)', content)
            if score_match:
                score = float(score_match.group(1))
                
                # 确保分数在有效范围内
                score = max(0.0, min(1.0, score))
                
                return score
            
            # 如果无法提取数字，返回默认值
            logger.warning(f"无法从LLM响应中提取忠实度分数: {content}")
            return 0.5
            
        except Exception as e:
            logger.error(f"计算忠实度分数失败: {str(e)}")
            return 0.0
    
    @property
    def name(self) -> str:
        return "faithfulness"
    
    @property
    def description(self) -> str:
        return "评估生成内容与检索内容的一致性"

class ContextPrecisionMetric(Metric):
    """上下文精确度指标 - 评估检索内容的精确性"""
    
    def __init__(self):
        pass
    
    async def calculate(self, query_result: QueryResult, **kwargs) -> float:
        """计算上下文精确度分数"""
        try:
            # 简单实现：基于检索块的得分
            if not query_result.chunks:
                return 0.0
                
            # 计算平均分数
            scores = [chunk.score or 0.0 for chunk in query_result.chunks]
            if not scores:
                return 0.0
                
            # 正则化分数到0-1范围
            avg_score = sum(scores) / len(scores)
            
            # 假设评分是相似度，已经在0-1范围内
            # 如果分数超出范围，进行适当调整
            normalized_score = max(0.0, min(1.0, avg_score))
            
            return normalized_score
            
        except Exception as e:
            logger.error(f"计算上下文精确度分数失败: {str(e)}")
            return 0.0
    
    @property
    def name(self) -> str:
        return "context_precision"
    
    @property
    def description(self) -> str:
        return "评估检索内容的精确性"