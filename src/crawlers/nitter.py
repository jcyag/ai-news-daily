"""
Twitter/X 爬虫 (通过 Nitter 实例)
增强稳定性与内容相关性
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
import urllib.parse

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
        """爬取关注用户的推文和关键词搜索"""
        all_items = []
        
        # 1. 寻找可用实例
        self.current_instance = self._get_working_instance()
        if not self.current_instance:
            logger.error("无法找到可用的 Nitter 实例，跳过 Twitter 爬取")
            return []
            
        logger.info(f"使用 Nitter 实例: {self.current_instance}")
        
        # 2. 爬取指定大V推文
        users_to_crawl = self.users[:]
        random.shuffle(users_to_crawl)
        
        for user in users_to_crawl[:10]: # 每次随机取10个大V
            user_items = self._crawl_user_with_retry(user)
            all_items.extend(user_items)
            time.sleep(1)
            
        # 3. 搜索AI关键词 (增加内容基数)
        search_keywords = [
            "AI", "LLM", "GPT-4o", "Claude 3.5", "Llama 3", 
            "DeepSeek", "Sora", "Generative AI", "AI Agents"
        ]
        for kw in search_keywords:
            search_items = self._search_with_retry(kw)
            all_items.extend(search_items)
            time.sleep(1)
                
        return all_items
    
    def _get_working_instance(self, exclude: str = None) -> Optional[str]:
        """寻找一个可用的 Nitter 实例"""
        test_instances = [i for i in self.instances if i != exclude]
        random.shuffle(test_instances)
        
        for instance in test_instances:
            try:
                resp = self.session.get(f"{instance}/jack/rss", timeout=8)
                if resp.status_code == 200 and "<rss" in resp.text.lower():
                    return instance
            except Exception:
                continue
        return None

    def _crawl_user_with_retry(self, username: str) -> List[NewsItem]:
        return self._action_with_retry(self._crawl_user_logic, username)

    def _search_with_retry(self, keyword: str) -> List[NewsItem]:
        return self._action_with_retry(self._search_logic, keyword)

    def _action_with_retry(self, func, arg) -> List[NewsItem]:
        max_retries = 2
        for attempt in range(max_retries):
            if not self.current_instance:
                self.current_instance = self._get_working_instance()
                if not self.current_instance: return []
            try:
                return func(self.current_instance, arg)
            except Exception as e:
                logger.warning(f"使用实例 {self.current_instance} 执行失败: {e}")
                old_instance = self.current_instance
                self.current_instance = self._get_working_instance(exclude=old_instance)
        return []

    def _crawl_user_logic(self, instance: str, username: str) -> List[NewsItem]:
        rss_url = f"{instance}/{username}/rss"
        return self._parse_nitter_rss(rss_url, f"Twitter (@{username})")

    def _search_logic(self, instance: str, keyword: str) -> List[NewsItem]:
        encoded_kw = urllib.parse.quote(keyword)
        rss_url = f"{instance}/search/rss?f=tweets&q={encoded_kw}"
        return self._parse_nitter_rss(rss_url, f"Twitter搜索: {keyword}")

    def _parse_nitter_rss(self, rss_url: str, source_name: str) -> List[NewsItem]:
        resp = self.session.get(rss_url, timeout=10)
        resp.raise_for_status()
        if "<rss" not in resp.text.lower():
            raise ValueError("非法的 RSS 内容")
        feed = feedparser.parse(resp.text)
        items = []
        time_threshold = datetime.now() - timedelta(hours=48)
        for entry in feed.entries:
            try:
                pub_date = self._parse_date(entry)
                if pub_date:
                    pub_date_naive = pub_date.replace(tzinfo=None)
                    if pub_date_naive < time_threshold:
                        continue
                title = str(entry.get("title", ""))
                # 移除用户名前缀 (e.g. "ylecun: ...")
                clean_title = re.sub(r'^@?\w+:', '', title).strip()
                if len(clean_title) < 10: continue

                summary = str(entry.get("summary", ""))
                summary = re.sub(r'<[^>]+>', '', summary).strip()

                items.append(NewsItem(
                    title=clean_title[:100],
                    url=str(entry.get("link", "")),
                    source="twitter",
                    source_name=source_name,
                    pub_date=pub_date,
                    summary=summary[:300],
                    score=0.0
                ))
            except Exception: continue
        return items

    def _parse_date(self, entry) -> Optional[datetime]:
        date_str = entry.get("published")
        if not date_str: return None
        try:
            return parsedate_to_datetime(date_str)
        except Exception: return None
