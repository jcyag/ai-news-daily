"""
Reddit爬虫 - RSS版本
无需API凭据即可获取r/MachineLearning和r/ArtificialInteligence热门帖子
"""
import sys
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import feedparser
from bs4 import BeautifulSoup

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from crawlers.base import BaseCrawler, NewsItem

logger = logging.getLogger(__name__)


class RedditCrawler(BaseCrawler):
    """Reddit爬虫 - 使用RSS订阅 (无需API Key)"""
    
    SUBREDDITS = ["MachineLearning", "ArtificialInteligence", "Singularity"]
    
    def __init__(self):
        super().__init__("reddit", "Reddit社区")
    
    def crawl(self) -> List[NewsItem]:
        """爬取Reddit帖子"""
        all_items = []
        
        for sub in self.SUBREDDITS:
            try:
                url = f"https://www.reddit.com/r/{sub}/hot/.rss"
                logger.info(f"正在爬取 Reddit r/{sub} RSS...")
                
                # Reddit RSS 需要设置特定的 User-Agent 否则会返回 429
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
                
                response = self.session.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                
                feed = feedparser.parse(response.text)
                
                for entry in feed.entries[:20]:
                    item = self._parse_entry(entry, sub)
                    if item:
                        all_items.append(item)
                        
            except Exception as e:
                logger.warning(f"爬取 Reddit r/{sub} 失败: {e}")
                continue
                
        return all_items
    
    def _parse_entry(self, entry, subreddit: str) -> Optional[NewsItem]:
        """解析单个RSS条目"""
        title = entry.get("title", "").strip()
        link = entry.get("link", "").strip()
        
        if not title or not link:
            return None
            
        # 解析时间
        pub_date = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            pub_date = datetime(*entry.published_parsed[:6])
            
        # 提取摘要 - Reddit RSS摘要包含HTML内容，主要是发帖人信息
        content_html = entry.get("summary", "") or entry.get("content", [{}])[0].get("value", "")
        summary = self._clean_reddit_html(content_html)
        
        # 提取分数 (如果可能的话，RSS中通常不包含分数)
        score = 0.0
        
        return NewsItem(
            title=title,
            url=link,
            source=self.source_id,
            source_name=f"Reddit r/{subreddit}",
            pub_date=pub_date,
            summary=summary,
            score=score
        )
        
    def _clean_reddit_html(self, html_content: str) -> str:
        """清理Reddit摘要中的HTML"""
        if not html_content:
            return ""
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            # Reddit RSS 摘要通常包含发帖人链接和内容预览
            # 我们只需要正文文本
            # 找到所有的 <td> 标签或者是特定内容
            text = soup.get_text(separator=" ", strip=True)
            # 移除一些常见的 Reddit RSS 噪音
            text = re.sub(r'submitted by.*?to r/.*?\[link\].*?\[comments\]', '', text, flags=re.IGNORECASE)
            text = re.sub(r'\s+', ' ', text).strip()
            return text[:300]
        except Exception:
            return ""
