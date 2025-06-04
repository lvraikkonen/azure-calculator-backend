# app/services/token_billing/cache_manager.py

import asyncio
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Tuple, Union
from dataclasses import dataclass, asdict
from uuid import UUID
import hashlib

from app.core.logging import get_logger
from app.utils.token_counter import count_tokens, count_tokens_batch

logger = get_logger(__name__)


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: datetime
    expires_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    def access(self):
        """记录访问"""
        self.access_count += 1
        self.last_accessed = datetime.now(timezone.utc)


class TokenCountCache:
    """Token计数缓存管理器"""
    
    def __init__(self, max_size: int = 10000, default_ttl: int = 3600):
        """
        初始化缓存管理器
        
        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认TTL（秒）
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, CacheEntry] = {}
        self.logger = logger
        
        # 统计信息
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'size': 0
        }
    
    def _generate_key(self, text: str, model_type: str, model_name: str) -> str:
        """生成缓存键"""
        # 使用文本内容的哈希值作为键，避免键过长
        content = f"{text}:{model_type}:{model_name}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _evict_expired(self):
        """清理过期条目"""
        expired_keys = [
            key for key, entry in self.cache.items() 
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            del self.cache[key]
            self.stats['evictions'] += 1
        
        self.stats['size'] = len(self.cache)
    
    def _evict_lru(self):
        """LRU清理"""
        if len(self.cache) <= self.max_size:
            return
        
        # 按最后访问时间排序，清理最久未访问的条目
        sorted_entries = sorted(
            self.cache.items(),
            key=lambda x: x[1].last_accessed or x[1].created_at
        )
        
        # 清理超出限制的条目
        excess_count = len(self.cache) - self.max_size
        for i in range(excess_count):
            key = sorted_entries[i][0]
            del self.cache[key]
            self.stats['evictions'] += 1
        
        self.stats['size'] = len(self.cache)
    
    def get(self, text: str, model_type: str, model_name: str) -> Optional[int]:
        """
        获取缓存的token数量
        
        Args:
            text: 文本内容
            model_type: 模型类型
            model_name: 模型名称
            
        Returns:
            Optional[int]: 缓存的token数量，如果不存在则返回None
        """
        key = self._generate_key(text, model_type, model_name)
        
        # 清理过期条目
        self._evict_expired()
        
        if key in self.cache:
            entry = self.cache[key]
            if not entry.is_expired():
                entry.access()
                self.stats['hits'] += 1
                return entry.value
            else:
                del self.cache[key]
                self.stats['evictions'] += 1
        
        self.stats['misses'] += 1
        return None
    
    def set(self, text: str, model_type: str, model_name: str, token_count: int, ttl: Optional[int] = None):
        """
        设置缓存
        
        Args:
            text: 文本内容
            model_type: 模型类型
            model_name: 模型名称
            token_count: token数量
            ttl: 生存时间（秒），为None则使用默认TTL
        """
        key = self._generate_key(text, model_type, model_name)
        
        # 计算过期时间
        expires_at = None
        if ttl is not None or self.default_ttl > 0:
            ttl_seconds = ttl if ttl is not None else self.default_ttl
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        
        # 创建缓存条目
        entry = CacheEntry(
            key=key,
            value=token_count,
            created_at=datetime.now(timezone.utc),
            expires_at=expires_at
        )
        
        self.cache[key] = entry
        self.stats['size'] = len(self.cache)
        
        # 清理策略
        self._evict_expired()
        self._evict_lru()
    
    def clear(self):
        """清空缓存"""
        self.cache.clear()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'size': 0
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = self.stats['hits'] / total_requests if total_requests > 0 else 0
        
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'hit_rate': round(hit_rate, 4),
            'evictions': self.stats['evictions'],
            'default_ttl': self.default_ttl
        }


class BatchTokenCounter:
    """批量Token计数器（带缓存优化）"""
    
    def __init__(self, cache_manager: TokenCountCache = None):
        """
        初始化批量计数器
        
        Args:
            cache_manager: 缓存管理器，为None则创建默认实例
        """
        self.cache = cache_manager or TokenCountCache()
        self.logger = logger
    
    async def count_tokens_cached(self, text: str, model_type: str, model_name: str) -> int:
        """
        带缓存的token计数
        
        Args:
            text: 文本内容
            model_type: 模型类型
            model_name: 模型名称
            
        Returns:
            int: token数量
        """
        # 尝试从缓存获取
        cached_count = self.cache.get(text, model_type, model_name)
        if cached_count is not None:
            return cached_count
        
        # 缓存未命中，执行实际计数
        try:
            token_count = count_tokens(text, model_type, model_name)
            
            # 存入缓存
            self.cache.set(text, model_type, model_name, token_count)
            
            return token_count
            
        except Exception as e:
            self.logger.error(f"Token计数失败: {str(e)}", exc_info=True)
            return 0
    
    async def count_tokens_batch_cached(self, texts: List[str], model_type: str, model_name: str) -> List[int]:
        """
        批量Token计数（带缓存优化）
        
        Args:
            texts: 文本列表
            model_type: 模型类型
            model_name: 模型名称
            
        Returns:
            List[int]: token数量列表
        """
        results = []
        uncached_texts = []
        uncached_indices = []
        
        # 检查缓存
        for i, text in enumerate(texts):
            cached_count = self.cache.get(text, model_type, model_name)
            if cached_count is not None:
                results.append(cached_count)
            else:
                results.append(None)  # 占位符
                uncached_texts.append(text)
                uncached_indices.append(i)
        
        # 批量计算未缓存的文本
        if uncached_texts:
            try:
                uncached_counts = count_tokens_batch(uncached_texts, model_type, model_name)
                
                # 更新结果和缓存
                for idx, count in zip(uncached_indices, uncached_counts):
                    results[idx] = count
                    self.cache.set(texts[idx], model_type, model_name, count)
                    
            except Exception as e:
                self.logger.error(f"批量Token计数失败: {str(e)}", exc_info=True)
                # 对于失败的情况，使用0填充
                for idx in uncached_indices:
                    results[idx] = 0
        
        return results
    
    async def precompute_common_texts(self, common_texts: List[Tuple[str, str, str]]):
        """
        预计算常用文本的token数量
        
        Args:
            common_texts: 常用文本列表，每个元素为(text, model_type, model_name)
        """
        self.logger.info(f"开始预计算 {len(common_texts)} 个常用文本的token数量")
        
        for text, model_type, model_name in common_texts:
            try:
                # 检查是否已缓存
                if self.cache.get(text, model_type, model_name) is None:
                    # 计算并缓存
                    token_count = count_tokens(text, model_type, model_name)
                    self.cache.set(text, model_type, model_name, token_count, ttl=7200)  # 2小时TTL
                    
            except Exception as e:
                self.logger.error(f"预计算token数量失败: {str(e)}", exc_info=True)
        
        self.logger.info("常用文本token数量预计算完成")


class PerformanceMetrics:
    """性能指标收集器"""
    
    def __init__(self):
        self.metrics = {
            'token_count_operations': [],
            'cache_operations': [],
            'database_operations': [],
            'api_requests': []
        }
        self.logger = logger
    
    def record_token_count_operation(self, text_length: int, token_count: int, 
                                   duration: float, model_type: str, cached: bool = False):
        """记录token计数操作"""
        self.metrics['token_count_operations'].append({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'text_length': text_length,
            'token_count': token_count,
            'duration_ms': duration * 1000,
            'model_type': model_type,
            'cached': cached,
            'tokens_per_second': token_count / duration if duration > 0 else 0
        })
        
        # 保持最近1000条记录
        if len(self.metrics['token_count_operations']) > 1000:
            self.metrics['token_count_operations'] = self.metrics['token_count_operations'][-1000:]
    
    def record_cache_operation(self, operation: str, hit: bool, duration: float):
        """记录缓存操作"""
        self.metrics['cache_operations'].append({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'operation': operation,
            'hit': hit,
            'duration_ms': duration * 1000
        })
        
        # 保持最近1000条记录
        if len(self.metrics['cache_operations']) > 1000:
            self.metrics['cache_operations'] = self.metrics['cache_operations'][-1000:]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        token_ops = self.metrics['token_count_operations']
        cache_ops = self.metrics['cache_operations']
        
        summary = {
            'token_operations': {
                'total_count': len(token_ops),
                'avg_duration_ms': 0,
                'avg_tokens_per_second': 0,
                'cache_hit_rate': 0
            },
            'cache_operations': {
                'total_count': len(cache_ops),
                'hit_rate': 0,
                'avg_duration_ms': 0
            }
        }
        
        # Token操作统计
        if token_ops:
            summary['token_operations']['avg_duration_ms'] = sum(op['duration_ms'] for op in token_ops) / len(token_ops)
            summary['token_operations']['avg_tokens_per_second'] = sum(op['tokens_per_second'] for op in token_ops) / len(token_ops)
            cached_ops = [op for op in token_ops if op['cached']]
            summary['token_operations']['cache_hit_rate'] = len(cached_ops) / len(token_ops)
        
        # 缓存操作统计
        if cache_ops:
            summary['cache_operations']['avg_duration_ms'] = sum(op['duration_ms'] for op in cache_ops) / len(cache_ops)
            hit_ops = [op for op in cache_ops if op['hit']]
            summary['cache_operations']['hit_rate'] = len(hit_ops) / len(cache_ops)
        
        return summary


# 全局实例
_global_cache_manager: Optional[TokenCountCache] = None
_global_batch_counter: Optional[BatchTokenCounter] = None
_global_performance_metrics: Optional[PerformanceMetrics] = None


def get_global_cache_manager() -> TokenCountCache:
    """获取全局缓存管理器"""
    global _global_cache_manager
    if _global_cache_manager is None:
        _global_cache_manager = TokenCountCache()
    return _global_cache_manager


def get_global_batch_counter() -> BatchTokenCounter:
    """获取全局批量计数器"""
    global _global_batch_counter
    if _global_batch_counter is None:
        _global_batch_counter = BatchTokenCounter(get_global_cache_manager())
    return _global_batch_counter


def get_global_performance_metrics() -> PerformanceMetrics:
    """获取全局性能指标收集器"""
    global _global_performance_metrics
    if _global_performance_metrics is None:
        _global_performance_metrics = PerformanceMetrics()
    return _global_performance_metrics


async def optimized_count_tokens(text: str, model_type: str, model_name: str) -> int:
    """
    优化的token计数函数（带缓存和性能监控）
    
    Args:
        text: 文本内容
        model_type: 模型类型
        model_name: 模型名称
        
    Returns:
        int: token数量
    """
    start_time = time.time()
    
    try:
        batch_counter = get_global_batch_counter()
        metrics = get_global_performance_metrics()
        
        # 执行计数
        token_count = await batch_counter.count_tokens_cached(text, model_type, model_name)
        
        # 记录性能指标
        duration = time.time() - start_time
        cached = batch_counter.cache.get(text, model_type, model_name) is not None
        
        metrics.record_token_count_operation(
            text_length=len(text),
            token_count=token_count,
            duration=duration,
            model_type=model_type,
            cached=cached
        )
        
        return token_count
        
    except Exception as e:
        logger.error(f"优化token计数失败: {str(e)}", exc_info=True)
        return 0


async def optimized_count_tokens_batch(texts: List[str], model_type: str, model_name: str) -> List[int]:
    """
    优化的批量token计数函数（带缓存和性能监控）
    
    Args:
        texts: 文本列表
        model_type: 模型类型
        model_name: 模型名称
        
    Returns:
        List[int]: token数量列表
    """
    start_time = time.time()
    
    try:
        batch_counter = get_global_batch_counter()
        metrics = get_global_performance_metrics()
        
        # 执行批量计数
        token_counts = await batch_counter.count_tokens_batch_cached(texts, model_type, model_name)
        
        # 记录性能指标
        duration = time.time() - start_time
        total_tokens = sum(token_counts)
        total_length = sum(len(text) for text in texts)
        
        metrics.record_token_count_operation(
            text_length=total_length,
            token_count=total_tokens,
            duration=duration,
            model_type=model_type,
            cached=False  # 批量操作的缓存状态较复杂，这里简化处理
        )
        
        return token_counts
        
    except Exception as e:
        logger.error(f"优化批量token计数失败: {str(e)}", exc_info=True)
        return [0] * len(texts)
