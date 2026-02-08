"""
AI关键词过滤器
过滤出与AI相关的新闻
"""
import sys
import logging
import re
from pathlib import Path
from typing import List, Optional, Set

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from crawlers.base import NewsItem
from config import AI_KEYWORDS

logger = logging.getLogger(__name__)


class AIKeywordFilter:
    """AI关键词过滤器"""
    
    def __init__(self, keywords: Optional[List[str]] = None):
        """
        初始化过滤器
        
        Args:
            keywords: 关键词列表，默认使用配置中的AI_KEYWORDS
        """
        self.keywords = keywords or AI_KEYWORDS
        
        # 预编译正则表达式以提高性能
        # 对于英文关键词，使用单词边界匹配
        # 对于中文关键词，直接匹配
        self._patterns = []
        for kw in self.keywords:
            if self._is_ascii(kw):
                # 英文关键词，使用单词边界（忽略大小写）
                pattern = re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE)
            else:
                # 中文关键词，直接匹配
                pattern = re.compile(re.escape(kw), re.IGNORECASE)
            self._patterns.append((kw, pattern))
    
    @staticmethod
    def _is_ascii(text: str) -> bool:
        """检查是否为纯ASCII字符"""
        return all(ord(c) < 128 for c in text)
    
    def matches(self, item: NewsItem) -> bool:
        """
        检查新闻是否匹配AI关键词
        
        Args:
            item: 新闻条目
            
        Returns:
            是否匹配
        """
        text = f"{item.title} {item.summary}".lower()
        
        for kw, pattern in self._patterns:
            if pattern.search(text):
                return True
        
        return False
    
    def filter(self, items: List[NewsItem]) -> List[NewsItem]:
        """
        过滤新闻列表，只保留AI相关的
        
        Args:
            items: 新闻列表
            
        Returns:
            过滤后的新闻列表
        """
        original_count = len(items)
        filtered = [item for item in items if self.matches(item)]
        
        logger.info(
            f"关键词过滤: {original_count} -> {len(filtered)} "
            f"(过滤掉 {original_count - len(filtered)} 条)"
        )
        
        return filtered
    
    def get_matched_keywords(self, item: NewsItem) -> Set[str]:
        """
        获取新闻匹配到的关键词列表
        
        Args:
            item: 新闻条目
            
        Returns:
            匹配到的关键词集合
        """
        text = f"{item.title} {item.summary}"
        matched = set()
        
        for kw, pattern in self._patterns:
            if pattern.search(text):
                matched.add(kw)
        
        return matched
