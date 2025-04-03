"""
文件处理器模块 - 提供各种文件格式的处理能力
"""
# 导出基础定义
from app.rag.utils.file_processors.base import FileProcessor, FileProcessorRegistry

# 导出工厂和缓存
from app.rag.utils.file_processors.factory import ProcessorFactory, DocumentCache

# 确保所有处理器都被导入以注册到注册表
from app.rag.utils.file_processors.text_processor import TextFileProcessor
from app.rag.utils.file_processors.pdf_processor import PDFFileProcessor
from app.rag.utils.file_processors.office_processors import DocxFileProcessor, ExcelFileProcessor

# 方便使用的导出
__all__ = [
    'FileProcessor',
    'FileProcessorRegistry',
    'ProcessorFactory',
    'DocumentCache',
    'TextFileProcessor',
    'PDFFileProcessor',
    'DocxFileProcessor',
    'ExcelFileProcessor'
]