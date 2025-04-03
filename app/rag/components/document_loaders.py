"""
文档加载器组件 - 从不同来源加载文档
"""
from typing import List, Dict, Optional
from pathlib import Path
import json
from datetime import datetime
import hashlib
import mimetypes

from app.rag.core.registry import register_component, RAGComponentRegistry
from app.rag.core.interfaces import DocumentLoader
from app.rag.core.models import Document, Metadata
from app.core.logging import get_logger
from app.rag.utils.file_processors import DocumentCache, ProcessorFactory

logger = get_logger(__name__)


@register_component(RAGComponentRegistry.DOCUMENT_LOADER, "web")
class WebDocumentLoader(DocumentLoader[Document]):
    """网页文档加载器 - 从URL加载网页内容"""
    
    def __init__(self, html_to_text: bool = True, timeout: int = 30, headers: Optional[Dict[str, str]] = None):
        """
        初始化网页文档加载器
        
        Args:
            html_to_text: 是否将HTML转换为纯文本
            timeout: 请求超时时间(秒)
            headers: 请求头
        """
        self.html_to_text = html_to_text
        self.timeout = timeout
        self.headers = headers or {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
    
    async def load(self, source: str, **kwargs) -> List[Document]:
        """
        加载网页文档
        
        Args:
            source: 网页URL
            **kwargs: 附加参数，可包含:
                - metadata: 自定义元数据
                - encoding: 文本编码
                - include_images: 是否包含图片文本说明
                
        Returns:
            List[Document]: 文档列表，通常只包含一个文档
        """
        pass
    
    def _html_to_text(self, html: str, include_images: bool = False) -> str:
        """
        将HTML转换为纯文本
        
        Args:
            html: HTML内容
            include_images: 是否包含图片文本说明
            
        Returns:
            str: 纯文本内容
        """
        pass
    
    def _extract_title(self, html: str) -> str:
        """
        从HTML中提取标题
        
        Args:
            html: HTML内容
            
        Returns:
            str: 标题，如果没有找到则返回空字符串
        """
        pass


@register_component(RAGComponentRegistry.DOCUMENT_LOADER, "file")
class FileDocumentLoader(DocumentLoader[Document]):
    """文件文档加载器 - 从文件系统加载文档"""

    def __init__(
            self,
            base_dir: Optional[str] = None,
            max_file_size: int = 10 * 1024 * 1024,
            use_cache: bool = True,
            safe_mode: bool = True
    ):
        """
        初始化文件文档加载器

        Args:
            base_dir: 基础目录，如果指定，则所有文件路径都将相对于此目录
            max_file_size: 最大处理文件大小(字节)，超过此大小的文件将被拒绝
            use_cache: 是否使用文档缓存
            safe_mode: 是否启用安全模式，拒绝处理可能不安全的文件
        """
        self.base_dir = Path(base_dir) if base_dir else None
        self.max_file_size = max_file_size
        self.use_cache = use_cache
        self.safe_mode = safe_mode

        # 注册MIME类型
        self._register_mime_types()

    def _register_mime_types(self):
        """注册额外的MIME类型"""
        mimetypes.add_type('application/javascript', '.js')
        mimetypes.add_type('text/markdown', '.md')
        mimetypes.add_type('text/x-python', '.py')

    def _is_safe_file(self, file_path: Path) -> bool:
        """
        检查文件是否安全

        Args:
            file_path: 文件路径

        Returns:
            bool: 是否安全
        """
        if not self.safe_mode:
            return True

        # 检查不安全的后缀
        unsafe_extensions = [
            '.exe', '.dll', '.bat', '.sh', '.com', '.cmd', '.ps1',
            '.vbs', '.js', '.jar', '.msi', '.app'
        ]

        if file_path.suffix.lower() in unsafe_extensions:
            logger.warning(f"不安全的文件类型: {file_path}")
            return False

        # 检查MIME类型
        mime_type, _ = mimetypes.guess_type(str(file_path))
        unsafe_mimes = [
            'application/x-executable',
            'application/x-dosexec',
            'application/x-msdos-program',
            'application/x-msdownload'
        ]

        if mime_type in unsafe_mimes:
            logger.warning(f"不安全的MIME类型: {file_path} ({mime_type})")
            return False

        return True

    def _generate_cache_key(self, file_path: Path, **kwargs) -> str:
        """
        生成缓存键

        Args:
            file_path: 文件路径
            **kwargs: 其他参数

        Returns:
            str: 缓存键
        """
        # 获取文件修改时间和大小
        stats = file_path.stat()
        mtime = stats.st_mtime
        size = stats.st_size

        # 生成参数哈希
        param_str = json.dumps(sorted(str(kwargs.items())))
        param_hash = hashlib.md5(param_str.encode()).hexdigest()

        # 组合缓存键
        return f"{file_path}_{mtime}_{size}_{param_hash}"

    async def load(self, source: str, **kwargs) -> List[Document]:
        """
        加载文件文档

        Args:
            source: 文件路径，可以是相对路径或绝对路径
            **kwargs: 附加参数，可包含:
                - metadata: 自定义元数据
                - encoding: 文本编码
                - skip_cache: 是否跳过缓存

        Returns:
            List[Document]: 文档列表
        """
        # 确定文件路径
        if self.base_dir:
            file_path = self.base_dir / source
        else:
            file_path = Path(source)

        logger.info(f"从文件加载文档: {file_path}")

        # 检查文件是否存在
        if not file_path.exists():
            logger.error(f"文件不存在: {file_path}")
            return []

        # 检查是否是目录
        if file_path.is_dir():
            logger.error(f"路径是目录，不是文件: {file_path}")
            return []

        # 安全检查
        if not self._is_safe_file(file_path):
            logger.error(f"文件未通过安全检查: {file_path}")
            return []

        # 检查文件大小
        file_size = file_path.stat().st_size
        if file_size > self.max_file_size:
            logger.error(f"文件大小超出限制: {file_path} ({file_size} bytes > {self.max_file_size} bytes)")
            return []

        try:
            # 检查缓存
            skip_cache = kwargs.get("skip_cache", False)
            cache_key = None

            if self.use_cache and not skip_cache:
                cache_key = self._generate_cache_key(file_path, **kwargs)
                cached_doc = DocumentCache.get(cache_key)

                if cached_doc:
                    logger.info(f"从缓存加载文档: {file_path}")
                    return [cached_doc]

            # 获取自定义参数
            custom_metadata = kwargs.get("metadata", {})
            encoding = kwargs.get("encoding", "utf-8")

            # 创建并使用适合的处理器
            processor = ProcessorFactory.create_processor(file_path)

            if not processor:
                logger.warning(f"找不到适合的处理器: {file_path}")
                return []

            # 处理文件
            result = await processor.process(file_path, encoding, **kwargs)

            if not result or "content" not in result:
                logger.error(f"处理器未返回有效内容: {file_path}")
                return []

            content = result["content"]
            processor_metadata = result.get("metadata", {})

            # 创建元数据
            metadata = Metadata(
                source=str(file_path),
                title=processor_metadata.get("title", file_path.name),
                created_at=datetime.fromtimestamp(file_path.stat().st_mtime),
                modified_at=datetime.fromtimestamp(file_path.stat().st_mtime),
                content_type=self._get_content_type(file_path),
                extra={
                    **custom_metadata,
                    **processor_metadata,
                    "file_size": file_path.stat().st_size,
                    "file_type": file_path.suffix.lower(),
                    "absolute_path": str(file_path.absolute())
                }
            )

            # 创建文档
            document = Document(
                content=content,
                metadata=metadata
            )

            # 缓存文档
            if self.use_cache and cache_key:
                DocumentCache.set(cache_key, document)

            logger.info(f"成功加载文档: {file_path}, 内容长度: {len(content)}")

            return [document]

        except FileNotFoundError:
            logger.error(f"文件不存在或无法访问: {file_path}")
            return []
        except PermissionError:
            logger.error(f"没有读取文件的权限: {file_path}")
            return []
        except UnicodeDecodeError:
            logger.error(f"文件编码错误: {file_path}, 尝试指定正确的编码")
            return []
        except json.JSONDecodeError:
            logger.error(f"JSON文件格式无效: {file_path}")
            return []
        except Exception as e:
            logger.error(f"加载文件失败: {file_path}, 错误类型: {type(e).__name__}, 错误信息: {str(e)}")
            return []

    def _get_content_type(self, file_path: Path) -> str:
        """
        获取内容类型

        Args:
            file_path: 文件路径

        Returns:
            str: 内容类型
        """
        # 尝试使用mimetypes模块获取类型
        mime_type, _ = mimetypes.guess_type(str(file_path))

        if mime_type:
            return mime_type

        # 如果mimetypes无法识别，使用自定义映射
        suffix = file_path.suffix.lower()

        content_type_map = {
            ".txt": "text/plain",
            ".html": "text/html",
            ".md": "text/markdown",
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".json": "application/json",
            ".csv": "text/csv",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".xls": "application/vnd.ms-excel",
            ".xml": "application/xml",
            ".yaml": "application/x-yaml",
            ".yml": "application/x-yaml",
            ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ".ppt": "application/vnd.ms-powerpoint",
            ".rtf": "application/rtf"
        }

        return content_type_map.get(suffix, "application/octet-stream")

# @register_component(RAGComponentRegistry.DOCUMENT_LOADER, "azure_api")
# class AzureAPIDocumentLoader(DocumentLoader[Document]):
#     """Azure API文档加载器 - 从Azure API获取服务信息"""
#
#     def __init__(self, api_key: Optional[str] = None, api_base: Optional[str] = None):
#         """
#         初始化Azure API文档加载器
#
#         Args:
#             api_key: Azure API密钥
#             api_base: Azure API基础URL
#         """
#         self.api_key = api_key
#         self.api_base = api_base or "https://management.azure.com"
#         self.headers = {
#             "User-Agent": "AzureCalculator/1.0",
#             "Content-Type": "application/json"
#         }
#
#         if api_key:
#             self.headers["Authorization"] = f"Bearer {api_key}"
#
#     async def load(self, source: str, **kwargs) -> List[Document]:
#         """
#         从Azure API加载文档
#
#         Args:
#             source: API路径或服务标识符
#             **kwargs: 附加参数，可包含:
#                 - api_version: API版本
#                 - metadata: 自定义元数据
#                 - params: 查询参数
#
#         Returns:
#             List[Document]: 文档列表
#         """
#         logger.info(f"从Azure API加载文档: {source}")
#
#         pass
#
#     def _create_document_from_item(
#         self,
#         item: Dict[str, Any],
#         source: str,
#         item_id: str,
#         custom_metadata: Dict[str, Any]
#     ) -> Document:
#         """
#         从API响应项创建文档
#
#         Args:
#             item: API响应项
#             source: 数据源
#             item_id: 项ID
#             custom_metadata: 自定义元数据
#
#         Returns:
#             Document: 文档
#         """
#         pass
#
# @register_component(RAGComponentRegistry.DOCUMENT_LOADER, "multi")
# class MultiDocumentLoader(DocumentLoader[Document]):
#     """多源文档加载器 - 从多个源加载文档并合并结果"""
#
#     def __init__(self, loaders: Optional[Dict[str, DocumentLoader[Document]]] = None):
#         """
#         初始化多源文档加载器
#
#         Args:
#             loaders: 加载器字典，键为类型，值为加载器实例
#         """
#         self.loaders = loaders or {}
#
#     def add_loader(self, loader_type: str, loader: DocumentLoader[Document]):
#         """
#         添加加载器
#
#         Args:
#             loader_type: 加载器类型
#             loader: 加载器实例
#         """
#         self.loaders[loader_type] = loader
#
#     async def load(self, source: Union[str, Dict[str, Any]], **kwargs) -> List[Document]:
#         """
#         从多个源加载文档
#
#         Args:
#             source: 源描述，可以是字符串或字典
#             **kwargs: 附加参数
#
#         Returns:
#             List[Document]: 文档列表
#         """
#         logger.info(f"从多个源加载文档")
#
#         pass
#
#     def _detect_source_type(self, source: str) -> str:
#         """
#         检测源类型
#
#         Args:
#             source: 源字符串
#
#         Returns:
#             str: 加载器类型
#         """
#         if source.startswith(("http://", "https://")):
#             return "web"
#         elif os.path.exists(source):
#             return "file"
#         elif "azure.com" in source or source.startswith(("subscriptions/", "providers/Microsoft")):
#             return "azure_api"
#         else:
#             return "web"  # 默认为网页