"""
文档加载器组件 - 从不同来源加载文档
"""
from typing import List, Dict, Any, Optional, Union
import aiohttp
import asyncio
import os
from pathlib import Path
import json
from datetime import datetime
import re

from app.rag.core.registry import register_component, RAGComponentRegistry
from app.rag.core.interfaces import DocumentLoader
from app.rag.core.models import Document, Metadata
from app.core.logging import get_logger

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
        logger.info(f"从URL加载文档: {source}")
        
        try:
            # 获取自定义参数
            custom_metadata = kwargs.get("metadata", {})
            encoding = kwargs.get("encoding", "utf-8")
            include_images = kwargs.get("include_images", False)
            
            # 发送HTTP请求
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    source, 
                    headers=self.headers, 
                    timeout=self.timeout
                ) as response:
                    
                    # 检查响应
                    if response.status != 200:
                        logger.error(f"加载URL失败: {source}, 状态码: {response.status}")
                        return []
                    
                    # 获取内容类型
                    content_type = response.headers.get("Content-Type", "")
                    
                    # 读取内容
                    if "application/json" in content_type:
                        # 处理JSON内容
                        content = await response.json()
                        text = json.dumps(content, ensure_ascii=False, indent=2)
                    else:
                        # 处理HTML或文本内容
                        html = await response.text(encoding=encoding)
                        
                        if self.html_to_text and "text/html" in content_type:
                            text = self._html_to_text(html, include_images)
                        else:
                            text = html
            
            # 创建元数据
            title = self._extract_title(text) if "text/html" in content_type else ""
            
            metadata = Metadata(
                source=source,
                title=title or f"网页内容: {source}",
                created_at=datetime.now(),
                content_type=content_type,
                extra={
                    **custom_metadata,
                    "url": source,
                    "status": 200,
                    "headers": dict(response.headers)
                }
            )
            
            # 创建文档
            document = Document(
                content=text,
                metadata=metadata
            )
            
            logger.info(f"成功加载文档: {source}, 内容长度: {len(text)}")
            return [document]
            
        except Exception as e:
            logger.error(f"加载URL失败: {source}, 错误: {str(e)}")
            return []
    
    def _html_to_text(self, html: str, include_images: bool = False) -> str:
        """
        将HTML转换为纯文本
        
        Args:
            html: HTML内容
            include_images: 是否包含图片文本说明
            
        Returns:
            str: 纯文本内容
        """
        try:
            # 尝试使用BeautifulSoup进行更好的解析
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html, "html.parser")
            
            # 移除脚本和样式
            for script in soup(["script", "style"]):
                script.extract()
            
            # 获取图片信息
            if include_images:
                for img in soup.find_all("img"):
                    alt = img.get("alt", "")
                    src = img.get("src", "")
                    if alt:
                        img.replace_with(f"[图片: {alt}]")
                    elif src:
                        img.replace_with(f"[图片: {src.split('/')[-1]}]")
                    else:
                        img.replace_with("[图片]")
            
            # 获取文本
            text = soup.get_text(separator="\n", strip=True)
            
            # 删除多余空行
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = "\n".join(chunk for chunk in chunks if chunk)
            
            return text
            
        except ImportError:
            # 如果没有BeautifulSoup，使用简单的正则表达式
            logger.warning("未安装BeautifulSoup，使用简单正则表达式处理HTML")
            
            # 移除HTML标签
            text = re.sub(r"<[^>]*>", " ", html)
            
            # 删除多余空格
            text = re.sub(r"\s+", " ", text).strip()
            
            return text
    
    def _extract_title(self, html: str) -> str:
        """
        从HTML中提取标题
        
        Args:
            html: HTML内容
            
        Returns:
            str: 标题，如果没有找到则返回空字符串
        """
        # 使用正则表达式提取标题
        title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        if title_match:
            return title_match.group(1).strip()
        
        # 尝试从h1标签获取
        h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.IGNORECASE | re.DOTALL)
        if h1_match:
            # 移除HTML标签
            h1_text = re.sub(r"<[^>]*>", "", h1_match.group(1))
            return h1_text.strip()
        
        return ""

