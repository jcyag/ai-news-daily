"""
新闻排序和选取模块
基于多维度对新闻进行排序，选取Top N
"""
import sys
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from crawlers.base import NewsItem

logger = logging.getLogger(__name__)


class NewsRanker:
    """新闻排序器"""
    
    def __init__(
        self,
        top_n: int = 30,
        recency_weight: float = 0.4,
        score_weight: float = 0.3,
        source_weight: float = 0.3,
    ):
        self.top_n = top_n
        self.recency_weight = recency_weight
        self.score_weight = score_weight
        self.source_weight = source_weight
        
        # 来源优先级
        self.source_priority = {
            "huggingface": 1.0,   # 学术源，最高优先级
            "hackernews": 0.95,
            "techcrunch": 0.9,
            "theverge": 0.9,
            "36kr": 0.85,
            "huxiu": 0.85,
            "weixin": 0.8,
            "reddit": 0.75,
            "twitter": 0.7,
            "weibo": 0.65,
        }
    
    def rank(self, items: List[NewsItem]) -> List[NewsItem]:
        if not items:
            return []
        
        scored_items = []
        for item in items:
            final_score = self._calculate_score(item, items)
            scored_items.append((item, final_score))
        
        # 按分数降序排序
        scored_items.sort(key=lambda x: x[1], reverse=True)
        
        # 选取Top N
        result = [item for item, score in scored_items[:self.top_n]]
        logger.info(f"排序完成: 从 {len(items)} 条中选取 Top {len(result)}")
        return result
    
    def _calculate_score(self, item: NewsItem, all_items: List[NewsItem]) -> float:
        # 1. 时效性
        recency_score = self._recency_score(item.pub_date)
        
        # 2. 原始热度分数
        raw_score = self._normalize_score(item.score, all_items)
        
        # 3. 来源权重
        source_score = self.source_priority.get(item.source, 0.5)
        
        # 加权求和
        return (
            recency_score * self.recency_weight +
            raw_score * self.score_weight +
            source_score * self.source_weight
        )
    
    def _recency_score(self, pub_date: Optional[datetime]) -> float:
        """计算时效性分数"""
        now = datetime.now(timezone.utc)
        
        if not pub_date:
            return 0.4
            
        # 确保 pub_date 带有时区
        if pub_date.tzinfo is None:
            pub_date = pub_date.replace(tzinfo=timezone.utc)
        
        try:
            age = now - pub_date
            # 如果时间是未来的（由于时区差错），给最高分
            if age.total_seconds() < 0:
                return 1.0
            
            hours = age.total_seconds() / 3600
            if hours < 1: return 1.0
            if hours < 6: return 0.9
            if hours < 12: return 0.8
            if hours < 24: return 0.7
            if hours < 48: return 0.4
            return 0.1
        except Exception:
            return 0.4
    
    def _normalize_score(self, score: float, all_items: List[NewsItem]) -> float:
        if score <= 0: return 0.0
        all_scores = [i.score for i in all_items if i.score > 0]
        if not all_scores: return 0.0
        max_score = max(all_scores)
        return min(score / max_score, 1.0)
