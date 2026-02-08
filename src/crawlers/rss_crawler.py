"""
RSS通用爬虫
支持36氪、虎嗅、TechCrunch、The Verge等RSS源
"""
import sys
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
from email.utils import parsedate_to_datetime

import feedparser
from bs4 import BeautifulSoup

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from crawlers.base import BaseCrawler, NewsItem
from config import RSS_SOURCES

logger = logging.getLogger(__name__)


class RSSCrawler(BaseCrawler):
    """RSS源爬虫"""
    
    def __init__(self, source_id: str):
        source_config = RSS_SOURCES.get(source_id)
        if not source_config:
            raise ValueError(f"未知的RSS源: {source_id}")
        
        super().__init__(source_id, source_config["name"])
        self.url = source_config["url"]
        self.language = source_config.get("language", "en")
    
    def crawl(self) -> List[NewsItem]:
        """爬取RSS源"""
        feed = feedparser.parse(
            self.url,
            agent=self.config.user_agent,
        )
        
        if feed.bozo and feed.bozo_exception:
            logger.warning(f"[{self.source_name}] RSS解析警告: {feed.bozo_exception}")
        
        items = []
        for entry in feed.entries[:self.config.max_articles_per_source]:
            try:
                item = self._parse_entry(entry)
                if item:
                    items.append(item)
            except Exception as e:
                logger.warning(f"[{self.source_name}] 解析条目失败: {e}")
                continue
        
        return items
    
    def _parse_entry(self, entry) -> Optional[NewsItem]:
        """解析单个RSS条目"""
        # 1. 预解析日期，检查是否在24小时内
        pub_date = self._parse_date(entry)
        if pub_date:
            now = datetime.now(pub_date.tzinfo) if pub_date.tzinfo else datetime.now()
            if now - pub_date > timedelta(hours=24):
                return None # 超过24小时，直接跳过
        
        title = entry.get("title", "").strip()
        link = entry.get("link", "").strip()
        
        if not title or not link:
            return None
        
        # 2. 解析摘要 - 只有时间符合才进行昂贵的 HTML 清理
        summary = self._clean_html(
            entry.get("summary", "") or 
            entry.get("description", "") or
            entry.get("content", [{}])[0].get("value", "")
        )
        
        return NewsItem(
            title=title,
            url=link,
            source=self.source_id,
            source_name=self.source_name,
            pub_date=pub_date,
            summary=summary,
        )
    
    def _parse_date(self, entry) -> Optional[datetime]:
        """解析日期"""
        date_str = (
            entry.get("published") or 
            entry.get("updated") or 
            entry.get("created")
        )
        
        if not date_str:
            return None
        
        try:
            return parsedate_to_datetime(date_str)
        except (ValueError, TypeError):
            pass
        
        try:
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                return datetime(*entry.published_parsed[:6])
            if hasattr(entry, "updated_parsed") and entry.updated_parsed:
                return datetime(*entry.updated_parsed[:6])
        except (ValueError, TypeError):
            pass
        
        return None
    
    def _clean_html(self, html_content: str) -> str:
        """清理HTML标签"""
        if not html_content:
            return ""
        
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            for tag in soup(["script", "style"]):
                tag.decompose()
            text = soup.get_text(separator=" ", strip=True)
            text = re.sub(r"\s+", " ", text)
            return text.strip()
        except Exception:
            text = re.sub(r"<[^>]+>", " ", html_content)
            text = re.sub(r"\s+", " ", text)
            return text.strip()


def create_all_rss_crawlers() -> List[RSSCrawler]:
    """创建所有RSS爬虫实例"""
    crawlers = []
    for source_id in RSS_SOURCES:
        try:
            crawler = RSSCrawler(source_id)
            crawlers.append(crawler)
        except Exception as e:
            logger.error(f"创建RSS爬虫失败 [{source_id}]: {e}")
    return crawlers
