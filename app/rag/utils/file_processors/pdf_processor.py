from typing import Dict, Any
from pathlib import Path
from app.rag.utils.file_processors.base import FileProcessorRegistry

from app.core.logging import get_logger

logger = get_logger(__name__)


@FileProcessorRegistry.register
class PDFFileProcessor:
    """PDF文件处理器"""

    @classmethod
    def can_process(cls, file_path: Path) -> bool:
        return file_path.suffix.lower() == ".pdf"

    async def process(self, file_path: Path, encoding: str = 'utf-8', **kwargs) -> Dict[str, Any]:
        pdf_text = ""
        metadata = {}

        try:
            # 尝试使用PyPDF2
            from PyPDF2 import PdfReader

            reader = PdfReader(str(file_path))

            # 提取元数据
            if reader.metadata:
                pdf_metadata = {}
                for key, value in reader.metadata.items():
                    if key and value and isinstance(key, str):
                        # 清理键名
                        clean_key = key.lower().replace('/', '_').replace(':', '_')
                        pdf_metadata[clean_key] = str(value)
                metadata["pdf_info"] = pdf_metadata

            # 记录页数
            metadata["page_count"] = len(reader.pages)

            # 提取文本
            text_parts = []
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    text_parts.append(f"--- 第{i + 1}页 ---\n{page_text}")
                else:
                    logger.warning(f"PDF第{i + 1}页未提取到文本，可能需要OCR处理: {file_path.name}")

            pdf_text = "\n\n".join(text_parts)

            # 如果未提取到文本，可能需要OCR
            if not pdf_text.strip():
                logger.warning(f"PDF文件未提取到文本内容，可能是扫描件: {file_path.name}")
                pdf_text = f"[PDF文件: {file_path.name}，共{len(reader.pages)}页，未提取到文本内容]"
                metadata["requires_ocr"] = True

        except ImportError:
            logger.warning("未安装PyPDF2，无法提取PDF文本")
            pdf_text = f"[PDF文件: {file_path.name}]"
            metadata["pdf_support"] = False
        except Exception as e:
            logger.error(f"PDF处理错误: {str(e)}")
            pdf_text = f"[PDF文件处理错误: {file_path.name}]"
            metadata["processing_error"] = str(e)

        return {
            "content": pdf_text,
            "metadata": metadata
        }