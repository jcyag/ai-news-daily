"""
Reddit爬虫
使用官方API获取r/MachineLearning热门帖子
需要配置Reddit API凭据
"""
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from crawlers.base import BaseCrawler, NewsItem
from config import get_reddit_config

logger = logging.getLogger(__name__)


class RedditCrawler(BaseCrawler):
    """Reddit爬虫 - 使用OAuth API"""
    
    OAUTH_URL = "https://oauth.reddit.com"
    TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
    SUBREDDIT = "MachineLearning"
    
    def __init__(self):
        super().__init__("reddit", f"Reddit r/{self.SUBREDDIT}")
        self.reddit_config = get_reddit_config()
        self._access_token = None
    
    def crawl(self) -> List[NewsItem]:
        """爬取Reddit帖子"""
        if not self.reddit_config.is_configured:
            logger.warning("[Reddit] 未配置API凭据，跳过爬取")
            return []
        
        # 获取访问令牌
        if not self._authenticate():
            return []
        
        # 获取热门帖子
        return self._fetch_hot_posts()
    
    def _authenticate(self) -> bool:
        """获取OAuth访问令牌"""
        try:
            auth = (
                self.reddit_config.client_id,
                self.reddit_config.client_secret,
            )
            
            data = {
                "grant_type": "client_credentials",
            }
            
            headers = {
                "User-Agent": self.reddit_config.user_agent,
            }
            
            response = self.session.post(
                self.TOKEN_URL,
                auth=auth,
                data=data,
                headers=headers,
                timeout=self.config.request_timeout,
            )
            response.raise_for_status()
            
            token_data = response.json()
            self._access_token = token_data.get("access_token")
            
            if not self._access_token:
                logger.error("[Reddit] 获取访问令牌失败")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"[Reddit] 认证失败: {e}")
            return False
    
    def _fetch_hot_posts(self) -> List[NewsItem]:
        """获取热门帖子"""
        url = f"{self.OAUTH_URL}/r/{self.SUBREDDIT}/hot"
        
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "User-Agent": self.reddit_config.user_agent,
        }
        
        params = {
            "limit": self.config.max_articles_per_source,
        }
        
        try:
            response = self.session.get(
                url,
                headers=headers,
                params=params,
                timeout=self.config.request_timeout,
            )
            response.raise_for_status()
            
            data = response.json()
            posts = data.get("data", {}).get("children", [])
            
            items = []
            for post in posts:
                item = self._parse_post(post.get("data", {}))
                if item:
                    items.append(item)
            
            return items
            
        except Exception as e:
            logger.error(f"[Reddit] 获取帖子失败: {e}")
            return []
    
    def _parse_post(self, post_data: dict) -> Optional[NewsItem]:
        """解析帖子数据"""
        title = post_data.get("title", "").strip()
        
        if not title:
            return None
        
        # 跳过置顶和删除的帖子
        if post_data.get("stickied") or post_data.get("removed"):
            return None
        
        # 获取URL - 优先使用外部链接
        url = post_data.get("url", "")
        permalink = post_data.get("permalink", "")
        
        # 如果是自帖子，使用Reddit链接
        if post_data.get("is_self") or not url:
            url = f"https://reddit.com{permalink}"
        
        # 解析时间
        pub_date = None
        created_utc = post_data.get("created_utc")
        if created_utc:
            pub_date = datetime.fromtimestamp(created_utc)
        
        # 构建摘要
        summary_parts = []
        
        # 添加flair
        flair = post_data.get("link_flair_text")
        if flair:
            summary_parts.append(f"[{flair}]")
        
        # 添加自帖子内容
        selftext = post_data.get("selftext", "")
        if selftext:
            selftext = selftext[:300].replace("\n", " ").strip()
            summary_parts.append(selftext)
        
        # 添加统计信息
        ups = post_data.get("ups", 0)
        num_comments = post_data.get("num_comments", 0)
        summary_parts.append(f"↑{ups} | {num_comments}评论")
        
        summary = " ".join(summary_parts)
        
        return NewsItem(
            title=title,
            url=url,
            source=self.source_id,
            source_name=self.source_name,
            pub_date=pub_date,
            summary=summary,
            score=float(post_data.get("score", 0)),
        )
