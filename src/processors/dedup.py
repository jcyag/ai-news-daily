"""
新闻去重模块
基于标题相似度去除重复新闻
"""
import sys
import logging
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import List, Tuple

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from crawlers.base import NewsItem

logger = logging.getLogger(__name__)


class Deduplicator:
    """新闻去重器"""
    
    def __init__(self, similarity_threshold: float = 0.7):
        """
        初始化去重器
        
        Args:
            similarity_threshold: 相似度阈值，超过此值视为重复 (0-1)
        """
        self.similarity_threshold = similarity_threshold
    
    def deduplicate(self, items: List[NewsItem]) -> List[NewsItem]:
        """
        对新闻列表去重
        
        策略:
        1. URL完全相同 -> 去重
        2. 标题相似度超过阈值 -> 保留分数更高的
        
        Args:
            items: 新闻列表
            
        Returns:
            去重后的新闻列表
        """
        if not items:
            return []
        
        original_count = len(items)
        
        # 第一步：URL去重
        seen_urls = set()
        url_unique = []
        for item in items:
            normalized_url = self._normalize_url(item.url)
            if normalized_url not in seen_urls:
                seen_urls.add(normalized_url)
                url_unique.append(item)
        
        # 第二步：标题相似度去重
        result = []
        for item in url_unique:
            is_duplicate = False
            normalized_title = self._normalize_title(item.title)
            
            for i, existing in enumerate(result):
                existing_title = self._normalize_title(existing.title)
                similarity = self._similarity(normalized_title, existing_title)
                
                if similarity >= self.similarity_threshold:
                    is_duplicate = True
                    # 保留分数更高的
                    if item.score > existing.score:
                        result[i] = item
                    break
            
            if not is_duplicate:
                result.append(item)
        
        logger.info(
            f"去重: {original_count} -> {len(result)} "
            f"(移除 {original_count - len(result)} 条重复)"
        )
        
        return result
    
    def _normalize_url(self, url: str) -> str:
        """规范化URL用于比较"""
        # 移除协议前缀
        url = re.sub(r'^https?://', '', url)
        # 移除末尾斜杠
        url = url.rstrip('/')
        # 移除www前缀
        url = re.sub(r'^www\.', '', url)
        # 转小写
        return url.lower()
    
    def _normalize_title(self, title: str) -> str:
        """规范化标题用于比较"""
        # 转小写
        title = title.lower()
        # 移除标点符号
        title = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', title)
        # 压缩空白
        title = re.sub(r'\s+', ' ', title)
        return title.strip()
    
    def _similarity(self, s1: str, s2: str) -> float:
        """计算两个字符串的相似度"""
        return SequenceMatcher(None, s1, s2).ratio()
