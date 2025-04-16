"""
RAG评估器实现
"""
from typing import Dict, Any, List, Optional, Type
import time
from app.rag.core.models import QueryResult
from app.rag.evaluation.base import Metric, EvaluationResult
from app.rag.evaluation.metrics import RelevanceMetric, FaithfulnessMetric, ContextPrecisionMetric
from app.services.llm.base import BaseLLMService
from app.core.logging import get_logger
from datetime import datetime

logger = get_logger(__name__)

class RAGEvaluator:
    """RAG评估器"""
    
    def __init__(self, llm_service: BaseLLMService):
        """
        初始化RAG评估器
        
        Args:
            llm_service: LLM服务
        """
        self.llm_service = llm_service
        self.metrics: Dict[str, Metric] = {}
        
        # 注册默认指标
        self.register_default_metrics()
    
    def register_default_metrics(self):
        """注册默认评估指标"""
        self.register_metric(RelevanceMetric(self.llm_service))
        self.register_metric(FaithfulnessMetric(self.llm_service))
        self.register_metric(ContextPrecisionMetric())
    
    def register_metric(self, metric: Metric):
        """
        注册评估指标
        
        Args:
            metric: 评估指标实例
        """
        self.metrics[metric.name] = metric
        logger.info(f"已注册评估指标: {metric.name}")
    
    async def evaluate(
        self, 
        query_result: QueryResult,
        metrics: Optional[List[str]] = None
    ) -> EvaluationResult:
        """
        评估查询结果
        
        Args:
            query_result: 查询结果
            metrics: 要使用的指标名称列表，为None则使用所有已注册指标
            
        Returns:
            EvaluationResult: 评估结果
        """
        start_time = time.time()
        
        result = EvaluationResult()
        result.query_result = query_result
        
        # 使用指定指标或所有已注册指标
        metrics_to_use = metrics or list(self.metrics.keys())
        
        # 添加基本信息
        result.details["query"] = query_result.query
        result.details["answer_length"] = len(query_result.answer)
        result.details["chunks_count"] = len(query_result.chunks)
        result.details["evaluation_time"] = datetime.now().isoformat()
        
        # 计算每个指标
        for metric_name in metrics_to_use:
            if metric_name not in self.metrics:
                logger.warning(f"未注册的评估指标: {metric_name}")
                continue
                
            metric = self.metrics[metric_name]
            
            try:
                # 计算指标得分
                score = await metric.calculate(query_result)
                
                # 添加到结果
                result.add_metric(metric_name, score)
                
                logger.debug(f"已计算指标 {metric_name}: {score}")
                
            except Exception as e:
                logger.error(f"计算指标 {metric_name} 失败: {str(e)}")
        
        # 添加评估元数据
        evaluation_time = time.time() - start_time
        result.details["processing_time_ms"] = round(evaluation_time * 1000, 2)
        
        return result