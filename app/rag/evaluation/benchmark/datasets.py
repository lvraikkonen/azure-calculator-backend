# app/rag/evaluation/benchmark/datasets.py
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import json
from pathlib import Path
import csv
import random


class BenchmarkQuery(BaseModel):
    """基准测试查询"""
    id: str
    query: str
    expected_answer: Optional[str] = None
    expected_documents: Optional[List[str]] = None
    category: Optional[str] = None
    difficulty: Optional[str] = None


class BenchmarkDataset:
    """基准测试数据集"""

    def __init__(self, name: str):
        """初始化基准测试数据集"""
        self.name = name
        self.queries: List[BenchmarkQuery] = []

    def add_query(self, query: BenchmarkQuery):
        """添加查询"""
        self.queries.append(query)

    def load_from_json(self, file_path: Path):
        """从JSON文件加载"""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data.get("queries", []):
            self.queries.append(BenchmarkQuery(**item))

    def load_from_csv(self, file_path: Path):
        """从CSV文件加载"""
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.add_query(BenchmarkQuery(**row))

    def sample(self, n: int) -> List[BenchmarkQuery]:
        """随机抽样n个查询"""
        if n >= len(self.queries):
            return self.queries
        return random.sample(self.queries, n)

    def filter(self, **kwargs) -> List[BenchmarkQuery]:
        """根据条件筛选查询"""
        result = []
        for query in self.queries:
            match = True
            for key, value in kwargs.items():
                if hasattr(query, key) and getattr(query, key) != value:
                    match = False
                    break
            if match:
                result.append(query)
        return result

    @staticmethod
    def create_azure_test_dataset():
        """创建Azure测试数据集"""
        dataset = BenchmarkDataset("azure_test")

        # 添加不同类型的测试查询

        # 定价查询
        dataset.add_query(BenchmarkQuery(
            id="p1",
            query="Azure虚拟机的定价是什么?",
            category="pricing"
        ))

        # 比较查询
        dataset.add_query(BenchmarkQuery(
            id="c1",
            query="Azure SQL Database和Cosmos DB有什么区别?",
            category="comparison"
        ))

        # 技术查询
        dataset.add_query(BenchmarkQuery(
            id="t1",
            query="如何配置Azure应用服务的自动扩展?",
            category="technical"
        ))

        # 添加更多查询...

        return dataset