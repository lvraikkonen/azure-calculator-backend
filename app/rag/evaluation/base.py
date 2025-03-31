"""
RAG评估基类和接口
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from app.rag.core.models import QueryResult

class Metric(ABC):
    """评估指标基类"""
    
    @abstractmethod
    async def calculate(self, query_result: QueryResult, **kwargs) -> float:
        """
        计算评估指标
        
        Args:
            query_result: 查询结果
            **kwargs: 附加参数
            
        Returns:
            float: 指标得分 (0.0-1.0)
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """指标名称"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """指标描述"""
        pass

class EvaluationResult:
    """评估结果类"""
    
    def __init__(self):
        self.metrics: Dict[str, float] = {}
        self.details: Dict[str, Any] = {}
        self.query_result: Optional[QueryResult] = None
        
    def add_metric(self, metric_name: str, score: float, details: Any = None):
        """
        添加指标结果
        
        Args:
            metric_name: 指标名称
            score: 指标得分
            details: 详细信息
        """
        self.metrics[metric_name] = score
        
        if details:
            if "metrics" not in self.details:
                self.details["metrics"] = {}
            self.details["metrics"][metric_name] = details
    
    @property
    def overall_score(self) -> float:
        """
        计算总体评分
        
        Returns:
            float: 总体评分 (0.0-1.0)
        """
        if not self.metrics:
            return 0.0
        return sum(self.metrics.values()) / len(self.metrics)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        
        Returns:
            Dict[str, Any]: 字典表示
        """
        return {
            "overall_score": self.overall_score,
            "metrics": self.metrics,
            "details": self.details
        }