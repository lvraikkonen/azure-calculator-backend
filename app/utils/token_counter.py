# app/utils/token_counter.py

import logging
from typing import Optional, Dict, Any
from app.core.logging import get_logger

logger = get_logger(__name__)

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

# 缓存已加载的tokenizer以提高性能
_TOKENIZER_CACHE = {}


def get_tokenizer(model_type: str, model_name: str):
    """获取适合特定模型的tokenizer"""
    if not TRANSFORMERS_AVAILABLE:
        return None

    cache_key = f"{model_type}:{model_name}"
    if cache_key in _TOKENIZER_CACHE:
        return _TOKENIZER_CACHE[cache_key]

    try:
        if model_type.lower() == 'openai':
            if TIKTOKEN_AVAILABLE:
                encoding_name = "cl100k_base"  # gpt-3.5-turbo, gpt-4默认值
                encoding = tiktoken.get_encoding(encoding_name)
                _TOKENIZER_CACHE[cache_key] = encoding
                return encoding

        elif model_type.lower() == 'deepseek':
            # Deepseek使用基于LLaMA的tokenizer
            tokenizer_name = "deepseek/deepseek-llm-7b-base"
            tokenizer = AutoTokenizer.from_pretrained(tokenizer_name, trust_remote_code=True)
            _TOKENIZER_CACHE[cache_key] = tokenizer
            return tokenizer

        # 通用回退方案 - 尝试直接用模型名称加载
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
                return len(tokenizer.encode(text))
            elif hasattr(tokenizer, 'tokenize'):
                return len(tokenizer.tokenize(text))
        except Exception as e:
            logger.warning(f"使用tokenizer计算失败: {e}")

    # 回退到估算方法
    return estimate_tokens(text)


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