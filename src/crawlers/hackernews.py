"""
Hacker News API爬虫
使用官方Firebase API获取热门AI相关文章
"""
import sys
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from crawlers.base import BaseCrawler, NewsItem

logger = logging.getLogger(__name__)


class HackerNewsCrawler(BaseCrawler):
    """Hacker News爬虫"""
    
    API_BASE = "https://hacker-news.firebaseio.com/v0"
    
    def __init__(self):
        super().__init__("hackernews", "Hacker News")
    
    def crawl(self) -> List[NewsItem]:
        """爬取Hacker News热门文章"""
        # 获取热门故事ID列表
        top_stories_url = f"{self.API_BASE}/topstories.json"
        response = self._make_request(top_stories_url)
        story_ids = response.json()
        
        # 只取前100个进行处理
        story_ids = story_ids[:100]
        
        # 并发获取故事详情
        items = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                executor.submit(self._fetch_story, story_id): story_id
                for story_id in story_ids
            }
            
            for future in as_completed(futures):
                try:
                    item = future.result()
                    if item:
                        items.append(item)
                except Exception as e:
                    logger.debug(f"获取故事详情失败: {e}")
        
        # 按分数排序
        items.sort(key=lambda x: x.score, reverse=True)
        
        return items[:self.config.max_articles_per_source]
    
    def _fetch_story(self, story_id: int) -> Optional[NewsItem]:
        """获取单个故事详情"""
        url = f"{self.API_BASE}/item/{story_id}.json"
        
        try:
            response = self._make_request(url)
            data = response.json()
            
            if not data or data.get("type") != "story":
                return None
            
            title = data.get("title", "")
            story_url = data.get("url", "")
            
            # 如果没有外部URL，使用HN讨论页面
            if not story_url:
                story_url = f"https://news.ycombinator.com/item?id={story_id}"
            
            if not title:
                return None
            
            # 解析时间戳
            pub_date = None
            if data.get("time"):
                pub_date = datetime.fromtimestamp(data["time"])
            
            # 构建摘要
            summary = ""
            if data.get("text"):
                summary = data["text"][:500]
            
            # 添加评论数信息
            descendants = data.get("descendants", 0)
            if descendants:
                if summary:
                    summary += f" ({descendants} 条评论)"
                else:
                    summary = f"{descendants} 条评论"
            
            return NewsItem(
                title=title,
                url=story_url,
                source=self.source_id,
                source_name=self.source_name,
                pub_date=pub_date,
                summary=summary,
                score=float(data.get("score", 0)),
            )
            
        except Exception as e:
            logger.debug(f"解析故事 {story_id} 失败: {e}")
            return None