@register_component(RAGComponentRegistry.DOCUMENT_LOADER, "file")
class FileDocumentLoader(DocumentLoader[Document]):
    """文件文档加载器 - 从文件系统加载文档"""
    
    def __init__(self, base_dir: Optional[str] = None):
        """
        初始化文件文档加载器
        
        Args:
            base_dir: 基础目录，如果指定，则所有文件路径都将相对于此目录
        """
        self.base_dir = Path(base_dir) if base_dir else None
    
    async def load(self, source: str, **kwargs) -> List[Document]:
        """
        加载文件文档
        
        Args:
            source: 文件路径，可以是相对路径或绝对路径
            **kwargs: 附加参数，可包含:
                - metadata: 自定义元数据
                - encoding: 文本编码
                
        Returns:
            List[Document]: 文档列表，通常只包含一个文档
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
        
        try:
            # 获取自定义参数
            custom_metadata = kwargs.get("metadata", {})
            encoding = kwargs.get("encoding", "utf-8")
            
            # 获取文件类型
            file_type = self._get_file_type(file_path)
            
            # 根据文件类型处理文件
            if file_type == "text":
                # 处理文本文件
                with open(file_path, "r", encoding=encoding) as f:
                    content = f.read()
                
            elif file_type == "pdf":
                # 处理PDF文件
                content = self._extract_pdf_text(file_path)
                
            elif file_type == "docx":
                # 处理Word文档
                content = self._extract_docx_text(file_path)
                
            elif file_type == "json":
                # 处理JSON文件
                with open(file_path, "r", encoding=encoding) as f:
                    data = json.load(f)
                content = json.dumps(data, ensure_ascii=False, indent=2)
                
            else:
                # 未知文件类型
                logger.warning(f"不支持的文件类型: {file_path.suffix}")
                return []
            
            # 创建元数据
            metadata = Metadata(
                source=str(file_path),
                title=file_path.name,
                created_at=datetime.fromtimestamp(file_path.stat().st_mtime),
                content_type=self._get_content_type(file_path),
                extra={
                    **custom_metadata,
                    "file_size": file_path.stat().st_size,
                    "file_type": file_type,
                    "absolute_path": str(file_path.absolute())
                }
            )
            
            # 创建文档
            document = Document(
                content=content,
                metadata=metadata
            )
            
            logger.info(f"成功加载文档: {file_path}, 内容长度: {len(content)}")
            return [document]
            
        except Exception as e:
            logger.error(f"加载文件失败: {file_path}, 错误: {str(e)}")
            return []
    
    def _get_file_type(self, file_path: Path) -> str:
        """
        获取文件类型
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: 文件类型
        """
        suffix = file_path.suffix.lower()
        
        if suffix in [".txt", ".md", ".py", ".js", ".html", ".css", ".csv"]:
            return "text"
        elif suffix == ".pdf":
            return "pdf"
        elif suffix in [".doc", ".docx"]:
            return "docx"
        elif suffix == ".json":
            return "json"
        else:
            return "unknown"
    
    def _get_content_type(self, file_path: Path) -> str:
        """
        获取内容类型
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: 内容类型
        """
        suffix = file_path.suffix.lower()
        
        if suffix == ".txt":
            return "text/plain"
        elif suffix == ".html":
            return "text/html"
        elif suffix == ".md":
            return "text/markdown"
        elif suffix == ".pdf":
            return "application/pdf"
        elif suffix in [".doc", ".docx"]:
            return "application/msword"
        elif suffix == ".json":
            return "application/json"
        elif suffix == ".csv":
            return "text/csv"
        else:
            return "application/octet-stream"
    
    def _extract_pdf_text(self, file_path: Path) -> str:
        """
        提取PDF文本
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            str: PDF文本内容
        """
        try:
            # 尝试使用PyPDF2
            from PyPDF2 import PdfReader
            
            text_parts = []
            reader = PdfReader(file_path)
            
            for page in reader.pages:
                text_parts.append(page.extract_text())
            
            return "\n\n".join(text_parts)
            
        except ImportError:
            logger.warning("未安装PyPDF2，无法提取PDF文本")
            return f"[PDF文件: {file_path.name}]"
    
    def _extract_docx_text(self, file_path: Path) -> str:
        """
        提取Word文档文本
        
        Args:
            file_path: Word文档路径
            
        Returns:
            str: Word文档文本内容
        """
        try:
            # 尝试使用python-docx
            import docx
            
            doc = docx.Document(file_path)
            text_parts = []
            
            for para in doc.paragraphs:
                text_parts.append(para.text)
            
            return "\n".join(text_parts)
            
        except ImportError:
            logger.warning("未安装python-docx，无法提取Word文档文本")
            return f"[Word文档: {file_path.name}]"

@register_component(RAGComponentRegistry.DOCUMENT_LOADER, "azure_api")
class AzureAPIDocumentLoader(DocumentLoader[Document]):
    """Azure API文档加载器 - 从Azure API获取服务信息"""
    
    def __init__(self, api_key: Optional[str] = None, api_base: Optional[str] = None):
        """
        初始化Azure API文档加载器
        
        Args:
            api_key: Azure API密钥
            api_base: Azure API基础URL
        """
        self.api_key = api_key
        self.api_base = api_base or "https://management.azure.com"
        self.headers = {
            "User-Agent": "AzureCalculator/1.0",
            "Content-Type": "application/json"
        }
        
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
    
    async def load(self, source: str, **kwargs) -> List[Document]:
        """
        从Azure API加载文档
        
        Args:
            source: API路径或服务标识符
            **kwargs: 附加参数，可包含:
                - api_version: API版本
                - metadata: 自定义元数据
                - params: 查询参数
                
        Returns:
            List[Document]: 文档列表
        """
        logger.info(f"从Azure API加载文档: {source}")
        
        # 获取自定义参数
        api_version = kwargs.get("api_version", "2022-12-01")
        custom_metadata = kwargs.get("metadata", {})
        params = kwargs.get("params", {})
        
        # 添加API版本参数
        params["api-version"] = api_version
        
        # 构建URL
        if source.startswith("http"):
            url = source
        else:
            url = f"{self.api_base}/{source}"
        
        try:
            # 发送API请求
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=self.headers,
                    params=params
                ) as response:
                    
                    # 检查响应
                    if response.status != 200:
                        logger.error(f"API请求失败: {url}, 状态码: {response.status}")
                        error_text = await response.text()
                        logger.error(f"错误信息: {error_text}")
                        return []
                    
                    # 获取响应数据
                    data = await response.json()
            
            # 处理响应数据
            documents = []
            
            # 检查数据类型
            if isinstance(data, list):
                # 列表数据，每个项创建一个文档
                for i, item in enumerate(data):
                    doc = self._create_document_from_item(
                        item,
                        source,
                        f"{source}[{i}]",
                        custom_metadata
                    )
                    documents.append(doc)
            elif isinstance(data, dict):
                # 检查是否有value字段(Azure分页响应)
                if "value" in data and isinstance(data["value"], list):
                    for i, item in enumerate(data["value"]):
                        doc = self._create_document_from_item(
                            item,
                            source,
                            f"{source}/value[{i}]",
                            custom_metadata
                        )
                        documents.append(doc)
                else:
                    # 单个对象
                    doc = self._create_document_from_item(
                        data,
                        source,
                        source,
                        custom_metadata
                    )
                    documents.append(doc)
            
            logger.info(f"从API加载了 {len(documents)} 个文档")
            return documents
            
        except Exception as e:
            logger.error(f"加载API文档失败: {url}, 错误: {str(e)}")
            return []
    
    def _create_document_from_item(
        self, 
        item: Dict[str, Any], 
        source: str, 
        item_id: str,
        custom_metadata: Dict[str, Any]
    ) -> Document:
        """
        从API响应项创建文档
        
        Args:
            item: API响应项
            source: 数据源
            item_id: 项ID
            custom_metadata: 自定义元数据
            
        Returns:
            Document: 文档
        """
        # 提取可能的标题字段
        title = None
        for title_field in ["name", "displayName", "title", "id"]:
            if title_field in item:
                title = item.get(title_field)
                break
        
        # 格式化内容
        content = json.dumps(item, ensure_ascii=False, indent=2)
        
        # 创建元数据
        metadata = Metadata(
            source=source,
            title=title or f"Azure API数据: {item_id}",
            content_type="application/json",
            extra={
                **custom_metadata,
                "api_path": source,
                "item_id": item_id
            }
        )
        
        # 创建文档
        return Document(
            content=content,
            metadata=metadata
        )

@register_component(RAGComponentRegistry.DOCUMENT_LOADER, "multi")
class MultiDocumentLoader(DocumentLoader[Document]):
    """多源文档加载器 - 从多个源加载文档并合并结果"""
    
    def __init__(self, loaders: Optional[Dict[str, DocumentLoader[Document]]] = None):
        """
        初始化多源文档加载器
        
        Args:
            loaders: 加载器字典，键为类型，值为加载器实例
        """
        self.loaders = loaders or {}
    
    def add_loader(self, loader_type: str, loader: DocumentLoader[Document]):
        """
        添加加载器
        
        Args:
            loader_type: 加载器类型
            loader: 加载器实例
        """
        self.loaders[loader_type] = loader
    
    async def load(self, source: Union[str, Dict[str, Any]], **kwargs) -> List[Document]:
        """
        从多个源加载文档
        
        Args:
            source: 源描述，可以是字符串或字典
            **kwargs: 附加参数
            
        Returns:
            List[Document]: 文档列表
        """
        logger.info(f"从多个源加载文档")
        
        if isinstance(source, str):
            # 自动检测源类型
            loader_type = self._detect_source_type(source)
            
            if loader_type in self.loaders:
                loader = self.loaders[loader_type]
                return await loader.load(source, **kwargs)
            else:
                logger.error(f"未找到适用于源 {source} 的加载器")
                return []
        
        elif isinstance(source, dict):
            # 源描述字典，包含多个源
            all_documents = []
            
            for loader_type, sources in source.items():
                if loader_type not in self.loaders:
                    logger.warning(f"未找到加载器: {loader_type}")
                    continue
                
                loader = self.loaders[loader_type]
                
                if isinstance(sources, list):
                    # 多个源
                    for src in sources:
                        docs = await loader.load(src, **kwargs)
                        all_documents.extend(docs)
                else:
                    # 单个源
                    docs = await loader.load(sources, **kwargs)
                    all_documents.extend(docs)
            
            logger.info(f"从多个源加载了总计 {len(all_documents)} 个文档")
            return all_documents
        
        else:
            logger.error(f"不支持的源类型: {type(source)}")
            return []
    
    def _detect_source_type(self, source: str) -> str:
        """
        检测源类型
        
        Args:
            source: 源字符串
            
        Returns:
            str: 加载器类型
        """
        if source.startswith(("http://", "https://")):
            return "web"
        elif os.path.exists(source):
            return "file"
        elif "azure.com" in source or source.startswith(("subscriptions/", "providers/Microsoft")):
            return "azure_api"
        else:
            return "web"  # 默认为网页