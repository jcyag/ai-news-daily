"""
Twitter/X 爬虫 (通过 Nitter 实例)
由于 Twitter 官方 API 限制，使用 Nitter 实例的 RSS 订阅作为替代
"""
import logging
import random
import sys
import time
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
    
    def crawl(self) -> List[NewsItem]:
        """爬取关注用户的推文"""
        all_items = []
        
        # 随机打乱用户顺序，分摊压力
        users_to_crawl = self.users[:]
        random.shuffle(users_to_crawl)
        
        # 选一个可用的 Nitter 实例
        instance = self._get_working_instance()
        if not instance:
            logger.error("无法找到可用的 Nitter 实例，跳过 Twitter 爬取")
            return []
            
        logger.info(f"使用 Nitter 实例: {instance}")
        
        for user in users_to_crawl:
            try:
                user_items = self._crawl_user(instance, user)
                all_items.extend(user_items)
                # 稍微延迟，避免被实例封禁
                time.sleep(1)
            except Exception as e:
                logger.warning(f"爬取用户 @{user} 失败: {e}")
                continue
                
        return all_items
    
    def _get_working_instance(self) -> Optional[str]:
        """寻找一个可用的 Nitter 实例"""
        test_instances = self.instances[:]
        random.shuffle(test_instances)
        
        for instance in test_instances:
            try:
                # 尝试访问一个知名账号确认实例存活
                resp = self.session.get(f"{instance}/jack/rss", timeout=5)
                if resp.status_code == 200:
                    return instance
            except Exception:
                continue
        return None

    def _crawl_user(self, instance: str, username: str) -> List[NewsItem]:
        """爬取单个用户的 RSS 订阅"""
        rss_url = f"{instance}/{username}/rss"
        feed = feedparser.parse(rss_url)
        
        items = []
        time_threshold = datetime.now() - timedelta(hours=24)
        
        for entry in feed.entries:
            try:
                # 1. 严格的时间过滤
                pub_date = self._parse_date(entry)
                if pub_date:
                    # 处理时区或 naïve datetime
                    pub_date_naive = pub_date.replace(tzinfo=None)
                    if pub_date_naive < time_threshold:
                        continue # 超过24小时，跳过

                title = entry.get("title", "")
                # 清理推文标题 (Nitter 会在标题加上用户名)
                clean_title = re.sub(r'^@?\w+:', '', title).strip()
                
                # 如果是转发(RT)，可以根据需要过滤或保留
                is_rt = title.startswith("RT by") or "re-tweeted" in title.lower()
                
                item = NewsItem(
                    title=f"@{username}: {clean_title[:100]}",
                    url=entry.get("link", ""),
                    source=self.source_id,
                    source_name=f"Twitter (@{username})",
                    pub_date=pub_date,
                    summary=entry.get("summary", ""),
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
