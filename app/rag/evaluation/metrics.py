"""
RAG评估指标 - 包含所有用于评估RAG系统的指标
"""
from typing import Dict, Any, List, Optional
import re
import math
import time
from app.rag.core.models import QueryResult
from app.rag.evaluation.base import Metric
from app.services.llm.base import BaseLLMService
from app.core.logging import get_logger

logger = get_logger(__name__)

class RelevanceMetric(Metric):
    """相关性评估指标 - 评估检索内容与查询的相关性"""

    def __init__(self, llm_service: BaseLLMService):
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

            # 添加检索内容（限制长度以控制令牌数）
            for i, chunk in enumerate(query_result.chunks):
                content_preview = chunk.content[:300] + "..." if len(chunk.content) > 300 else chunk.content
                prompt += f"\n内容 {i+1}: {content_preview}"

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

    def __init__(self, llm_service: BaseLLMService):
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

            # 添加检索内容（限制长度以控制令牌数）
            for i, chunk in enumerate(query_result.chunks):
                content_preview = chunk.content[:300] + "..." if len(chunk.content) > 300 else chunk.content
                prompt += f"\n内容 {i+1}: {content_preview}"

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

class AnswerCompletenessMetric(Metric):
    """回答完整性评估指标 - 评估生成回答的完整性"""

    def __init__(self, llm_service: BaseLLMService):
        self.llm_service = llm_service

    async def calculate(self, query_result: QueryResult, **kwargs) -> float:
        """计算完整性分数"""
        try:
            if not query_result.answer:
                return 0.0

            prompt = f"""
            请评估以下回答对用户问题的完整性。完整性指回答是否涵盖了问题的所有方面，并提供了足够的信息。
            
            用户问题: {query_result.query}
            
            回答:
            {query_result.answer}
            
            请根据回答的完整性打分:
            - 0.0: 完全不完整，没有回答问题或只回答了极小部分
            - 0.3: 低度完整，回答了问题的部分方面，但遗漏了多数重要信息
            - 0.5: 部分完整，回答了问题的约一半方面
            - 0.7: 较为完整，回答了问题的大部分方面，仅遗漏少量信息
            - 1.0: 高度完整，全面回答了问题的所有方面
            
            仅返回一个0.0到1.0之间的浮点数作为完整性评分。
            """

            # 调用LLM
            response = await self.llm_service.chat(prompt)

            # 解析分数
            content = response.content.strip()

            # 提取数字
            score_match = re.search(r'(\d+\.\d+|\d+)', content)
            if score_match:
                score = float(score_match.group(1))

                # 确保分数在有效范围内
                score = max(0.0, min(1.0, score))

                return score

            # 如果无法提取数字，返回默认值
            logger.warning(f"无法从LLM响应中提取完整性分数: {content}")
            return 0.5

        except Exception as e:
            logger.error(f"计算完整性分数失败: {str(e)}")
            return 0.0

    @property
    def name(self) -> str:
        return "completeness"

    @property
    def description(self) -> str:
        return "评估生成回答的完整性"

class ConciseMeaningfulnessMetric(Metric):
    """简洁有意义性评估指标 - 评估回答的简洁性和有意义性"""

    def __init__(self, llm_service: BaseLLMService):
        self.llm_service = llm_service

    async def calculate(self, query_result: QueryResult, **kwargs) -> float:
        """计算简洁有意义性分数"""
        try:
            if not query_result.answer:
                return 0.0

            prompt = f"""
            请评估以下回答的简洁有意义性。简洁有意义性指回答是否简明扼要且有实质性内容，避免冗余和无关信息。
            
            用户问题: {query_result.query}
            
            回答:
            {query_result.answer}
            
            请根据回答的简洁有意义性打分:
            - 0.0: 完全不简洁，过于冗长或包含大量无关信息
            - 0.3: 低度简洁，有较多冗余或无关内容
            - 0.5: 部分简洁，有一些冗余但也有有用信息
            - 0.7: 较为简洁，大部分内容简明有用，有少量冗余
            - 1.0: 高度简洁有意义，信息密度高，无冗余内容
            
            仅返回一个0.0到1.0之间的浮点数作为简洁有意义性评分。
            """

            # 调用LLM
            response = await self.llm_service.chat(prompt)

            # 解析分数
            content = response.content.strip()

            # 提取数字
            score_match = re.search(r'(\d+\.\d+|\d+)', content)
            if score_match:
                score = float(score_match.group(1))

                # 确保分数在有效范围内
                score = max(0.0, min(1.0, score))

                return score

            # 如果无法提取数字，返回默认值
            logger.warning(f"无法从LLM响应中提取简洁有意义性分数: {content}")
            return 0.5

        except Exception as e:
            logger.error(f"计算简洁有意义性分数失败: {str(e)}")
            return 0.0

    @property
    def name(self) -> str:
        return "conciseness"

    @property
    def description(self) -> str:
        return "评估回答的简洁性和有意义性"

class LatencyMetric(Metric):
    """延迟评估指标 - 评估系统响应时间"""

    def __init__(self, target_latency: float = 2000.0):
        """
        初始化延迟评估指标

        Args:
            target_latency: 目标延迟(毫秒)，用于归一化分数
        """
        self.target_latency = target_latency

    async def calculate(self, query_result: QueryResult, **kwargs) -> float:
        """计算延迟分数"""
        try:
            # 从元数据中获取总处理时间
            metrics = query_result.metadata.get("metrics", {})
            total_time = metrics.get("total_time", 0)

            # 转换为毫秒
            latency_ms = total_time * 1000

            # 计算分数 (反比例关系，延迟越低分数越高)
            # 使用指数衰减函数: score = exp(-latency/target)
            score = math.exp(-latency_ms / self.target_latency)

            # 确保分数在0-1范围内
            score = max(0.0, min(1.0, score))

            return score

        except Exception as e:
            logger.error(f"计算延迟分数失败: {str(e)}")
            return 0.0

    @property
    def name(self) -> str:
        return "latency"

    @property
    def description(self) -> str:
        return "评估系统响应时间"