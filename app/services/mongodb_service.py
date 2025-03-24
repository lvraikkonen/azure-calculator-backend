# app/services/mongodb_service.py
from typing import List, Optional, Dict, Any
from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import Depends

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.product import Product

logger = get_logger(__name__)

class MongoDBService:
    """MongoDB服务类"""
    
    def __init__(self):
        settings = get_settings()
        self.client = AsyncIOMotorClient(settings.MONGODB_URI)
        self.db = self.client[settings.MONGODB_DATABASE]
        logger.info(f"MongoDB服务初始化: {settings.MONGODB_URI}, 数据库: {settings.MONGODB_DATABASE}")
    
    async def get_all_products(self) -> List[Product]:
        """获取所有产品"""
        products = []
        logger.debug("开始从MongoDB获取所有产品")
        
        try:
            # 使用投影只获取需要的字段，优化性能
            cursor = self.db.azure_products.find(
                {}, 
                {
                    "_id": 1,
                    "product_code": 1, 
                    "name": 1, 
                    "description": 1, 
                    "price": 1, 
                    "price_unit": 1, 
                    "category": 1
                }
            )
            
            async for doc in cursor:
                products.append(Product(
                    id=str(doc["_id"]),
                    product_code=doc["product_code"],
                    name=doc["name"],
                    description=doc.get("description", ""),
                    price=doc["price"],
                    price_unit=doc["price_unit"],
                    category=doc["category"]
                ))
            
            logger.debug(f"MongoDB获取产品成功, 数量: {len(products)}")
            return products
        except Exception as e:
            logger.error(f"MongoDB获取产品失败: {str(e)}")
            return []
    
    async def get_products_by_category(self, category: str) -> List[Product]:
        """根据分类获取产品"""
        products = []
        logger.debug(f"开始从MongoDB获取分类 '{category}' 的产品")
        
        try:
            cursor = self.db.azure_products.find({"category": category})
            
            async for doc in cursor:
                products.append(Product(
                    id=str(doc["_id"]),
                    product_code=doc["product_code"],
                    name=doc["name"],
                    description=doc.get("description", ""),
                    price=doc["price"],
                    price_unit=doc["price_unit"],
                    category=doc["category"]
                ))
            
            logger.debug(f"MongoDB获取分类产品成功, 分类: {category}, 数量: {len(products)}")
            return products
        except Exception as e:
            logger.error(f"MongoDB获取分类产品失败: {str(e)}")
            return []
    
    async def get_product_by_id(self, product_code: str) -> Optional[Product]:
        """根据产品代码获取产品"""
        logger.debug(f"开始从MongoDB获取产品: {product_code}")
        
        try:
            doc = await self.db.azure_products.find_one({"product_code": product_code})
            
            if not doc:
                logger.warning(f"产品未找到: {product_code}")
                return None
                
            product = Product(
                id=str(doc["_id"]),
                product_code=doc["product_code"],
                name=doc["name"],
                description=doc.get("description", ""),
                price=doc["price"],
                price_unit=doc["price_unit"],
                category=doc["category"]
            )
            
            logger.debug(f"MongoDB获取产品成功: {product_code}")
            return product
        except Exception as e:
            logger.error(f"MongoDB获取产品失败: {str(e)}")
            return None
    
    async def get_price_trends(self, product_code: str, period: str = "month", limit: int = 12) -> List[Dict[str, Any]]:
        """
        获取价格趋势数据
        """
        logger.debug(f"获取价格趋势: {product_code}, 周期: {period}, 限制: {limit}")
        
        try:
            # 使用MongoDB聚合管道
            pipeline = [
                {"$match": {"product_code": product_code}},
                {"$sort": {"effective_date": -1}},
                {"$limit": limit},
                {"$project": {
                    "_id": 0,
                    "date": "$effective_date",
                    "price": 1
                }}
            ]
            
            result = []
            cursor = self.db.price_history.aggregate(pipeline)
            
            async for doc in cursor:
                result.append(doc)
            
            # 按日期排序
            result.sort(key=lambda x: x["date"])
            
            logger.debug(f"获取价格趋势成功, 结果数量: {len(result)}")
            return result
        except Exception as e:
            logger.error(f"获取价格趋势失败: {str(e)}")
            return []

    async def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        try:
            # 获取产品数量
            product_count = await self.db.azure_products.count_documents({})
            
            # 获取分类统计
            categories = []
            category_cursor = self.db.azure_products.aggregate([
                {"$group": {"_id": "$category", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ])
            
            async for doc in category_cursor:
                categories.append({
                    "name": doc["_id"],
                    "count": doc["count"]
                })
            
            # 获取最新同步信息
            sync_info = await self.db.sync_metadata.find_one(
                {"sync_type": "azure_prices"},
                sort=[("end_time", -1)]
            )
            
            last_sync = None
            if sync_info:
                last_sync = {
                    "sync_id": str(sync_info["_id"]),
                    "status": sync_info["status"],
                    "end_time": sync_info["end_time"],
                    "record_count": sync_info.get("record_count", 0)
                }
            
            return {
                "product_count": product_count,
                "categories": categories,
                "last_sync": last_sync
            }
        except Exception as e:
            logger.error(f"获取数据库统计失败: {str(e)}")
            return {
                "error": str(e)
            }

# 依赖注入函数
async def get_mongodb_service():
    """获取MongoDB服务实例"""
    service = MongoDBService()
    return service