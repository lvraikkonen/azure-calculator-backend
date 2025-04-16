from typing import List, Dict, Any
from app.services.product import ProductService
from app.services.llm.base import ContextProvider


class ProductContextProvider(ContextProvider):
    """产品上下文提供者"""

    def __init__(self, product_service: ProductService):
        self.product_service = product_service

    async def get_context(self) -> str:
        """获取产品上下文信息"""
        products = await self.product_service.get_all_products()
        return "\n".join(
            [f"{p.name} (ID: {p.product_code}): {p.description}. 价格: {p.price} {p.price_unit}."
             for p in products]
        )

    @property
    def provider_name(self) -> str:
        return "product_context"


# 可以添加更多上下文提供者，例如:
class KnowledgeBaseContextProvider(ContextProvider):
    """知识库上下文提供者"""

    def __init__(self, knowledge_service):
        self.knowledge_service = knowledge_service

    async def get_context(self) -> str:
        """获取知识库上下文"""
        # 实现知识库检索逻辑
        return "相关知识..."

    @property
    def provider_name(self) -> str:
        return "knowledge_base"