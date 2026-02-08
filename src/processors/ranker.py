"""
新闻排序和选取模块
基于多维度对新闻进行排序，选取Top N
"""
import sys
import logging
from datetime import datetime, timedelta
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
        top_n: int = 10,
        recency_weight: float = 0.3,
        score_weight: float = 0.4,
        source_weight: float = 0.3,
    ):
        """
        初始化排序器
        
        Args:
            top_n: 选取的新闻数量
            recency_weight: 时效性权重
            score_weight: 分数权重(如HN分数、Reddit upvotes)
            source_weight: 来源权重
        """
        self.top_n = top_n
        self.recency_weight = recency_weight
        self.score_weight = score_weight
        self.source_weight = source_weight
        
        # 来源优先级（可调整）
        self.source_priority = {
            "techcrunch": 1.0,
            "theverge": 0.9,
            "hackernews": 0.95,
            "reddit": 0.85,
            "36kr": 0.9,
            "huxiu": 0.85,
            "sogou": 0.5,  # 搜索结果优先级较低
        }
    
    def rank(self, items: List[NewsItem]) -> List[NewsItem]:
        """
        对新闻进行排序
        
        Args:
            items: 新闻列表
            
        Returns:
            排序后的Top N新闻
        """
        if not items:
            return []
        
        # 计算综合分数
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
    
    def _calculate_score(
        self, 
        item: NewsItem, 
        all_items: List[NewsItem]
    ) -> float:
        """计算综合分数"""
        # 时效性分数 (最近24小时内的文章得分更高)
        recency_score = self._recency_score(item.pub_date)
        
        # 原始分数（归一化）
        raw_score = self._normalize_score(item.score, all_items)
        
        # 来源分数
        source_score = self.source_priority.get(item.source, 0.5)
        
        # 加权求和
        final_score = (
            recency_score * self.recency_weight +
            raw_score * self.score_weight +
            source_score * self.source_weight
        )
        
        return final_score
    
    def _recency_score(self, pub_date: Optional[datetime]) -> float:
        """
        计算时效性分数
        
        最近1小时: 1.0
        最近6小时: 0.8
        最近24小时: 0.5
        超过24小时: 0.2
        """
        if not pub_date:
            return 0.3  # 无日期给个中等分数
        
        now = datetime.now()
        
        # 处理时区问题
        if pub_date.tzinfo is not None:
            from datetime import timezone
            now = datetime.now(timezone.utc)
        
        try:
            age = now - pub_date
        except TypeError:
            # 如果时区不匹配，移除时区信息
            pub_date = pub_date.replace(tzinfo=None)
            now = datetime.now()
            age = now - pub_date
        
        if age < timedelta(hours=1):
            return 1.0
        elif age < timedelta(hours=6):
            return 0.8
        elif age < timedelta(hours=24):
            return 0.5
        elif age < timedelta(days=3):
            return 0.3
        else:
            return 0.1
    
    def _normalize_score(
        self, 
        score: float, 
        all_items: List[NewsItem]
    ) -> float:
        """将分数归一化到0-1范围"""
        if score <= 0:
            return 0.0
        
        # 获取所有非零分数
        all_scores = [item.score for item in all_items if item.score > 0]
        
        if not all_scores:
            return 0.0
        
        max_score = max(all_scores)
        if max_score <= 0:
            return 0.0
        
        return min(score / max_score, 1.0)
