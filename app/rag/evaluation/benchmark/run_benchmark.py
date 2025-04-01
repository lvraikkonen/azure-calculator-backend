# app/rag/evaluation/benchmark/run_benchmark.py
import asyncio
import argparse
from pathlib import Path
import logging
import datetime
from typing import List, Optional

from app.services.llm_service import LLMService
from app.rag.services.rag_factory import create_rag_service, get_evaluator
from app.rag.evaluation.benchmark.datasets import BenchmarkDataset
from app.rag.evaluation.benchmark.runner import BenchmarkRunner
from app.rag.evaluation.benchmark.analysis import BenchmarkAnalyzer

from app.rag.evaluation.metrics import (
    RelevanceMetric,
    FaithfulnessMetric,
    ContextPrecisionMetric,
    AnswerCompletenessMetric,
    ConciseMeaningfulnessMetric,
    LatencyMetric
)
from app.core.logging import get_logger

logger = get_logger(__name__)


async def main():
    """运行RAG基准测试"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="运行RAG基准测试")
    parser.add_argument("--dataset", type=str, default="azure_test", help="测试数据集名称或文件路径")
    parser.add_argument("--output-dir", type=str, default="./benchmark_results", help="输出目录")
    parser.add_argument("--sample-size", type=int, default=None, help="采样大小")
    parser.add_argument("--category", type=str, default=None, help="分类过滤器")
    parser.add_argument("--metrics", type=str, nargs="*", help="要使用的指标列表，默认全部使用")
    parser.add_argument("--run-name", type=str, default=None, help="测试运行名称")
    args = parser.parse_args()

    # 设置运行名称
    run_name = args.run_name or f"benchmark-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"

    # 创建LLM服务
    llm_service = LLMService()

    # 创建RAG服务
    rag_service = await create_rag_service(llm_service)

    # 创建评估器
    evaluator = await get_evaluator(llm_service, force_new=True)

    # 清除已注册的指标（确保不会重复）
    evaluator.metrics.clear()

    # 注册所有评估指标
    register_all_metrics(evaluator, llm_service)

    # 根据命令行参数筛选指标
    if args.metrics:
        available_metrics = list(evaluator.metrics.keys())
        metrics_to_use = [m for m in args.metrics if m in available_metrics]

        if not metrics_to_use:
            logger.warning(f"指定的指标无效，将使用所有可用指标：{available_metrics}")
        else:
            logger.info(f"将使用以下指标：{metrics_to_use}")
    else:
        metrics_to_use = None  # 使用所有指标

    # 创建输出目录
    output_dir = Path(args.output_dir) / run_name
    output_dir.mkdir(exist_ok=True, parents=True)

    # 加载数据集
    dataset = load_dataset(args.dataset)

    # 创建基准测试运行器
    runner = BenchmarkRunner(rag_service, evaluator, output_dir)

    # 运行基准测试
    result = await runner.run_benchmark(
        dataset,
        metrics=metrics_to_use,
        sample_size=args.sample_size,
        category_filter=args.category
    )

    # 分析结果
    analyzer = BenchmarkAnalyzer(result.to_dataframe())
    report_path = analyzer.export_report(output_dir)

    logger.info(f"基准测试完成，报告已生成: {report_path}")
    print(f"\n基准测试报告: {report_path}")

    # 输出简要结果摘要
    summary = analyzer.summary_stats()
    print("\n===== 测试结果摘要 =====")
    print(f"测试查询总数: {len(result.results)}")
    print(f"平均总体得分: {summary.loc['mean', 'overall_score']:.4f}")
    if 'metric_latency' in summary.columns:
        print(f"平均延迟分数: {summary.loc['mean', 'metric_latency']:.4f}")

    # 如果有分类，显示分类信息
    if args.category:
        print(f"\n分类 '{args.category}' 的结果:")
    elif 'category' in analyzer.df.columns:
        categories = analyzer.df['category'].unique()
        print("\n各类别平均分数:")
        for category in categories:
            cat_score = analyzer.df[analyzer.df['category'] == category]['overall_score'].mean()
            print(f"  {category}: {cat_score:.4f}")


def register_all_metrics(evaluator, llm_service: LLMService):
    """注册所有评估指标"""
    # 基础质量指标
    evaluator.register_metric(RelevanceMetric(llm_service))
    evaluator.register_metric(FaithfulnessMetric(llm_service))
    evaluator.register_metric(ContextPrecisionMetric())

    # 高级质量指标
    evaluator.register_metric(AnswerCompletenessMetric(llm_service))
    evaluator.register_metric(ConciseMeaningfulnessMetric(llm_service))

    # 性能指标
    evaluator.register_metric(LatencyMetric())

    logger.info(f"已注册 {len(evaluator.metrics)} 个评估指标: {list(evaluator.metrics.keys())}")


def load_dataset(dataset_spec: str) -> BenchmarkDataset:
    """加载数据集"""
    if dataset_spec == "azure_test":
        logger.info("使用内置Azure测试数据集")
        return BenchmarkDataset.create_azure_test_dataset()
    else:
        # 从文件加载
        dataset_path = Path(dataset_spec)

        if not dataset_path.exists():
            raise ValueError(f"数据集文件不存在: {dataset_path}")

        logger.info(f"从文件加载数据集: {dataset_path}")
        dataset = BenchmarkDataset(dataset_path.stem)

        if dataset_path.suffix.lower() == ".json":
            dataset.load_from_json(dataset_path)
        elif dataset_path.suffix.lower() == ".csv":
            dataset.load_from_csv(dataset_path)
        else:
            raise ValueError(f"不支持的数据集格式: {dataset_path.suffix}")

        return dataset


if __name__ == "__main__":
    asyncio.run(main())