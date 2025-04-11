"""
提示词模板引擎
使用Jinja2实现模板渲染
"""
from typing import Dict, Any, Optional
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.logging import get_logger

logger = get_logger(__name__)

class TemplateEngine:
    """Jinja2模板引擎封装类"""

    def __init__(self):
        """初始化模板引擎"""
        # 获取提示词模板目录的绝对路径
        template_dir = Path(__file__).parent.parent / "templates"
        
        if not template_dir.exists():
            raise FileNotFoundError(f"模板目录不存在: {template_dir}")
        
        # 创建Jinja2环境
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        logger.info(f"模板引擎初始化成功，模板目录: {template_dir}")
    
    def render(self, template_path: str, variables: Optional[Dict[str, Any]] = None) -> str:
        """
        渲染指定的模板
        
        Args:
            template_path: 模板文件路径，相对于templates目录
            variables: 模板变量
            
        Returns:
            str: 渲染后的文本
        """
        try:
            template = self.env.get_template(template_path)
            result = template.render(**(variables or {}))
            return result
        except Exception as e:
            logger.error(f"模板渲染失败 | 模板: {template_path} | 错误: {str(e)}")
            # 返回错误信息，避免系统崩溃
            return f"[模板渲染错误: {str(e)}]"
    
    def render_string(self, template_string: str, variables: Optional[Dict[str, Any]] = None) -> str:
        """
        渲染模板字符串
        
        Args:
            template_string: 模板字符串
            variables: 模板变量
            
        Returns:
            str: 渲染后的文本
        """
        try:
            template = self.env.from_string(template_string)
            result = template.render(**(variables or {}))
            return result
        except Exception as e:
            logger.error(f"字符串模板渲染失败 | 错误: {str(e)}")
            # 返回错误信息，避免系统崩溃
            return f"[模板渲染错误: {str(e)}]"

# 创建全局模板引擎实例
template_engine = TemplateEngine()