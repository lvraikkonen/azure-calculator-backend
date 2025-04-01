# app/rag/evaluation/benchmark/analysis.py
from typing import List, Dict, Any, Optional, Union
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import json
import numpy as np


class BenchmarkAnalyzer:
    """基准测试分析器"""

    def __init__(self, results_df: pd.DataFrame):
        """初始化基准测试分析器"""
        self.df = results_df

    @classmethod
    def from_file(cls, file_path: Path):
        """从文件加载"""
        if file_path.suffix.lower() == ".csv":
            return cls(pd.read_csv(file_path))
        elif file_path.suffix.lower() == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 转换为DataFrame
            flat_results = []
            for result in data.get("results", []):
                flat_result = {
                    "query_id": result.get("query_id"),
                    "query": result.get("query"),
                    "category": result.get("category"),
                    "answer": result.get("answer"),
                    "overall_score": result.get("overall_score"),
                    "processing_time_ms": result.get("processing_time_ms")
                }

                # 添加每个指标的分数
                for metric, score in result.get("metrics", {}).items():
                    flat_result[f"metric_{metric}"] = score

                flat_results.append(flat_result)

            return cls(pd.DataFrame(flat_results))

    def summary_stats(self) -> pd.DataFrame:
        """汇总统计"""
        # 提取指标列
        metric_cols = [col for col in self.df.columns if col.startswith("metric_")]

        # 计算基本统计量
        stats = self.df[metric_cols + ["overall_score"]].describe()

        # 按类别统计
        if "category" in self.df.columns:
            category_stats = self.df.groupby("category")[metric_cols + ["overall_score"]].mean()
            stats = pd.concat([stats, category_stats], axis=0)

        return stats

    def plot_metrics_distribution(self, output_path: Optional[Path] = None):
        """绘制指标分布"""
        # 提取指标列
        metric_cols = [col for col in self.df.columns if col.startswith("metric_")]

        if not metric_cols:
            return

        # 设置图表
        fig, axes = plt.subplots(1, len(metric_cols), figsize=(len(metric_cols) * 5, 6))
        if len(metric_cols) == 1:
            axes = [axes]

        # 绘制每个指标的分布
        for i, col in enumerate(metric_cols):
            metric_name = col.replace("metric_", "")
            sns.histplot(self.df[col], ax=axes[i], kde=True)
            axes[i].set_title(f"{metric_name} 分布")
            axes[i].set_xlabel("分数")
            axes[i].set_ylabel("频率")

        plt.tight_layout()

        # 保存或显示
        if output_path:
            plt.savefig(output_path)
        else:
            plt.show()

        plt.close()

    def plot_category_comparison(self, output_path: Optional[Path] = None):
        """绘制类别比较"""
        if "category" not in self.df.columns:
            return

        # 提取指标列
        metric_cols = [col for col in self.df.columns if col.startswith("metric_")]

        if not metric_cols:
            return

        # 按类别分组计算均值
        category_means = self.df.groupby("category")[metric_cols].mean()

        # 绘制热图
        plt.figure(figsize=(10, 8))
        sns.heatmap(category_means, annot=True, cmap="YlGnBu", fmt=".3f")
        plt.title("各类别的指标均值比较")
        plt.tight_layout()

        # 保存或显示
        if output_path:
            plt.savefig(output_path)
        else:
            plt.show()

        plt.close()

        # 绘制雷达图
        categories = category_means.index.tolist()
        metrics = [col.replace("metric_", "") for col in metric_cols]

        # 设置雷达图
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))

        # 计算角度
        angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
        angles += angles[:1]  # 闭合图形

        # 绘制每个类别
        for category in categories:
            values = category_means.loc[category].tolist()
            values += values[:1]  # 闭合图形
            ax.plot(angles, values, linewidth=2, label=category)
            ax.fill(angles, values, alpha=0.1)

        # 设置刻度和标签
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(metrics)
        ax.set_title("各类别性能雷达图")
        ax.legend(loc="upper right")

        # 保存或显示
        if output_path:
            output_path = output_path.with_stem(f"{output_path.stem}_radar")
            plt.savefig(output_path)
        else:
            plt.show()

        plt.close()

    def export_report(self, output_dir: Path):
        """导出完整报告"""
        output_dir.mkdir(exist_ok=True, parents=True)

        # 保存统计摘要
        stats = self.summary_stats()
        stats.to_csv(output_dir / "summary_stats.csv")

        # 绘制图表
        self.plot_metrics_distribution(output_dir / "metrics_distribution.png")
        self.plot_category_comparison(output_dir / "category_comparison.png")

        # 保存最优和最差查询示例
        if "overall_score" in self.df.columns:
            best_examples = self.df.nlargest(3, "overall_score")[["query", "answer", "overall_score"]]
            worst_examples = self.df.nsmallest(3, "overall_score")[["query", "answer", "overall_score"]]

            best_examples.to_csv(output_dir / "best_examples.csv", index=False)
            worst_examples.to_csv(output_dir / "worst_examples.csv", index=False)

        # 创建HTML报告
        html = f"""
        <html>
        <head>
            <title>RAG基准测试报告</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2, h3 {{ color: #2c3e50; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                img {{ max-width: 100%; }}
                .section {{ margin-bottom: 30px; }}
            </style>
        </head>
        <body>
            <h1>RAG基准测试报告</h1>
            <div class="section">
                <h2>测试概述</h2>
                <p>总查询数: {len(self.df)}</p>
                <p>平均总体得分: {self.df["overall_score"].mean():.4f}</p>
                <p>平均处理时间: {self.df["processing_time_ms"].mean():.2f} ms</p>
            </div>

            <div class="section">
                <h2>指标分布</h2>
                <img src="metrics_distribution.png" alt="指标分布">
            </div>

            <div class="section">
                <h2>类别比较</h2>
                <img src="category_comparison.png" alt="类别比较">
                <img src="category_comparison_radar.png" alt="类别雷达图">
            </div>

            <div class="section">
                <h2>优秀示例</h2>
                <table>
                    <tr>
                        <th>查询</th>
                        <th>回答</th>
                        <th>分数</th>
                    </tr>
                    {"".join(f"<tr><td>{row['query']}</td><td>{row['answer']}</td><td>{row['overall_score']:.4f}</td></tr>" for _, row in best_examples.iterrows())}
                </table>
            </div>

            <div class="section">
                <h2>待改进示例</h2>
                <table>
                    <tr>
                        <th>查询</th>
                        <th>回答</th>
                        <th>分数</th>
                    </tr>
                    {"".join(f"<tr><td>{row['query']}</td><td>{row['answer']}</td><td>{row['overall_score']:.4f}</td></tr>" for _, row in worst_examples.iterrows())}
                </table>
            </div>
        </body>
        </html>
        """

        with open(output_dir / "report.html", "w", encoding="utf-8") as f:
            f.write(html)

        return output_dir / "report.html"