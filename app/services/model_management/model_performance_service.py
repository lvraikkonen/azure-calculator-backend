from datetime import datetime, timezone
import uuid
import statistics
import asyncio
from time import perf_counter_ns
from typing import Dict, Any, List, Optional, Tuple, Union
from functools import lru_cache
from contextlib import asynccontextmanager
import json
from enum import Enum

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.logging import get_logger
from app.models.model_performance_test import ModelPerformanceTest
from app.models.model_configuration import ModelConfiguration
from app.services.llm.factory import LLMServiceFactory
from app.services.llm.base import BaseLLMService, ModelType
from app.schemas.model_management.performance import (
    TestCreate, TestResponse, TestDetailResponse,
    SpeedTestRequest, LatencyTestRequest, BatchTestRequest, BatchTestResponse,
    TestComparisonRequest, TestComparisonResponse
)
from app.utils.token_counter import count_tokens

logger = get_logger(__name__)


class TestStatus(Enum):
    """测试状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class TestProgress:
    """测试进度跟踪"""

    def __init__(self, test_id: uuid.UUID, total_rounds: int):
        self.test_id = test_id
        self.total_rounds = total_rounds
        self.completed_rounds = 0
        self.failed_rounds = 0
        self.status = TestStatus.PENDING
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.current_round_start: Optional[datetime] = None
        self.error_details: List[Dict[str, Any]] = []

    def start_test(self):
        """开始测试"""
        self.status = TestStatus.RUNNING
        self.start_time = datetime.now(timezone.utc)

    def start_round(self, round_num: int):
        """开始新一轮测试"""
        self.current_round_start = datetime.now(timezone.utc)
        logger.debug(f"测试 {self.test_id} 开始第 {round_num} 轮")

    def complete_round(self, round_num: int, success: bool = True, error: Optional[str] = None):
        """完成一轮测试"""
        if success:
            self.completed_rounds += 1
        else:
            self.failed_rounds += 1
            if error:
                self.error_details.append({
                    "round": round_num,
                    "error": error,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

        round_duration = None
        if self.current_round_start:
            round_duration = (datetime.now(timezone.utc) - self.current_round_start).total_seconds()

        logger.debug(f"测试 {self.test_id} 第 {round_num} 轮完成，耗时: {round_duration}s")

    def complete_test(self, success: bool = True):
        """完成测试"""
        self.end_time = datetime.now(timezone.utc)
        if success and self.failed_rounds == 0:
            self.status = TestStatus.COMPLETED
        else:
            self.status = TestStatus.FAILED

        total_duration = None
        if self.start_time:
            total_duration = (self.end_time - self.start_time).total_seconds()

        logger.info(f"测试 {self.test_id} 完成，状态: {self.status.value}, 总耗时: {total_duration}s")

    def get_progress_percentage(self) -> float:
        """获取进度百分比"""
        if self.total_rounds == 0:
            return 0.0
        return (self.completed_rounds + self.failed_rounds) / self.total_rounds * 100

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "test_id": str(self.test_id),
            "status": self.status.value,
            "total_rounds": self.total_rounds,
            "completed_rounds": self.completed_rounds,
            "failed_rounds": self.failed_rounds,
            "progress_percentage": self.get_progress_percentage(),
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "error_count": len(self.error_details),
            "latest_errors": self.error_details[-3:] if self.error_details else []
        }


class PerformanceMetrics:
    """性能指标收集器"""

    def __init__(self):
        self.metrics: Dict[str, List[float]] = {
            "test_duration": [],
            "round_duration": [],
            "api_call_duration": [],
            "token_generation_rate": [],
            "error_rate": [],
            "cache_hit_rate": []
        }
        self.counters: Dict[str, int] = {
            "total_tests": 0,
            "successful_tests": 0,
            "failed_tests": 0,
            "total_rounds": 0,
            "successful_rounds": 0,
            "failed_rounds": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }

    def record_metric(self, metric_name: str, value: float):
        """记录指标值"""
        if metric_name in self.metrics:
            self.metrics[metric_name].append(value)

    def increment_counter(self, counter_name: str, value: int = 1):
        """增加计数器"""
        if counter_name in self.counters:
            self.counters[counter_name] += value

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {}

        # 计算指标统计
        for metric_name, values in self.metrics.items():
            if values:
                stats[metric_name] = {
                    "count": len(values),
                    "avg": statistics.mean(values),
                    "min": min(values),
                    "max": max(values),
                    "std": statistics.stdev(values) if len(values) > 1 else 0
                }
            else:
                stats[metric_name] = {"count": 0}

        # 添加计数器
        stats["counters"] = self.counters.copy()

        # 计算派生指标
        if self.counters["total_tests"] > 0:
            stats["test_success_rate"] = self.counters["successful_tests"] / self.counters["total_tests"] * 100

        if self.counters["total_rounds"] > 0:
            stats["round_success_rate"] = self.counters["successful_rounds"] / self.counters["total_rounds"] * 100

        cache_total = self.counters["cache_hits"] + self.counters["cache_misses"]
        if cache_total > 0:
            stats["cache_hit_rate"] = self.counters["cache_hits"] / cache_total * 100

        return stats


class PerformanceTestConfig:
    """性能测试配置常量"""

    # 测试间隔配置
    DEFAULT_SLEEP_INTERVAL = 0.5  # 测试轮次间隔（秒）
    BATCH_SLEEP_INTERVAL = 1.0    # 批量测试间隔（秒）

    # 测试限制
    MAX_ROUNDS = 50               # 最大测试轮数
    MAX_BATCH_SIZE = 10           # 最大批量测试数量
    DEFAULT_TIMEOUT = 300         # 默认超时时间（秒）

    # 缓存配置
    MODEL_CONFIG_CACHE_SIZE = 100 # 模型配置缓存大小
    CACHE_TTL = 3600             # 缓存生存时间（秒）

    # 重试配置
    MAX_RETRIES = 3              # 最大重试次数
    RETRY_DELAY = 2              # 重试延迟（秒）

    # 并发配置
    MAX_CONCURRENT_TESTS = 5     # 最大并发测试数

    # 默认测试提示词
    DEFAULT_PROMPTS = [
        "请简要介绍Azure云服务的主要优势。",
        "你好",
        "今天天气如何",
        "Azure是什么",
        "1+1等于几",
        "解释量子计算"
    ]


class ModelPerformanceService:
    """模型性能测试服务"""

    def __init__(self, db: AsyncSession):
        """初始化性能测试服务

        Args:
            db: 数据库会话
        """
        self.db = db
        self._model_config_cache: Dict[str, ModelConfiguration] = {}
        self._test_progress: Dict[str, TestProgress] = {}
        self._performance_metrics = PerformanceMetrics()
        self._active_tests: Dict[str, asyncio.Task] = {}

    async def _get_model_config(self, model_id: uuid.UUID) -> Optional[ModelConfiguration]:
        """获取模型配置（带缓存）

        Args:
            model_id: 模型ID

        Returns:
            Optional[ModelConfiguration]: 模型配置，如果不存在则返回None
        """
        cache_key = str(model_id)

        # 检查缓存
        if cache_key in self._model_config_cache:
            self._performance_metrics.increment_counter("cache_hits")
            return self._model_config_cache[cache_key]

        self._performance_metrics.increment_counter("cache_misses")

        # 从数据库查询
        result = await self.db.execute(
            select(ModelConfiguration).where(ModelConfiguration.id == model_id)
        )
        model_config = result.scalar_one_or_none()

        # 缓存结果
        if model_config:
            self._model_config_cache[cache_key] = model_config

        return model_config

    def _clear_model_config_cache(self, model_id: Optional[uuid.UUID] = None):
        """清除模型配置缓存

        Args:
            model_id: 要清除的特定模型ID，如果为None则清除所有缓存
        """
        if model_id:
            cache_key = str(model_id)
            self._model_config_cache.pop(cache_key, None)
        else:
            self._model_config_cache.clear()

    async def _get_model_type_enum(self, model_config: ModelConfiguration) -> Optional[ModelType]:
        """将字符串模型类型转换为枚举

        Args:
            model_config: 模型配置

        Returns:
            Optional[ModelType]: 模型类型枚举，如果转换失败则返回None
        """
        try:
            return ModelType(model_config.model_type)
        except ValueError:
            logger.warning(f"未知模型类型: {model_config.model_type}")
            return None

    def get_test_progress(self, test_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """获取测试进度

        Args:
            test_id: 测试ID

        Returns:
            Optional[Dict[str, Any]]: 测试进度信息
        """
        progress = self._test_progress.get(str(test_id))
        return progress.to_dict() if progress else None

    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标统计

        Returns:
            Dict[str, Any]: 性能指标统计信息
        """
        return self._performance_metrics.get_statistics()

    async def cancel_test(self, test_id: uuid.UUID) -> bool:
        """取消正在运行的测试

        Args:
            test_id: 测试ID

        Returns:
            bool: 是否成功取消
        """
        test_key = str(test_id)

        # 取消任务
        if test_key in self._active_tests:
            task = self._active_tests[test_key]
            if not task.done():
                task.cancel()

        # 更新进度状态
        if test_key in self._test_progress:
            progress = self._test_progress[test_key]
            progress.status = TestStatus.CANCELLED
            progress.complete_test(success=False)

        logger.info(f"测试 {test_id} 已取消")
        return True

    @retry(
        stop=stop_after_attempt(PerformanceTestConfig.MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=PerformanceTestConfig.RETRY_DELAY, max=10),
        retry=retry_if_exception_type((asyncio.TimeoutError, ConnectionError, Exception))
    )
    async def _execute_single_test_round_with_retry(
            self,
            llm_service: BaseLLMService,
            prompt: str,
            model_config: ModelConfiguration,
            round_num: int,
            timeout: float = PerformanceTestConfig.DEFAULT_TIMEOUT
    ) -> Dict[str, Any]:
        """执行单轮测试（带重试和超时）

        Args:
            llm_service: LLM服务实例
            prompt: 测试提示词
            model_config: 模型配置
            round_num: 轮次编号
            timeout: 超时时间（秒）

        Returns:
            Dict[str, Any]: 单轮测试结果
        """
        try:
            # 使用超时控制
            return await asyncio.wait_for(
                self._execute_single_test_round(llm_service, prompt, model_config, round_num),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"测试轮次 {round_num} 超时 ({timeout}s)")
            raise
        except Exception as e:
            logger.warning(f"测试轮次 {round_num} 失败，将重试: {str(e)}")
            raise

    async def _execute_single_test_round(
            self,
            llm_service: BaseLLMService,
            prompt: str,
            model_config: ModelConfiguration,
            round_num: int
    ) -> Dict[str, Any]:
        """执行单轮测试

        Args:
            llm_service: LLM服务实例
            prompt: 测试提示词
            model_config: 模型配置
            round_num: 轮次编号

        Returns:
            Dict[str, Any]: 单轮测试结果
        """
        logger.info(f"执行测试第 {round_num} 轮")

        # 使用流式API精确获取首个token时间和token计数
        start_time = perf_counter_ns()
        first_token_received = False
        first_token_time = None
        content = ""

        async for chunk in llm_service.chat_stream(
                user_message=prompt,
                extra_context={"is_performance_test": True}
        ):
            # 记录首个token时间
            chunk_content = chunk.get("content", "")
            if not first_token_received and chunk_content and chunk_content.strip():
                current_time = perf_counter_ns()
                first_token_time = (current_time - start_time) / 1_000_000  # 纳秒转毫秒
                first_token_received = True
                logger.debug(f"接收到首个token: '{chunk_content}'")

            # 累积内容
            if chunk_content:
                content += chunk_content

        # 计算总响应时间
        end_time = perf_counter_ns()
        response_time = (end_time - start_time) / 1_000_000  # 纳秒转毫秒

        # 准确计算token数
        model_type = model_config.model_type if model_config else "unknown"
        model_name = model_config.model_name if model_config else "unknown"
        input_token_count = count_tokens(prompt, model_type, model_name)
        output_token_count = count_tokens(content, model_type, model_name)

        # 计算token生成速度 (tokens/sec)
        tokens_per_sec = 0
        if response_time > 0:
            tokens_per_sec = output_token_count / (response_time / 1000)  # 转换为秒

        # 计算成本（如果模型有价格信息）
        input_cost = 0
        output_cost = 0
        if model_config:
            input_cost = (input_token_count * model_config.input_price) / 1000000
            output_cost = (output_token_count * model_config.output_price) / 1000000

        return {
            "round": round_num,
            "response_time": response_time,
            "first_token_time": first_token_time,
            "input_tokens": input_token_count,
            "output_tokens": output_token_count,
            "tokens_per_second": tokens_per_sec,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "content_sample": content[:150] + "..." if len(content) > 150 else content
        }

    def _calculate_test_statistics(self, round_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算测试统计数据

        Args:
            round_results: 各轮测试结果

        Returns:
            Dict[str, Any]: 统计结果
        """
        if not round_results:
            return {}

        # 提取各项指标
        response_times = [r["response_time"] for r in round_results if r.get("response_time")]
        first_token_times = [r["first_token_time"] for r in round_results if r.get("first_token_time")]
        input_token_counts = [r["input_tokens"] for r in round_results if r.get("input_tokens")]
        output_token_counts = [r["output_tokens"] for r in round_results if r.get("output_tokens")]
        tokens_per_second_list = [r["tokens_per_second"] for r in round_results if r.get("tokens_per_second")]

        results = {}

        # 响应时间统计
        if response_times:
            results["avg_response_time"] = statistics.mean(response_times)
            results["min_response_time"] = min(response_times)
            results["max_response_time"] = max(response_times)
            if len(response_times) > 1:
                results["std_response_time"] = statistics.stdev(response_times)

        # 首token时间统计
        if first_token_times:
            results["avg_first_token_time"] = statistics.mean(first_token_times)
            results["min_first_token_time"] = min(first_token_times)
            results["max_first_token_time"] = max(first_token_times)

        # Token统计
        if output_token_counts:
            results["avg_output_tokens"] = statistics.mean(output_token_counts)
            results["total_output_tokens"] = sum(output_token_counts)

        if input_token_counts:
            results["avg_input_tokens"] = statistics.mean(input_token_counts)
            results["total_input_tokens"] = sum(input_token_counts)

        if tokens_per_second_list:
            results["avg_tokens_per_second"] = statistics.mean(tokens_per_second_list)

        return results

    async def create_test_record(self, test_data: TestCreate) -> ModelPerformanceTest:
        """创建新的测试记录

        Args:
            test_data: 测试数据

        Returns:
            ModelPerformanceTest: 创建的测试记录
        """
        test_record = ModelPerformanceTest(
            model_id=test_data.model_id,
            test_name=test_data.test_name,
            test_type=test_data.test_type,
            rounds=test_data.rounds,
            test_params=test_data.test_params,
            test_date=datetime.utcnow()
        )

        self.db.add(test_record)
        await self.db.commit()
        await self.db.refresh(test_record)

        logger.info(f"创建性能测试记录: ID {test_record.id}, 模型 {test_data.model_id}, 类型 {test_data.test_type}")
        return test_record

    async def get_test_by_id(self, test_id: uuid.UUID) -> Optional[ModelPerformanceTest]:
        """通过ID获取测试记录

        Args:
            test_id: 测试ID

        Returns:
            Optional[ModelPerformanceTest]: 测试记录，如果不存在则返回None
        """
        result = await self.db.execute(
            select(ModelPerformanceTest).where(ModelPerformanceTest.id == test_id)
        )
        return result.scalar_one_or_none()

    async def list_tests(
            self,
            model_id: Optional[uuid.UUID] = None,
            test_type: Optional[str] = None,
            limit: int = 100,
            offset: int = 0
    ) -> Tuple[List[ModelPerformanceTest], int]:
        """获取测试记录列表

        Args:
            model_id: 按模型ID筛选
            test_type: 按测试类型筛选
            limit: 分页限制
            offset: 分页偏移

        Returns:
            Tuple[List[ModelPerformanceTest], int]: 测试记录列表和总记录数
        """
        # 构建基础查询
        query = select(ModelPerformanceTest)
        count_query = select(func.count()).select_from(ModelPerformanceTest)

        # 应用筛选条件
        if model_id:
            query = query.where(ModelPerformanceTest.model_id == model_id)
            count_query = count_query.where(ModelPerformanceTest.model_id == model_id)

        if test_type:
            query = query.where(ModelPerformanceTest.test_type == test_type)
            count_query = count_query.where(ModelPerformanceTest.test_type == test_type)

        # 排序和分页
        query = query.order_by(ModelPerformanceTest.test_date.desc())
        query = query.limit(limit).offset(offset)

        # 执行查询
        result = await self.db.execute(query)
        count_result = await self.db.execute(count_query)

        # 返回结果和总数
        return result.scalars().all(), count_result.scalar_one()

    async def update_test_results(
            self,
            test_id: uuid.UUID,
            results: Dict[str, Any]
    ) -> Optional[ModelPerformanceTest]:
        """更新测试结果

        Args:
            test_id: 测试ID
            results: 测试结果数据

        Returns:
            Optional[ModelPerformanceTest]: 更新后的测试记录
        """
        test_record = await self.get_test_by_id(test_id)
        if not test_record:
            logger.warning(f"尝试更新不存在的测试记录: {test_id}")
            return None

        # 更新通用测试结果字段
        standard_fields = [
            "avg_response_time", "avg_first_token_time", "avg_throughput",
            "success_rate", "error_rate", "min_response_time", "max_response_time"
        ]

        for field in standard_fields:
            if field in results:
                setattr(test_record, field, results[field])

        # 更新token统计字段，新字段需要放入detailed_results
        token_fields = {
            "avg_input_tokens": "avg_input_tokens",
            "avg_output_tokens": "avg_output_tokens",
            "total_input_tokens": "total_input_tokens",
            "total_output_tokens": "total_output_tokens",
            "avg_tokens_per_second": "avg_throughput",
            "input_cost": "input_cost",
            "output_cost": "output_cost",
            "total_cost": "total_cost"
        }

        # 确保详细结果存在
        detailed_results = test_record.detailed_results or {}
        additional_results = {}

        # 将token统计数据存储到详细结果中
        for key, db_field in token_fields.items():
            if key in results:
                if hasattr(test_record, db_field):
                    setattr(test_record, db_field, results[key])
                else:
                    additional_results[key] = results[key]

        # 如果提供了详细结果，合并
        if "detailed_results" in results:
            detailed_results.update(results["detailed_results"])

        # 添加其他统计数据
        if additional_results:
            detailed_results["additional_stats"] = additional_results

        # 更新详细结果字段
        test_record.detailed_results = detailed_results

        # 更新时间戳
        test_record.test_date = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(test_record)

        logger.info(f"更新测试记录结果: ID {test_id}")
        return test_record

    async def run_standard_test(
            self,
            request: SpeedTestRequest,
            llm_factory: LLMServiceFactory
    ) -> TestResponse:
        """运行标准性能测试

        Args:
            request: 测试请求
            llm_factory: LLM服务工厂

        Returns:
            TestResponse: 测试结果
        """
        # 首先创建测试记录
        test_data = TestCreate(
            model_id=request.model_id,
            test_name=f"标准测试 - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            test_type=request.test_type,
            rounds=request.rounds,
            test_params={
                "prompt": request.prompt or PerformanceTestConfig.DEFAULT_PROMPTS[0],
                "timestamp": datetime.utcnow().isoformat()
            }
        )

        test_record = await self.create_test_record(test_data)

        try:
            # 获取模型配置
            model_config = await self._get_model_config(request.model_id)
            if not model_config:
                raise ValueError(f"未找到模型ID: {request.model_id}")

            # 获取模型类型枚举
            model_type = await self._get_model_type_enum(model_config)

            # 获取LLM服务
            llm_service = await llm_factory.get_service(
                model_type=model_type,
                model_name=model_config.model_name
            )

            # 执行测试
            test_results = await self._execute_standard_test(
                llm_service=llm_service,
                test_record=test_record,
                prompt=request.prompt or "请简要介绍Azure云服务的主要优势。",
                rounds=request.rounds
            )

            # 更新测试结果
            updated_record = await self.update_test_results(
                test_id=test_record.id,
                results=test_results
            )

            # 构建响应
            response = TestResponse(
                id=updated_record.id,
                model_id=updated_record.model_id,
                model_name=model_config.display_name if model_config else "未知模型",
                test_name=updated_record.test_name,
                test_type=updated_record.test_type,
                rounds=updated_record.rounds,
                avg_response_time=test_results.get("avg_response_time"),
                avg_first_token_time=test_results.get("avg_first_token_time"),
                avg_throughput=test_results.get("avg_tokens_per_second"),
                success_rate=test_results.get("success_rate"),
                error_rate=test_results.get("error_rate"),
                test_params=updated_record.test_params or {},
                test_date=updated_record.test_date,
                tested_by=updated_record.tested_by
            )

            # 添加扩展属性 - 如果使用TestDetailResponse
            if isinstance(response, TestDetailResponse):
                response.input_tokens = test_results.get("avg_input_tokens")
                response.output_tokens = test_results.get("avg_output_tokens")
                response.tokens_per_second = test_results.get("avg_tokens_per_second")
                response.input_cost = test_results.get("input_cost")
                response.output_cost = test_results.get("output_cost")
                response.total_cost = test_results.get("total_cost")
                response.detailed_results = test_results.get("detailed_results")

            return response

        except Exception as e:
            # 记录错误并更新测试状态
            logger.error(f"执行标准测试时出错: {str(e)}", exc_info=True)

            # 更新测试记录状态为失败
            await self.update_test_results(
                test_id=test_record.id,
                results={
                    "success_rate": 0,
                    "error_rate": 100,
                    "detailed_results": {
                        "error": str(e),
                        "status": "failed",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            )

            # 返回测试失败响应
            return TestResponse(
                id=test_record.id,
                model_id=request.model_id,
                model_name="未知模型",
                test_name=test_record.test_name,
                test_type=request.test_type,
                rounds=request.rounds,
                avg_response_time=None,
                avg_first_token_time=None,
                avg_throughput=None,
                success_rate=0,
                error_rate=100,
                test_params=test_record.test_params or {},
                test_date=test_record.test_date,
                tested_by=None
            )

    async def _execute_standard_test(
            self,
            llm_service: BaseLLMService,
            test_record: ModelPerformanceTest,
            prompt: str,
            rounds: int
    ) -> Dict[str, Any]:
        """执行标准测试逻辑

        Args:
            llm_service: LLM服务实例
            test_record: 测试记录
            prompt: 测试提示词
            rounds: 测试轮数

        Returns:
            Dict[str, Any]: 测试结果数据
        """
        test_start_time = perf_counter_ns()

        # 创建进度跟踪
        progress = TestProgress(test_record.id, rounds)
        self._test_progress[str(test_record.id)] = progress
        progress.start_test()

        # 获取模型配置
        model_config = await self._get_model_config(test_record.model_id)
        if not model_config:
            raise ValueError(f"未找到模型配置: {test_record.model_id}")

        # 准备测试结果存储
        success_count = 0
        error_details = []
        round_results = []

        try:
            # 执行多轮测试
            for round_num in range(1, rounds + 1):
                progress.start_round(round_num)
                round_start_time = perf_counter_ns()

                try:
                    # 执行单轮测试（带重试和超时）
                    round_result = await self._execute_single_test_round_with_retry(
                        llm_service=llm_service,
                        prompt=prompt,
                        model_config=model_config,
                        round_num=round_num
                    )
                    round_results.append(round_result)
                    success_count += 1

                    # 记录轮次完成
                    progress.complete_round(round_num, success=True)
                    self._performance_metrics.increment_counter("successful_rounds")

                    # 记录轮次耗时
                    round_duration = (perf_counter_ns() - round_start_time) / 1_000_000_000  # 转换为秒
                    self._performance_metrics.record_metric("round_duration", round_duration)

                    # 轮次之间短暂暂停，避免API限流
                    await asyncio.sleep(PerformanceTestConfig.DEFAULT_SLEEP_INTERVAL)

                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"测试轮次 {round_num} 失败: {error_msg}", exc_info=True)

                    error_details.append({
                        "round": round_num,
                        "error": error_msg,
                        "type": type(e).__name__
                    })

                    # 记录轮次失败
                    progress.complete_round(round_num, success=False, error=error_msg)
                    self._performance_metrics.increment_counter("failed_rounds")

        finally:
            # 完成测试
            test_success = success_count > 0
            progress.complete_test(success=test_success)

            # 记录测试统计
            if test_success:
                self._performance_metrics.increment_counter("successful_tests")
            else:
                self._performance_metrics.increment_counter("failed_tests")

            self._performance_metrics.increment_counter("total_tests")
            self._performance_metrics.increment_counter("total_rounds", rounds)

            # 记录总测试时间
            test_duration = (perf_counter_ns() - test_start_time) / 1_000_000_000  # 转换为秒
            self._performance_metrics.record_metric("test_duration", test_duration)

        # 计算统计数据
        results = self._calculate_test_statistics(round_results)

        # 计算总成本
        if model_config and round_results:
            total_input_tokens = sum(r.get("input_tokens", 0) for r in round_results)
            total_output_tokens = sum(r.get("output_tokens", 0) for r in round_results)

            input_cost = (total_input_tokens * model_config.input_price) / 1000000
            output_cost = (total_output_tokens * model_config.output_price) / 1000000
            results["input_cost"] = input_cost
            results["output_cost"] = output_cost
            results["total_cost"] = input_cost + output_cost

        # 计算成功率和错误率
        results["success_rate"] = (success_count / rounds) * 100
        results["error_rate"] = 100 - results["success_rate"]

        # 构建详细结果
        results["detailed_results"] = {
            "responses": round_results,
            "errors": error_details,
            "stats": {
                "response_times": [r.get("response_time") for r in round_results if r.get("response_time")],
                "first_token_times": [r.get("first_token_time") for r in round_results if r.get("first_token_time")],
                "token_counts": [r.get("output_tokens") for r in round_results if r.get("output_tokens")],
                "tokens_per_second": [r.get("tokens_per_second") for r in round_results if r.get("tokens_per_second")]
            },
            "model_info": {
                "model_type": model_config.model_type,
                "model_name": model_config.model_name,
                "input_price": model_config.input_price,
                "output_price": model_config.output_price
            }
        }

        return results

    async def run_latency_test(
            self,
            request: LatencyTestRequest,
            llm_factory: LLMServiceFactory
    ) -> TestResponse:
        """运行延迟测试

        Args:
            request: 测试请求
            llm_factory: LLM服务工厂

        Returns:
            TestResponse: 测试结果
        """
        # 首先创建测试记录
        test_data = TestCreate(
            model_id=request.model_id,
            test_name=f"延迟测试 - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            test_type="latency",
            rounds=request.rounds,
            test_params={
                "measure_first_token": request.measure_first_token,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

        test_record = await self.create_test_record(test_data)

        try:
            # 获取模型配置
            model_config = await self._get_model_config(request.model_id)
            if not model_config:
                raise ValueError(f"未找到模型ID: {request.model_id}")

            # 获取模型类型枚举
            model_type = await self._get_model_type_enum(model_config)

            # 获取LLM服务
            llm_service = await llm_factory.get_service(
                model_type=model_type,
                model_name=model_config.model_name
            )

            # 执行延迟测试
            test_results = await self._execute_latency_test(
                llm_service=llm_service,
                test_record=test_record,
                measure_first_token=request.measure_first_token,
                rounds=request.rounds
            )

            # 更新测试结果
            updated_record = await self.update_test_results(
                test_id=test_record.id,
                results=test_results
            )

            # 构建响应
            response = TestResponse(
                id=updated_record.id,
                model_id=updated_record.model_id,
                model_name=model_config.display_name,
                test_name=updated_record.test_name,
                test_type="latency",
                rounds=updated_record.rounds,
                avg_response_time=test_results.get("avg_response_time"),
                avg_first_token_time=test_results.get("avg_first_token_time"),
                success_rate=test_results.get("success_rate"),
                error_rate=test_results.get("error_rate"),
                test_params=updated_record.test_params or {},
                test_date=updated_record.test_date,
                tested_by=updated_record.tested_by
            )

            # 添加扩展属性 - 如果使用TestDetailResponse
            if isinstance(response, TestDetailResponse):
                response.input_tokens = test_results.get("avg_input_tokens")
                response.output_tokens = test_results.get("avg_output_tokens")
                response.input_cost = test_results.get("input_cost")
                response.output_cost = test_results.get("output_cost")
                response.total_cost = test_results.get("total_cost")
                response.detailed_results = test_results.get("detailed_results")

            return response

        except Exception as e:
            # 记录错误并更新测试状态
            logger.error(f"执行延迟测试时出错: {str(e)}", exc_info=True)

            # 更新测试记录状态为失败
            await self.update_test_results(
                test_id=test_record.id,
                results={
                    "success_rate": 0,
                    "error_rate": 100,
                    "detailed_results": {
                        "error": str(e),
                        "status": "failed",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            )

            # 返回测试失败响应
            return TestResponse(
                id=test_record.id,
                model_id=request.model_id,
                model_name="未知模型",
                test_name=test_record.test_name,
                test_type="latency",
                rounds=request.rounds,
                avg_response_time=None,
                avg_first_token_time=None,
                avg_throughput=None,
                success_rate=0,
                error_rate=100,
                test_params=test_record.test_params or {},
                test_date=test_record.test_date,
                tested_by=None
            )

    async def _execute_latency_test(
            self,
            llm_service: BaseLLMService,
            test_record: ModelPerformanceTest,
            measure_first_token: bool,
            rounds: int
    ) -> Dict[str, Any]:
        """执行延迟测试逻辑

        Args:
            llm_service: LLM服务实例
            test_record: 测试记录
            measure_first_token: 是否测量首个token延迟
            rounds: 测试轮数

        Returns:
            Dict[str, Any]: 测试结果数据
        """
        import statistics
        import asyncio
        from time import perf_counter_ns

        # 获取模型配置
        from sqlalchemy import select
        from app.models.model_configuration import ModelConfiguration
        model_config_result = await self.db.execute(
            select(ModelConfiguration).where(ModelConfiguration.id == test_record.model_id)
        )
        model_config = model_config_result.scalar_one_or_none()
        model_type = model_config.model_type if model_config else "unknown"
        model_name = model_config.model_name if model_config else "unknown"

        # 准备测试结果存储
        response_times = []
        first_token_times = []
        input_token_counts = []
        output_token_counts = []
        success_count = 0
        error_details = []
        responses = []

        # 导入token计数工具
        from app.utils.token_counter import count_tokens

        # 测试提示词库 - 简单且多样化，专注测试延迟
        test_prompts = [
            "你好",
            "今天天气如何",
            "Azure是什么",
            "1+1等于几",
            "解释量子计算"
        ]

        # 确保有足够的提示词
        while len(test_prompts) < rounds:
            test_prompts.extend(test_prompts[:rounds - len(test_prompts)])

        # 执行多轮测试
        for round_num in range(1, rounds + 1):
            logger.info(f"执行延迟测试 {test_record.id} 第 {round_num}/{rounds} 轮")

            try:
                prompt = test_prompts[round_num - 1]

                if measure_first_token:
                    # 测量首个token时间 - 使用流式API
                    # 使用高精度计时器
                    start_time = perf_counter_ns()
                    first_token_received = False
                    first_token_time = None
                    response_content = ""

                    # 使用流式API
                    async for chunk in llm_service.chat_stream(
                            user_message=prompt,
                            extra_context={"is_performance_test": True}
                    ):
                        # 获取实际内容
                        chunk_content = chunk.get("content", "")

                        # 只在接收到非空内容时记录首个token时间
                        if not first_token_received and chunk_content and chunk_content.strip():
                            current_time = perf_counter_ns()
                            first_token_time = (current_time - start_time) / 1_000_000  # 纳秒转毫秒
                            first_token_received = True
                            logger.debug(f"接收到首个有效token: '{chunk_content}'")

                        # 累积内容
                        if chunk_content:
                            response_content += chunk_content

                    # 计算总响应时间
                    end_time = perf_counter_ns()
                    response_time = (end_time - start_time) / 1_000_000  # 纳秒转毫秒

                    # 计算token数
                    input_token_count = count_tokens(prompt, model_type, model_name)
                    output_token_count = count_tokens(response_content, model_type, model_name)

                    # 记录指标
                    response_times.append(response_time)
                    if first_token_time:
                        first_token_times.append(first_token_time)
                    input_token_counts.append(input_token_count)
                    output_token_counts.append(output_token_count)

                    # 记录成功
                    success_count += 1

                    # 计算成本（如果模型有价格信息）
                    input_cost = 0
                    output_cost = 0

                    if model_config:
                        input_cost = (input_token_count * model_config.input_price) / 1000000
                        output_cost = (output_token_count * model_config.output_price) / 1000000

                    # 保存响应内容
                    responses.append({
                        "round": round_num,
                        "prompt": prompt,
                        "response_time": response_time,
                        "first_token_time": first_token_time,
                        "input_tokens": input_token_count,
                        "output_tokens": output_token_count,
                        "input_cost": input_cost,
                        "output_cost": output_cost,
                        "content_sample": response_content[:100] + "..." if len(
                            response_content) > 100 else response_content,
                    })
                else:
                    # 只测量总响应时间
                    start_time = perf_counter_ns()

                    # 调用LLM服务
                    response = await llm_service.chat(
                        user_message=prompt,
                        extra_context={"is_performance_test": True}
                    )

                    # 计算总响应时间
                    end_time = perf_counter_ns()
                    response_time = (end_time - start_time) / 1_000_000  # 纳秒转毫秒

                    # 提取内容
                    content = response.get("content", "")

                    # 计算token数
                    input_token_count = count_tokens(prompt, model_type, model_name)
                    output_token_count = count_tokens(content, model_type, model_name)

                    # 记录指标
                    response_times.append(response_time)
                    input_token_counts.append(input_token_count)
                    output_token_counts.append(output_token_count)

                    # 记录成功
                    success_count += 1

                    # 计算成本（如果模型有价格信息）
                    input_cost = 0
                    output_cost = 0

                    if model_config:
                        input_cost = (input_token_count * model_config.input_price) / 1000000
                        output_cost = (output_token_count * model_config.output_price) / 1000000

                    # 保存响应内容
                    responses.append({
                        "round": round_num,
                        "prompt": prompt,
                        "response_time": response_time,
                        "input_tokens": input_token_count,
                        "output_tokens": output_token_count,
                        "input_cost": input_cost,
                        "output_cost": output_cost,
                        "content_sample": content[:100] + "..." if len(content) > 100 else content
                    })

                # 每轮之间短暂等待，避免API限流
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"延迟测试轮次 {round_num} 失败: {str(e)}", exc_info=True)
                error_details.append({
                    "round": round_num,
                    "error": str(e),
                    "type": type(e).__name__
                })

        # 计算统计数据
        results = {}

        if response_times:
            results["avg_response_time"] = statistics.mean(response_times)
            results["min_response_time"] = min(response_times)
            results["max_response_time"] = max(response_times)

            if len(response_times) > 1:
                results["std_response_time"] = statistics.stdev(response_times)

        if first_token_times:
            results["avg_first_token_time"] = statistics.mean(first_token_times)
            results["min_first_token_time"] = min(first_token_times)
            results["max_first_token_time"] = max(first_token_times)

            if len(first_token_times) > 1:
                results["std_first_token_time"] = statistics.stdev(first_token_times)

        if input_token_counts:
            results["avg_input_tokens"] = statistics.mean(input_token_counts)
            results["total_input_tokens"] = sum(input_token_counts)

        if output_token_counts:
            results["avg_output_tokens"] = statistics.mean(output_token_counts)
            results["total_output_tokens"] = sum(output_token_counts)

        # 计算成本
        if model_config and input_token_counts and output_token_counts:
            input_cost = (sum(input_token_counts) * model_config.input_price) / 1000000
            output_cost = (sum(output_token_counts) * model_config.output_price) / 1000000
            results["input_cost"] = input_cost
            results["output_cost"] = output_cost
            results["total_cost"] = input_cost + output_cost

        # 计算成功率和错误率
        results["success_rate"] = (success_count / rounds) * 100
        results["error_rate"] = 100 - results["success_rate"]

        # 构建详细结果
        results["detailed_results"] = {
            "responses": responses,
            "errors": error_details,
            "stats": {
                "response_times": response_times,
                "first_token_times": first_token_times,
                "input_token_counts": input_token_counts,
                "output_token_counts": output_token_counts
            },
            "test_config": {
                "measure_first_token": measure_first_token,
                "rounds": rounds
            },
            "model_info": {
                "model_type": model_type,
                "model_name": model_name,
                "input_price": model_config.input_price if model_config else 0,
                "output_price": model_config.output_price if model_config else 0
            }
        }

        return results

    async def run_batch_test(
            self,
            request: BatchTestRequest,
            llm_factory: LLMServiceFactory
    ) -> BatchTestResponse:
        """运行批量测试

        Args:
            request: 批量测试请求
            llm_factory: LLM服务工厂

        Returns:
            BatchTestResponse: 批量测试结果
        """
        batch_id = uuid.uuid4()
        completed_tests = []
        failed_tests = []

        logger.info(f"开始批量测试 {batch_id}，共 {len(request.model_ids)} 个模型")

        # 并发执行测试（限制并发数）
        semaphore = asyncio.Semaphore(PerformanceTestConfig.MAX_CONCURRENT_TESTS)

        async def test_single_model(model_id: uuid.UUID) -> Optional[TestResponse]:
            async with semaphore:
                try:
                    # 创建单个测试请求
                    test_request = SpeedTestRequest(
                        model_id=model_id,
                        test_type=request.test_type,
                        rounds=request.rounds,
                        prompt=request.prompt
                    )

                    # 执行测试
                    result = await self.run_standard_test(test_request, llm_factory)
                    return result

                except Exception as e:
                    logger.error(f"批量测试中模型 {model_id} 失败: {str(e)}")
                    failed_tests.append({
                        "model_id": str(model_id),
                        "error": str(e),
                        "error_type": type(e).__name__
                    })
                    return None

        # 并发执行所有测试
        tasks = [test_single_model(model_id) for model_id in request.model_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        for result in results:
            if isinstance(result, TestResponse):
                completed_tests.append(result)
            elif isinstance(result, Exception):
                failed_tests.append({
                    "error": str(result),
                    "error_type": type(result).__name__
                })

        # 确定状态
        if len(completed_tests) == len(request.model_ids):
            status = "completed"
        elif len(completed_tests) > 0:
            status = "partial"
        else:
            status = "failed"

        logger.info(f"批量测试 {batch_id} 完成，成功: {len(completed_tests)}, 失败: {len(failed_tests)}")

        return BatchTestResponse(
            batch_id=batch_id,
            total_models=len(request.model_ids),
            completed_tests=completed_tests,
            failed_tests=failed_tests,
            status=status
        )

    async def compare_tests(
            self,
            request: TestComparisonRequest
    ) -> TestComparisonResponse:
        """比较多个测试结果

        Args:
            request: 测试比较请求

        Returns:
            TestComparisonResponse: 比较结果
        """
        comparison_id = uuid.uuid4()

        # 获取所有测试记录
        tests = []
        for test_id in request.test_ids:
            test = await self.get_test_by_id(test_id)
            if not test:
                raise ValueError(f"测试记录不存在: {test_id}")
            tests.append(test)

        # 构建详细测试响应
        test_details = []
        for test in tests:
            model_config = await self._get_model_config(test.model_id)
            model_name = model_config.display_name if model_config else "未知模型"

            test_detail = TestDetailResponse(
                id=test.id,
                model_id=test.model_id,
                model_name=model_name,
                test_name=test.test_name,
                test_type=test.test_type,
                rounds=test.rounds,
                avg_response_time=test.avg_response_time,
                avg_first_token_time=test.avg_first_token_time,
                avg_throughput=test.avg_throughput,
                success_rate=test.success_rate,
                error_rate=test.error_rate,
                test_params=test.test_params or {},
                test_date=test.test_date,
                tested_by=test.tested_by,
                detailed_results=test.detailed_results
            )
            test_details.append(test_detail)

        # 计算指标比较
        metrics_comparison = {}
        for metric in request.metrics:
            metric_values = []
            for test in tests:
                value = getattr(test, metric, None)
                if value is not None:
                    metric_values.append({
                        "test_id": str(test.id),
                        "model_id": str(test.model_id),
                        "value": value
                    })

            if metric_values:
                values = [v["value"] for v in metric_values]
                metrics_comparison[metric] = {
                    "values": metric_values,
                    "min": min(values),
                    "max": max(values),
                    "avg": statistics.mean(values),
                    "std": statistics.stdev(values) if len(values) > 1 else 0
                }

        # 生成比较摘要
        summary = {
            "total_tests": len(tests),
            "test_types": list(set(test.test_type for test in tests)),
            "models_count": len(set(test.model_id for test in tests)),
            "best_performers": {},
            "worst_performers": {}
        }

        # 找出最佳和最差表现者
        for metric in request.metrics:
            if metric in metrics_comparison:
                values = metrics_comparison[metric]["values"]

                # 对于响应时间等，值越小越好
                if "time" in metric.lower():
                    best = min(values, key=lambda x: x["value"])
                    worst = max(values, key=lambda x: x["value"])
                else:
                    # 对于成功率等，值越大越好
                    best = max(values, key=lambda x: x["value"])
                    worst = min(values, key=lambda x: x["value"])

                summary["best_performers"][metric] = best
                summary["worst_performers"][metric] = worst

        return TestComparisonResponse(
            comparison_id=comparison_id,
            tests=test_details,
            metrics_comparison=metrics_comparison,
            summary=summary,
            created_at=datetime.utcnow()
        )