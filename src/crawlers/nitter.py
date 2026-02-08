"""
Nitter (Twitter) 爬虫
通过轮询 Nitter 实例获取 Twitter RSS

注意：由于 X/Twitter 的反爬策略，Nitter 实例经常失效。
此爬虫会尝试多个实例，如果全部失败会优雅降级。
"""
import sys
import logging
import random
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import feedparser

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from crawlers.base import BaseCrawler, NewsItem
from config import NITTER_INSTANCES, TWITTER_USERS

logger = logging.getLogger(__name__)


class NitterCrawler(BaseCrawler):
    """Nitter/Twitter 爬虫"""
    
    def __init__(self):
        super().__init__("twitter", "Twitter (via Nitter)")
        self.instances = NITTER_INSTANCES
        self.users = TWITTER_USERS
    
    def crawl(self) -> List[NewsItem]:
        """爬取所有配置的 Twitter 用户"""
        all_items = []
        
        if not self.instances:
            logger.warning("[Nitter] 没有配置实例，跳过")
            return []
        
        if not self.users:
            logger.warning("[Nitter] 没有配置用户，跳过")
            return []
        
        # 找到一个可用的实例
        working_instance = self._find_working_instance()
        if not working_instance:
            logger.warning("[Nitter] 所有实例均不可用，跳过 Twitter 数据源")
            return []
        
        logger.info(f"[Nitter] 使用实例: {working_instance}")
        
        for user in self.users:
            try:
                items = self._crawl_user(working_instance, user)
                all_items.extend(items)
                self._delay()
            except Exception as e:
                logger.warning(f"[Nitter] 获取 @{user} 失败: {e}")
                continue
            
        return all_items
    
    def _find_working_instance(self) -> Optional[str]:
        """找到一个可用的 Nitter 实例"""
        # 随机打乱实例顺序，负载均衡
        instances = list(self.instances)
        random.shuffle(instances)
        
        for instance in instances:
            try:
                # 尝试访问实例首页
                response = self.session.get(
                    instance,
                    timeout=10,
                    allow_redirects=True,
                )
                if response.status_code == 200:
                    return instance
            except Exception as e:
                logger.debug(f"[Nitter] 实例 {instance} 不可用: {e}")
                continue
        
        return None
    
    def _crawl_user(self, instance: str, username: str) -> List[NewsItem]:
        """爬取单个用户的推文"""
        rss_url = f"{instance}/{username}/rss"
        
        logger.info(f"[Nitter] 获取 @{username}...")
        
        # 使用 feedparser 解析 RSS
        feed = feedparser.parse(
            rss_url,
            agent=self.config.user_agent,
        )
        
        if feed.bozo and not feed.entries:
            raise Exception(f"RSS解析错误: {feed.bozo_exception}")
        
        items = []
        for entry in feed.entries[:5]:  # 每个用户只取最新5条
            item = self._parse_entry(entry, username)
            if item:
                items.append(item)
        
        if items:
            logger.info(f"[Nitter] @{username} 获取 {len(items)} 条推文")
        
        return items
    
    def _parse_entry(self, entry, username: str) -> Optional[NewsItem]:
        """解析单个推文"""
        # Nitter RSS 的 title 通常就是推文内容（截断）
        title = entry.get("title", "").strip()
        link = entry.get("link", "")
        
        if not title:
            return None
        
        # 清理标题中的换行
        title = title.replace("\n", " ").strip()
        
        # 限制标题长度
        if len(title) > 100:
            title = title[:97] + "..."
        
        # 完整内容作为摘要
        description = entry.get("description", "")
        
        # 时间处理
        pub_date = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                pub_date = datetime(*entry.published_parsed[:6])
            except:
                pass
        
        # 转换链接为 Twitter 原链接（可选）
        twitter_link = link
        for instance in self.instances:
            if instance.replace("https://", "") in link:
                twitter_link = link.replace(
                    instance.replace("https://", "").split("/")[0],
                    "twitter.com"
                )
                break
        
        return NewsItem(
            title=f"@{username}: {title}",
            url=twitter_link,
            source=self.source_id,
            source_name=f"Twitter @{username}",
            pub_date=pub_date,
            summary=description[:500] if description else "",
            score=80.0,
        )
