"""
基础爬虫类和数据模型
"""
import sys
import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import requests

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import get_crawler_config

logger = logging.getLogger(__name__)


@dataclass
class NewsItem:
    """新闻条目数据模型"""
    title: str
    url: str
    source: str
    source_name: str
    pub_date: Optional[datetime] = None
    summary: str = ""
    score: float = 0.0  # 用于排序的分数
    
    def __post_init__(self):
        # 清理标题和摘要中的空白字符
        self.title = self.title.strip()
        self.summary = self.summary.strip()
        # 截断过长的摘要
        if len(self.summary) > 500:
            self.summary = self.summary[:497] + "..."
    
    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "source_name": self.source_name,
            "pub_date": self.pub_date.isoformat() if self.pub_date else None,
            "summary": self.summary,
            "score": self.score,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "NewsItem":
        pub_date = None
        if data.get("pub_date"):
            pub_date = datetime.fromisoformat(data["pub_date"])
        return cls(
            title=data["title"],
            url=data["url"],
            source=data["source"],
            source_name=data["source_name"],
            pub_date=pub_date,
            summary=data.get("summary", ""),
            score=data.get("score", 0.0),
        )


class BaseCrawler(ABC):
    """爬虫基类"""
    
    def __init__(self, source_id: str, source_name: str):
        self.source_id = source_id
        self.source_name = source_name
        self.config = get_crawler_config()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.config.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })
    
    @abstractmethod
    def crawl(self) -> List[NewsItem]:
        """
        执行爬取，返回新闻列表
        子类必须实现此方法
        """
        pass
    
    def _make_request(self, url: str, **kwargs) -> requests.Response:
        """发起HTTP请求，带有重试和延迟"""
        timeout = kwargs.pop("timeout", self.config.request_timeout)
        
        try:
            response = self.session.get(url, timeout=timeout, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logger.error(f"[{self.source_name}] 请求失败: {url} - {e}")
            raise
    
    def _delay(self):
        """请求间隔延迟"""
        time.sleep(self.config.request_delay)
    
    def safe_crawl(self) -> List[NewsItem]:
        """
        安全的爬取方法，捕获异常并返回空列表
        """
        try:
            logger.info(f"[{self.source_name}] 开始爬取...")
            items = self.crawl()
            logger.info(f"[{self.source_name}] 爬取完成，获取 {len(items)} 条")
            return items
        except Exception as e:
            logger.error(f"[{self.source_name}] 爬取失败: {e}")
            return []
