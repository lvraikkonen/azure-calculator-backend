# app/utils/token_counter.py

import os
import time
from pathlib import Path
from typing import Optional, Dict, Any, Union
from multiprocessing import Pool, cpu_count
from app.core.logging import get_logger

logger = get_logger(__name__)

# 尝试导入各种tokenizer库
try:
    from transformers import AutoTokenizer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("transformers库未安装，将使用估算方法计算token数量")

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    logger.warning("tiktoken库未安装，将使用估算方法计算OpenAI模型token数量")

try:
    from tokenizers import Tokenizer
    TOKENIZERS_AVAILABLE = True
except ImportError:
    TOKENIZERS_AVAILABLE = False
    logger.warning("tokenizers库未安装，无法使用本地tokenizer文件")

# 缓存已加载的tokenizer以提高性能
_TOKENIZER_CACHE = {}

# 本地tokenizer文件路径
LOCAL_TOKENIZER_PATH = Path(__file__).parent.parent / "data" / "tokenizer.json"


class LocalTokenizerManager:
    """本地tokenizer管理器"""

    def __init__(self):
        self._local_tokenizer = None
        self._initialized = False

    def get_local_tokenizer(self):
        """获取本地tokenizer实例"""
        if not self._initialized:
            self._initialize_local_tokenizer()
        return self._local_tokenizer

    def _initialize_local_tokenizer(self):
        """初始化本地tokenizer"""
        self._initialized = True

        if not TOKENIZERS_AVAILABLE:
            logger.warning("tokenizers库不可用，无法加载本地tokenizer")
            return

        if not LOCAL_TOKENIZER_PATH.exists():
            logger.warning(f"本地tokenizer文件不存在: {LOCAL_TOKENIZER_PATH}")
            return

        try:
            self._local_tokenizer = Tokenizer.from_file(str(LOCAL_TOKENIZER_PATH))
            logger.info(f"成功加载本地tokenizer: {LOCAL_TOKENIZER_PATH}")
        except Exception as e:
            logger.error(f"加载本地tokenizer失败: {e}")

# 全局本地tokenizer管理器实例
_local_tokenizer_manager = LocalTokenizerManager()


def get_tokenizer(model_type: str, model_name: str):
    """获取适合特定模型的tokenizer"""
    cache_key = f"{model_type}:{model_name}"
    if cache_key in _TOKENIZER_CACHE:
        return _TOKENIZER_CACHE[cache_key]

    try:
        # 优先使用本地tokenizer（适用于deepseek模型）
        if model_type.lower() == 'deepseek':
            local_tokenizer = _local_tokenizer_manager.get_local_tokenizer()
            if local_tokenizer:
                _TOKENIZER_CACHE[cache_key] = local_tokenizer
                logger.info(f"使用本地tokenizer处理{model_type}/{model_name}")
                return local_tokenizer

            # 回退到transformers tokenizer
            if TRANSFORMERS_AVAILABLE:
                tokenizer_name = "deepseek/deepseek-llm-7b-base"
                tokenizer = AutoTokenizer.from_pretrained(tokenizer_name, trust_remote_code=True)
                _TOKENIZER_CACHE[cache_key] = tokenizer
                return tokenizer

        elif model_type.lower() == 'openai':
            if TIKTOKEN_AVAILABLE:
                encoding_name = "cl100k_base"  # gpt-3.5-turbo, gpt-4默认值
                encoding = tiktoken.get_encoding(encoding_name)
                _TOKENIZER_CACHE[cache_key] = encoding
                return encoding

        # 通用回退方案 - 尝试直接用模型名称加载
        if TRANSFORMERS_AVAILABLE:
            tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
            _TOKENIZER_CACHE[cache_key] = tokenizer
            return tokenizer

    except Exception as e:
        logger.warning(f"加载{model_type}/{model_name}的tokenizer失败: {e}")

    return None


def count_tokens(text: str, model_type: str, model_name: str) -> int:
    """
    准确计算文本的token数量

    Args:
        text: 要计算的文本
        model_type: 模型类型 (openai, deepseek等)
        model_name: 模型名称

    Returns:
        int: token数量
    """
    # 处理空文本
    if not text:
        return 0

    tokenizer = get_tokenizer(model_type, model_name)

    if tokenizer:
        try:
            # 根据tokenizer类型调用相应方法
            if hasattr(tokenizer, 'encode'):
                # 对于本地tokenizer（HuggingFace tokenizers库）
                if hasattr(tokenizer.encode(text), 'ids'):
                    return len(tokenizer.encode(text).ids)
                # 对于tiktoken或transformers tokenizer
                else:
                    return len(tokenizer.encode(text))
            elif hasattr(tokenizer, 'tokenize'):
                return len(tokenizer.tokenize(text))
        except Exception as e:
            logger.warning(f"使用tokenizer计算失败: {e}")

    # 回退到估算方法
    return estimate_tokens(text)


def count_tokens_batch(texts: list[str], model_type: str, model_name: str) -> list[int]:
    """
    批量计算文本的token数量

    Args:
        texts: 要计算的文本列表
        model_type: 模型类型
        model_name: 模型名称

    Returns:
        list[int]: token数量列表
    """
    if not texts:
        return []

    tokenizer = get_tokenizer(model_type, model_name)

    if tokenizer:
        try:
            results = []
            for text in texts:
                if not text:
                    results.append(0)
                    continue

                if hasattr(tokenizer, 'encode'):
                    if hasattr(tokenizer.encode(text), 'ids'):
                        results.append(len(tokenizer.encode(text).ids))
                    else:
                        results.append(len(tokenizer.encode(text)))
                elif hasattr(tokenizer, 'tokenize'):
                    results.append(len(tokenizer.tokenize(text)))
                else:
                    results.append(estimate_tokens(text))

            return results
        except Exception as e:
            logger.warning(f"批量token计算失败: {e}")

    # 回退到估算方法
    return [estimate_tokens(text) for text in texts]


def estimate_tokens(text: str) -> int:
    """
    当没有准确tokenizer时估算token数量

    针对不同语言特点优化的估算方法
    """
    import re

    # 检测文本是否主要是中文
    chinese_char_count = len(re.findall(r'[\u4e00-\u9fff]', text))
    total_length = len(text)

    if chinese_char_count > total_length * 0.3:
        # 中文文本: 每个字符约为一个token
        return total_length
    else:
        # 英文/混合文本: 按词数和标点符号数估算
        words = len(re.findall(r'\b\w+\b', text))
        punctuations = len(re.findall(r'[^\w\s]', text))

        # 优化系数: 英文单词平均约1.3个token
        return int(words * 1.3) + punctuations