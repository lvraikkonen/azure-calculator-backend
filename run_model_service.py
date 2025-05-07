import asyncio
import logging
import sys
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List

# 将项目根目录添加到Python路径
project_root = Path(__file__).parent.parent.absolute()
sys.path.append(str(project_root))

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.services.model_management.model_configuration_service import ModelConfigurationService
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.services.llm.factory import LLMServiceFactory

# 设置日志
setup_logging()
logger = logging.getLogger("run_model_service")
logger.setLevel(logging.INFO)

settings = get_settings()


class ModelServiceTester:
    """交互式测试ModelConfigurationService的功能"""

    def __init__(self):
        self.db_session: Optional[AsyncSession] = None
        self.service: Optional[ModelConfigurationService] = None
        self.llm_factory: Optional[LLMServiceFactory] = None

    async def setup(self):
        """初始化数据库会话和服务"""
        self.db_session = AsyncSessionLocal()
        self.service = ModelConfigurationService(self.db_session)
        self.llm_factory = LLMServiceFactory()
        print("服务初始化完成")

    async def cleanup(self):
        """关闭数据库会话"""
        if self.db_session:
            await self.db_session.close()
        print("服务清理完成")

    async def list_models(self):
        """列出所有模型"""
        print("\n=== 模型列表 ===")

        # 获取筛选参数
        model_type = input("模型类型(留空为全部): ").strip() or None
        is_active_input = input("是否激活(y/n/留空为全部): ").strip().lower()
        is_active = None
        if is_active_input == 'y':
            is_active = True
        elif is_active_input == 'n':
            is_active = False

        search_term = input("搜索关键词(留空为全部): ").strip() or None

        # 调用服务方法
        models = await self.service.list_models(
            model_type=model_type,
            is_active=is_active,
            search_term=search_term
        )

        # 显示结果
        if not models:
            print("没有找到符合条件的模型")
            return

        print(f"\n共找到 {len(models)} 个模型:")
        for idx, model in enumerate(models, 1):
            print(f"{idx}. {model.name} ({model.model_type}/{model.model_name})")
            print(f"   状态: {'激活' if model.is_active else '停用'}")
            print(f"   价格: 输入 ${model.input_price:.4f}/百万tokens, 输出 ${model.output_price:.4f}/百万tokens")
            print(f"   ID: {model.id}")
            print("   " + "-" * 40)

    async def view_model_details(self):
        """查看特定模型详情"""
        print("\n=== 查看模型详情 ===")

        # 获取模型ID或名称
        id_or_name = input("请输入模型ID或名称: ").strip()
        if not id_or_name:
            print("未提供有效的ID或名称")
            return

        # 尝试解析为UUID
        model = None
        try:
            model_id = uuid.UUID(id_or_name)
            model = await self.service.get_model_by_id(model_id)
        except ValueError:
            # 不是有效的UUID，尝试作为名称查询
            model = await self.service.get_model_by_name(id_or_name)

        # 显示结果
        if not model:
            print(f"未找到模型: {id_or_name}")
            return

        print(f"\n模型详情:")
        print(f"名称: {model.name}")
        print(f"显示名称: {model.display_name}")
        print(f"描述: {model.description}")
        print(f"模型类型: {model.model_type}")
        print(f"模型名称: {model.model_name}")
        print(f"基础URL: {model.base_url}")
        print(f"API密钥: {'已设置' if model.api_key else '未设置'}")
        print(f"状态: {'激活' if model.is_active else '停用'}")
        print(f"可见性: {'可见' if model.is_visible else '隐藏'}")
        print(f"自定义: {'是' if model.is_custom else '否'}")
        print(f"价格: 输入 ${model.input_price:.4f}/百万tokens, 输出 ${model.output_price:.4f}/百万tokens")
        print(f"能力: {', '.join(model.capabilities or [])}")
        print(f"创建时间: {model.created_at}")
        print(f"最后更新: {model.updated_at}")
        print(f"使用请求数: {model.total_requests}")
        print(f"平均响应时间: {model.avg_response_time} ms")

    async def create_model(self):
        """创建新模型"""
        print("\n=== 创建新模型 ===")

        # 收集必要参数
        name = input("模型名称(唯一): ").strip()
        if not name:
            print("名称不能为空")
            return

        display_name = input("显示名称: ").strip() or name
        description = input("描述: ").strip()

        model_type = input("模型类型(openai, deepseek, anthropic): ").strip().lower()
        if model_type not in ['openai', 'deepseek', 'anthropic', 'azure_openai']:
            print("无效的模型类型")
            return

        model_name = input("具体模型名称: ").strip()
        if not model_name:
            print("模型名称不能为空")
            return

        api_key = input("API密钥(可选): ").strip() or None
        base_url = input("API基础URL(可选): ").strip() or None

        # 收集可选参数
        input_price_str = input("输入价格(每百万tokens): ").strip()
        input_price = float(input_price_str) if input_price_str else 0.0

        output_price_str = input("输出价格(每百万tokens): ").strip()
        output_price = float(output_price_str) if output_price_str else 0.0

        capabilities_str = input("能力(逗号分隔，如 text,chat,reasoning): ").strip()
        capabilities = [cap.strip() for cap in capabilities_str.split(',')] if capabilities_str else []

        is_active = input("是否激活(y/n): ").strip().lower() == 'y'
        is_visible = input("是否在UI可见(y/n): ").strip().lower() == 'y'
        is_custom = input("是否自定义模型(y/n): ").strip().lower() == 'y'

        # 调用服务创建模型
        try:
            model, created = await self.service.create_model(
                name=name,
                display_name=display_name,
                description=description,
                model_type=model_type,
                model_name=model_name,
                api_key=api_key,
                base_url=base_url,
                input_price=input_price,
                output_price=output_price,
                is_active=is_active,
                is_visible=is_visible,
                is_custom=is_custom,
                capabilities=capabilities
            )

            if created:
                print(f"成功创建模型: {name} (ID: {model.id})")
            else:
                print(f"模型已存在: {name} (ID: {model.id})")

        except Exception as e:
            print(f"创建模型时出错: {str(e)}")

    async def update_model(self):
        """更新现有模型"""
        print("\n=== 更新模型 ===")

        # 获取模型ID或名称
        id_or_name = input("请输入模型ID或名称: ").strip()
        if not id_or_name:
            print("未提供有效的ID或名称")
            return

        # 尝试获取模型
        model = None
        try:
            model_id = uuid.UUID(id_or_name)
            model = await self.service.get_model_by_id(model_id)
        except ValueError:
            # 不是有效的UUID，尝试作为名称查询
            model = await self.service.get_model_by_name(id_or_name)

        if not model:
            print(f"未找到模型: {id_or_name}")
            return

        print(f"将更新模型: {model.name} (ID: {model.id})")

        # 收集要更新的字段
        update_data: Dict[str, Any] = {}

        display_name = input(f"显示名称 [{model.display_name}] (留空保持不变): ").strip()
        if display_name:
            update_data['display_name'] = display_name

        description = input(f"描述 (留空保持不变): ").strip()
        if description:
            update_data['description'] = description

        api_key = input("API密钥 (留空保持不变): ").strip()
        if api_key:
            update_data['api_key'] = api_key

        base_url = input("API基础URL (留空保持不变): ").strip()
        if base_url:
            update_data['base_url'] = base_url

        input_price_str = input(f"输入价格 [{model.input_price}] (留空保持不变): ").strip()
        if input_price_str:
            update_data['input_price'] = float(input_price_str)

        output_price_str = input(f"输出价格 [{model.output_price}] (留空保持不变): ").strip()
        if output_price_str:
            update_data['output_price'] = float(output_price_str)

        is_active_str = input(f"是否激活 [{'y' if model.is_active else 'n'}] (y/n/留空保持不变): ").strip().lower()
        if is_active_str in ['y', 'n']:
            update_data['is_active'] = (is_active_str == 'y')

        is_visible_str = input(
            f"是否在UI可见 [{'y' if model.is_visible else 'n'}] (y/n/留空保持不变): ").strip().lower()
        if is_visible_str in ['y', 'n']:
            update_data['is_visible'] = (is_visible_str == 'y')

        # 如果没有更新数据，则退出
        if not update_data:
            print("没有提供任何更新数据")
            return

        # 调用服务更新模型
        try:
            updated_model = await self.service.update_model(model.id, update_data)
            if updated_model:
                print(f"成功更新模型: {updated_model.name}")
                print("更新的字段:")
                for key, value in update_data.items():
                    print(f"  {key}: {value}")
            else:
                print("更新失败")
        except Exception as e:
            print(f"更新模型时出错: {str(e)}")

    async def toggle_model_status(self):
        """切换模型状态(激活/停用)"""
        print("\n=== 切换模型状态 ===")

        # 获取模型ID或名称
        id_or_name = input("请输入模型ID或名称: ").strip()
        if not id_or_name:
            print("未提供有效的ID或名称")
            return

        # 尝试获取模型
        model = None
        try:
            model_id = uuid.UUID(id_or_name)
            model = await self.service.get_model_by_id(model_id)
        except ValueError:
            # 不是有效的UUID，尝试作为名称查询
            model = await self.service.get_model_by_name(id_or_name)

        if not model:
            print(f"未找到模型: {id_or_name}")
            return

        # 显示当前状态并确认操作
        current_status = "激活" if model.is_active else "停用"
        print(f"模型 {model.name} 当前状态: {current_status}")

        new_status_str = "停用" if model.is_active else "激活"
        confirm = input(f"确认将状态改为{new_status_str}? (y/n): ").strip().lower()
        if confirm != 'y':
            print("操作已取消")
            return

        # 执行状态切换
        try:
            if model.is_active:
                result = await self.service.deactivate_model(model.id)
            else:
                result = await self.service.activate_model(model.id)

            if result:
                print(f"已成功将模型 {model.name} 状态设为{new_status_str}")
            else:
                print("状态切换失败")
        except Exception as e:
            print(f"切换状态时出错: {str(e)}")

    async def delete_model(self):
        """删除模型"""
        print("\n=== 删除模型 ===")

        # 获取模型ID或名称
        id_or_name = input("请输入要删除的模型ID或名称: ").strip()
        if not id_or_name:
            print("未提供有效的ID或名称")
            return

        # 尝试获取模型
        model = None
        model_id = None
        try:
            model_id = uuid.UUID(id_or_name)
            model = await self.service.get_model_by_id(model_id)
        except ValueError:
            # 不是有效的UUID，尝试作为名称查询
            model = await self.service.get_model_by_name(id_or_name)
            if model:
                model_id = model.id

        if not model:
            print(f"未找到模型: {id_or_name}")
            return

        # 确认删除
        confirm = input(f"确认删除模型 {model.name} (ID: {model.id})? 此操作不可撤销 (yes/no): ").strip().lower()
        if confirm != 'yes':
            print("删除操作已取消")
            return

        # 执行删除
        try:
            result = await self.service.delete_model(model_id)
            if result:
                print(f"已成功删除模型 {model.name}")
            else:
                print("删除操作失败")
        except Exception as e:
            print(f"删除模型时出错: {str(e)}")

    async def test_model_connection(self):
        """测试模型连接"""
        print("\n=== 测试模型连接 ===")

        # 获取模型ID或名称
        id_or_name = input("请输入要测试的模型ID或名称: ").strip()
        if not id_or_name:
            print("未提供有效的ID或名称")
            return

        # 尝试获取模型
        model = None
        model_id = None
        try:
            model_id = uuid.UUID(id_or_name)
            model = await self.service.get_model_by_id(model_id)
        except ValueError:
            # 不是有效的UUID，尝试作为名称查询
            model = await self.service.get_model_by_name(id_or_name)
            if model:
                model_id = model.id

        if not model:
            print(f"未找到模型: {id_or_name}")
            return

        # 确认测试模型具有API密钥
        if not model.api_key:
            print(f"模型 {model.name} 没有设置API密钥，无法测试连接")
            return

        # 获取测试消息
        test_message = input("测试消息 (留空使用默认消息): ").strip()

        # 创建测试请求
        from app.schemas.model_management.configuration import ModelTestRequest
        test_request = ModelTestRequest(
            model_id=model_id,
            test_message=test_message if test_message else None
        )

        # 执行测试
        print(f"正在测试模型 {model.name} 的连接...")
        try:
            if not self.llm_factory:
                print("LLM工厂未初始化")
                return

            response = await self.service.test_model_connection(test_request, self.llm_factory)

            # 显示测试结果
            print("\n测试结果:")
            print(f"状态: {'成功' if response.success else '失败'}")
            if response.response_time:
                print(f"响应时间: {response.response_time:.2f} ms")
            print(f"消息: {response.message}")

            if response.success:
                print(f"模型响应: {response.response}")
            else:
                print(f"错误: {response.error}")

        except Exception as e:
            print(f"测试连接时出错: {str(e)}")

    async def run(self):
        """运行交互式菜单"""
        await self.setup()

        while True:
            print("\n==== 模型配置服务测试 ====")
            print("1. 列出所有模型")
            print("2. 查看模型详情")
            print("3. 创建新模型")
            print("4. 更新模型")
            print("5. 切换模型状态(激活/停用)")
            print("6. 删除模型")
            print("7. 测试模型连接")
            print("0. 退出")

            choice = input("\n请选择操作: ").strip()

            try:
                if choice == '1':
                    await self.list_models()
                elif choice == '2':
                    await self.view_model_details()
                elif choice == '3':
                    await self.create_model()
                elif choice == '4':
                    await self.update_model()
                elif choice == '5':
                    await self.toggle_model_status()
                elif choice == '6':
                    await self.delete_model()
                elif choice == '7':
                    await self.test_model_connection()
                elif choice == '0':
                    break
                else:
                    print("无效的选择，请重试")
            except Exception as e:
                print(f"操作执行过程中出错: {str(e)}")

        await self.cleanup()


if __name__ == "__main__":
    try:
        tester = ModelServiceTester()
        asyncio.run(tester.run())
    except KeyboardInterrupt:
        print("\n程序已被用户中断")
    except Exception as e:
        logger.error(f"程序运行错误: {str(e)}")
        sys.exit(1)