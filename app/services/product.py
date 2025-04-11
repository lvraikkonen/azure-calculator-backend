from typing import List, Optional
import logging

from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product as ProductModel
from app.schemas.product import Product, ProductCreate, ProductUpdate

logger = logging.getLogger(__name__)

class ProductService:
    """产品服务，用于提供Azure产品数据"""
    
    def __init__(self, db: Optional[AsyncSession] = None):
        """初始化产品服务"""
        self.db = db
    
    async def get_all_products(self) -> List[Product]:
        """
        获取所有产品列表
        
        Returns:
            List[Product]: 产品列表
        """
        if self.db:
            # 使用数据库获取
            stmt = select(ProductModel)
            result = await self.db.execute(stmt)
            products = result.scalars().all()
            return [Product.from_orm(product) for product in products]
        else:
            # 返回预定义样本数据
            return self._load_sample_products()
    
    async def get_product_by_id(self, product_id: str) -> Optional[Product]:
        """
        根据ID获取产品
        
        Args:
            product_id: 产品代码
            
        Returns:
            Optional[Product]: 产品信息，如不存在则返回None
        """
        if self.db:
            stmt = select(ProductModel).where(ProductModel.product_code == product_id)
            result = await self.db.execute(stmt)
            product = result.scalar_one_or_none()
            return Product.from_orm(product) if product else None
        else:
            # 从样本数据中查找
            for product in self._load_sample_products():
                if product.id == product_id:
                    return product
            return None
    
    async def get_products_by_category(self, category: str) -> List[Product]:
        """
        根据分类获取产品列表
        
        Args:
            category: 产品分类
            
        Returns:
            List[Product]: 指定分类的产品列表
        """
        if self.db:
            stmt = select(ProductModel).where(ProductModel.category == category)
            result = await self.db.execute(stmt)
            products = result.scalars().all()
            return [Product.from_orm(product) for product in products]
        else:
            # 从样本数据过滤
            return [p for p in self._load_sample_products() if p.category == category]
    
    def _load_sample_products(self) -> List[Product]:
        """
        加载示例产品数据
        在后续迭代中，这将从Azure定价API获取
        """
        return [
            Product(
                id="00000000-0000-0000-0000-000000000001",
                product_code="vm-basic",
                name="虚拟机(基础)",
                description="基础型虚拟机，适合开发测试和轻量级应用",
                price=0.0575,
                price_unit="USD/小时",
                category="计算"
            ),
            Product(
                id="00000000-0000-0000-0000-000000000002",
                product_code="vm-standard",
                name="虚拟机(标准)",
                description="标准型虚拟机，适合生产环境的中等负载应用",
                price=0.1150,
                price_unit="USD/小时",
                category="计算"
            ),
            Product(
                id="00000000-0000-0000-0000-000000000003",
                product_code="vm-premium",
                name="虚拟机(高级)",
                description="高性能虚拟机，适合密集型计算和高负载应用",
                price=0.2300,
                price_unit="USD/小时",
                category="计算"
            ),
            Product(
                id="00000000-0000-0000-0000-000000000004",
                product_code="storage-std",
                name="标准存储",
                description="标准性能存储，适合一般文件存储需求",
                price=0.0184,
                price_unit="USD/GB/月",
                category="存储"
            ),
            Product(
                id="00000000-0000-0000-0000-000000000005",
                product_code="storage-premium",
                name="高级存储",
                description="高性能SSD存储，适合性能敏感型应用",
                price=0.0749,
                price_unit="USD/GB/月",
                category="存储"
            ),
            Product(
                id="00000000-0000-0000-0000-000000000006",
                product_code="cosmos-db",
                name="CosmosDB",
                description="全球分布式多模型数据库服务",
                price=25.00,
                price_unit="USD/100 RU/s/月",
                category="数据库"
            ),
            Product(
                id="00000000-0000-0000-0000-000000000007",
                product_code="sql-db-basic",
                name="SQL数据库(基础)",
                description="基础SQL数据库服务，适合小型应用",
                price=15.39,
                price_unit="USD/月",
                category="数据库"
            ),
            Product(
                id="00000000-0000-0000-0000-000000000008",
                product_code="app-service-basic",
                name="应用服务(基础)",
                description="托管Web应用、移动后端和RESTful API的基础平台",
                price=0.018,
                price_unit="USD/小时",
                category="应用服务"
            ),
            Product(
                id="00000000-0000-0000-0000-000000000009",
                product_code="app-service-standard",
                name="应用服务(标准)",
                description="托管Web应用的标准平台，支持自动扩展",
                price=0.075,
                price_unit="USD/小时",
                category="应用服务"
            ),
            Product(
                id="00000000-0000-0000-0000-000000000010",
                product_code="cdn-standard",
                name="内容分发网络(标准)",
                description="全球内容分发网络，加速静态内容交付",
                price=0.081,
                price_unit="USD/GB",
                category="网络"
            )
        ]
    
    async def create_product(self, db: AsyncSession, product: ProductCreate) -> Product:
        """
        创建新产品
        
        Args:
            db: 数据库会话
            product: 产品创建模型
            
        Returns:
            Product: 创建的产品
        """
        db_product = ProductModel(
            product_code=product.product_code,
            name=product.name,
            description=product.description,
            price=product.price,
            price_unit=product.price_unit,
            category=product.category
        )
        
        db.add(db_product)
        await db.commit()
        await db.refresh(db_product)
        
        return Product.from_orm(db_product)
    
    async def update_product(self, db: AsyncSession, product_code: str, product_update: ProductUpdate) -> Optional[Product]:
        """
        更新产品
        
        Args:
            db: 数据库会话
            product_code: 产品代码
            product_update: 产品更新模型
            
        Returns:
            Optional[Product]: 更新后的产品，如不存在则返回None
        """
        stmt = select(ProductModel).where(ProductModel.product_code == product_code)
        result = await db.execute(stmt)
        db_product = result.scalar_one_or_none()
        
        if not db_product:
            return None
            
        update_data = product_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_product, key, value)
            
        await db.commit()
        await db.refresh(db_product)
        
        return Product.from_orm(db_product)