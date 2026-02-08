"""
Twitter/X 爬虫 (通过 Nitter 实例)
由于 Twitter 官方 API 限制，使用 Nitter 实例的 RSS 订阅作为替代
"""
import logging
import random
import sys
import time
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
from email.utils import parsedate_to_datetime

import feedparser

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from crawlers.base import BaseCrawler, NewsItem
from config import NITTER_INSTANCES, TWITTER_USERS

logger = logging.getLogger(__name__)


class NitterCrawler(BaseCrawler):
    """Twitter 爬虫 - 通过 Nitter 获取"""
    
    def __init__(self):
        super().__init__("twitter", "Twitter/X")
        self.users = TWITTER_USERS
        self.instances = NITTER_INSTANCES
        self.current_instance = None
    
    def crawl(self) -> List[NewsItem]:
        """爬取关注用户的推文"""
        all_items = []
        
        # 随机打乱用户顺序
        users_to_crawl = self.users[:]
        random.shuffle(users_to_crawl)
        
        # 尝试获取一个初始实例
        self.current_instance = self._get_working_instance()
        
        for user in users_to_crawl:
            user_items = self._crawl_user_with_retry(user)
            all_items.extend(user_items)
            time.sleep(1) # 避免频率过快
                
        return all_items
    
    def _get_working_instance(self, exclude: str = None) -> Optional[str]:
        """寻找一个可用的 Nitter 实例"""
        test_instances = [i for i in self.instances if i != exclude]
        random.shuffle(test_instances)
        
        for instance in test_instances:
            try:
                # 尝试访问知名账号确认实例存活且返回正确的 RSS
                resp = self.session.get(f"{instance}/jack/rss", timeout=8)
                if resp.status_code == 200 and "<rss" in resp.text.lower():
                    return instance
            except Exception:
                continue
        return None

    def _crawl_user_with_retry(self, username: str) -> List[NewsItem]:
        """尝试爬取单个用户，如果失败则换实例重试"""
        max_retries = 3
        for attempt in range(max_retries):
            if not self.current_instance:
                self.current_instance = self._get_working_instance()
                if not self.current_instance:
                    return []

            try:
                items = self._crawl_user_logic(self.current_instance, username)
                return items
            except Exception as e:
                logger.warning(f"使用实例 {self.current_instance} 爬取 @{username} 失败: {e}")
                # 标记当前实例失效，更换实例
                old_instance = self.current_instance
                self.current_instance = self._get_working_instance(exclude=old_instance)
                if not self.current_instance:
                    break
        return []

    def _crawl_user_logic(self, instance: str, username: str) -> List[NewsItem]:
        """爬取逻辑实现"""
        rss_url = f"{instance}/{username}/rss"
        # 先手动获取文本，检查是否是合法的 XML
        resp = self.session.get(rss_url, timeout=10)
        resp.raise_for_status()
        
        if "<rss" not in resp.text.lower():
            raise ValueError("返回的内容不是有效的 RSS XML")

        feed = feedparser.parse(resp.text)
        if feed.bozo:
            raise ValueError(f"RSS 解析错误: {feed.bozo_exception}")

        items = []
        time_threshold = datetime.now() - timedelta(hours=24)
        
        for entry in feed.entries:
            try:
                # 时间过滤
                pub_date = self._parse_date(entry)
                if pub_date:
                    pub_date_naive = pub_date.replace(tzinfo=None)
                    if pub_date_naive < time_threshold:
                        continue

                title = entry.get("title", "")
                # 移除用户名前缀
                clean_title = re.sub(r'^@?\w+:', '', title).strip()
                
                # Nitter 摘要通常包含完整推文
                summary = entry.get("summary", "")
                # 简单清理摘要中的 HTML
                summary = re.sub(r'<[^>]+>', '', summary).strip()

                item = NewsItem(
                    title=f"@{username}: {clean_title[:100]}",
                    url=entry.get("link", ""),
                    source=self.source_id,
                    source_name=f"Twitter (@{username})",
                    pub_date=pub_date,
                    summary=summary,
                )
                items.append(item)
            except Exception:
                continue
        return items

    def _parse_date(self, entry) -> Optional[datetime]:
        """解析日期"""
        date_str = entry.get("published")
        if not date_str:
            return None
        try:
            return parsedate_to_datetime(date_str)
        except Exception:
            return None
