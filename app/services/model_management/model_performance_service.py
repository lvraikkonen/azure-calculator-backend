from datetime import datetime
import uuid
from typing import Dict, Any, List, Optional, Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.model_performance_test import ModelPerformanceTest
from app.services.llm.factory import LLMServiceFactory
from app.services.llm.base import BaseLLMService
from app.schemas.model_management.performance import (
    TestCreate, TestResponse, TestDetailResponse,
    SpeedTestRequest, LatencyTestRequest
)

logger = get_logger(__name__)


class ModelPerformanceService:
    """模型性能测试服务"""

    def __init__(self, db: AsyncSession):
        """初始化性能测试服务

        Args:
            db: 数据库会话
        """
        self.db = db

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
                "prompt": request.prompt or "请简要介绍Azure云服务的主要优势。",
                "timestamp": datetime.utcnow().isoformat()
            }
        )

        test_record = await self.create_test_record(test_data)

        try:
            # 获取LLM服务实例
            from app.services.llm.base import ModelType
            model_type = None

            # 查询模型类型
            from app.models.model_configuration import ModelConfiguration
            result = await self.db.execute(
                select(ModelConfiguration).where(
                    ModelConfiguration.id == request.model_id
                )
            )
            model_config = result.scalar_one_or_none()

            if model_config:
                # 将字符串模型类型转换为枚举
                try:
                    model_type = ModelType(model_config.model_type)
                except ValueError:
                    logger.warning(f"未知模型类型: {model_config.model_type}")

            # 获取LLM服务
            llm_service = await llm_factory.get_service(
                model_type=model_type,
                model_name=model_config.model_name if model_config else None
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
        token_counts = []
        input_token_counts = []
        tokens_per_second_list = []
        success_count = 0
        error_details = []
        responses = []

        # 导入token计数工具
        from app.utils.token_counter import count_tokens

        # 执行多轮测试
        for round_num in range(1, rounds + 1):
            logger.info(f"执行测试 {test_record.id} 第 {round_num}/{rounds} 轮")

            try:
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
                input_token_count = count_tokens(prompt, model_type, model_name)
                output_token_count = count_tokens(content, model_type, model_name)

                # 计算token生成速度 (tokens/sec)
                tokens_per_sec = 0
                if response_time > 0:
                    tokens_per_sec = output_token_count / (response_time / 1000)  # 转换为秒

                # 记录指标
                response_times.append(response_time)
                if first_token_time:
                    first_token_times.append(first_token_time)
                token_counts.append(output_token_count)
                input_token_counts.append(input_token_count)
                tokens_per_second_list.append(tokens_per_sec)

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
                    "response_time": response_time,
                    "first_token_time": first_token_time,
                    "input_tokens": input_token_count,
                    "output_tokens": output_token_count,
                    "tokens_per_second": tokens_per_sec,
                    "input_cost": input_cost,
                    "output_cost": output_cost,
                    "content_sample": content[:150] + "..." if len(content) > 150 else content
                })

                # 轮次之间短暂暂停，避免API限流
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"测试轮次 {round_num} 失败: {str(e)}", exc_info=True)
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

        if token_counts:
            results["avg_output_tokens"] = statistics.mean(token_counts)
            results["total_output_tokens"] = sum(token_counts)

        if input_token_counts:
            results["avg_input_tokens"] = statistics.mean(input_token_counts)
            results["total_input_tokens"] = sum(input_token_counts)

        if tokens_per_second_list:
            results["avg_tokens_per_second"] = statistics.mean(tokens_per_second_list)

        # 计算成本
        if model_config and input_token_counts and token_counts:
            input_cost = (sum(input_token_counts) * model_config.input_price) / 1000000
            output_cost = (sum(token_counts) * model_config.output_price) / 1000000
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
                "token_counts": token_counts,
                "tokens_per_second": tokens_per_second_list
            },
            "model_info": {
                "model_type": model_type,
                "model_name": model_name,
                "input_price": model_config.input_price if model_config else 0,
                "output_price": model_config.output_price if model_config else 0
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
            # 查询模型配置
            from app.models.model_configuration import ModelConfiguration
            result = await self.db.execute(
                select(ModelConfiguration).where(
                    ModelConfiguration.id == request.model_id
                )
            )
            model_config = result.scalar_one_or_none()

            if not model_config:
                raise ValueError(f"未找到模型ID: {request.model_id}")

            # 将字符串模型类型转换为枚举
            from app.services.llm.base import ModelType
            try:
                model_type = ModelType(model_config.model_type)
            except ValueError:
                logger.warning(f"未知模型类型: {model_config.model_type}")
                model_type = None

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