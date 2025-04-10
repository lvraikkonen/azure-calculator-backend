"""
组件初始化文件 - 导入并注册所有组件
"""
# 内置组件导入
from app.rag.components import embedders
from app.rag.components import chunkers
from app.rag.components import retrievers
from app.rag.components import rerankers
from app.rag.components import vector_store
from app.rag.components import query_transformers
from app.rag.components import generators
from app.rag.components import document_loaders
