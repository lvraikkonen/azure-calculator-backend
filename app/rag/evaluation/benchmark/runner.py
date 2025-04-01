# app/rag/evaluation/benchmark/runner.py
from typing import List, Dict, Any, Optional, Union
import time
import asyncio
import pandas as pd
from datetime import datetime
from pathlib import Path
import json

import random

from app.rag.evaluation.benchmark.datasets import BenchmarkDataset, BenchmarkQuery
from app.rag.services.hybrid_rag_service import HybridRAGService
from app.rag.evaluation.evaluator import RAGEvaluator
from app.rag.core.models import QueryResult
from app.core.logging import get_logger

logger = get_logger(__name__)


class BenchmarkResult:
    """基准测试结果"""

    def __init__(self, dataset_name: str):
        self.dataset_name = dataset_name
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results: List[Dict[str, Any]] = []
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        self.config_info: Dict[str, Any] = {}

    def add_result(self, query: BenchmarkQuery, query_result: QueryResult, eval_result: Dict[str, Any]):
        """添加查询结果"""
        self.results.append({
            "query_id": query.id,
            "query": query.query,
            "category": query.category,
            "answer": query_result.answer,
            "metrics": eval_result.get("metrics", {}),
            "overall_score": eval_result.get("overall_score", 0),
            "processing_time_ms": eval_result.get("details", {}).get("processing_time_ms", 0)
        })

    def complete(self):
        """完成测试"""
        self.end_time = datetime.now()

    def to_dataframe(self) -> pd.DataFrame:
        """转换为DataFrame"""
        # 展平结果数据
        flat_results = []
        for result in self.results:
            flat_result = {
                "query_id": result["query_id"],
                "query": result["query"],
                "category": result["category"],
                "answer": result["answer"],
                "overall_score": result["overall_score"],
                "processing_time_ms": result["processing_time_ms"]
            }

            # 添加每个指标的分数
            for metric, score in result["metrics"].items():
                flat_result[f"metric_{metric}"] = score

            flat_results.append(flat_result)

        return pd.DataFrame(flat_results)

    def save(self, output_dir: Path):
        """保存结果"""
        output_dir.mkdir(exist_ok=True, parents=True)

        # 保存为JSON
        result_json = {
            "dataset": self.dataset_name,
            "run_id": self.run_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "config": self.config_info,
            "results": self.results
        }

        json_path = output_dir / f"benchmark_{self.run_id}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result_json, f, ensure_ascii=False, indent=2)

        # 保存为CSV
        csv_path = output_dir / f"benchmark_{self.run_id}.csv"
        self.to_dataframe().to_csv(csv_path, index=False)

        logger.info(f"基准测试结果已保存: {json_path}")
        return json_path


class BenchmarkRunner:
    """基准测试运行器"""

    def __init__(
            self,
            rag_service: HybridRAGService,
            evaluator: RAGEvaluator,
            output_dir: Optional[Path] = None
    ):
        """初始化基准测试运行器"""
        self.rag_service = rag_service
        self.evaluator = evaluator
        self.output_dir = output_dir or Path("./benchmark_results")

    async def run_benchmark(
            self,
            dataset: Union[BenchmarkDataset, List[BenchmarkQuery]],
            metrics: Optional[List[str]] = None,
            sample_size: Optional[int] = None,
            category_filter: Optional[str] = None
    ) -> BenchmarkResult:
        """运行基准测试"""
        # 准备查询列表
        if isinstance(dataset, BenchmarkDataset):
            queries = dataset.queries
            dataset_name = dataset.name
        else:
            queries = dataset
            dataset_name = "custom_dataset"

        # 应用过滤器
        if category_filter:
            queries = [q for q in queries if q.category == category_filter]

        # 应用采样
        if sample_size and sample_size < len(queries):
            queries = random.sample(queries, sample_size)

        # 创建结果对象
        result = BenchmarkResult(dataset_name)

        # 添加配置信息
        result.config_info = {
            "mode": self.rag_service.config.mode,
            "retriever_type": self.rag_service.config.retriever.type,
            "top_k": self.rag_service.config.retriever.top_k,
            "metrics": metrics or list(self.evaluator.metrics.keys())
        }

        # 运行每个查询
        total = len(queries)
        logger.info(f"开始基准测试，共 {total} 个查询")

        for i, query in enumerate(queries):
            try:
                logger.info(f"查询 {i + 1}/{total}: {query.query}")

                # 执行查询
                query_result = await self.rag_service.query(query.query)

                # 评估结果
                eval_result = await self.evaluator.evaluate(query_result, metrics)

                # 添加结果
                result.add_result(query, query_result, eval_result.to_dict())

            except Exception as e:
                logger.error(f"处理查询失败: {query.query}, 错误: {str(e)}")

        # 完成测试
        result.complete()

        # 保存结果
        if self.output_dir:
            result.save(self.output_dir)

        return result