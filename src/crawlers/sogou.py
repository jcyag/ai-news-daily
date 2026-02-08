"""
搜狗搜索爬虫
注意：搜狗有强反爬机制，此爬虫可能不稳定
仅用于个人学习研究目的
"""
import sys
import logging
import re
import random
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote_plus, urljoin

from bs4 import BeautifulSoup

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from crawlers.base import BaseCrawler, NewsItem

logger = logging.getLogger(__name__)


class SogouCrawler(BaseCrawler):
    """搜狗搜索爬虫"""
    
    SEARCH_URL = "https://www.sogou.com/web"
    
    # 多个User-Agent轮换
    USER_AGENTS = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    ]
    
    def __init__(self, query: str = "AI人工智能 最新消息"):
        super().__init__("sogou", "搜狗搜索")
        self.query = query
        # 更新请求头，模拟真实浏览器
        self.session.headers.update({
            "User-Agent": random.choice(self.USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        })
    
    def crawl(self) -> List[NewsItem]:
        """爬取搜狗搜索结果"""
        logger.warning(
            "[搜狗搜索] 注意：搜狗有强反爬机制，爬取可能失败。"
            "建议配置代理或使用其他数据源。"
        )
        
        items = []
        
        # 搜索多个关键词组合
        queries = [
            "AI人工智能 最新",
            "大模型 新闻",
            "ChatGPT GPT 最新动态",
        ]
        
        for query in queries:
            try:
                self._delay()  # 请求间隔
                query_items = self._search(query)
                items.extend(query_items)
            except Exception as e:
                logger.error(f"[搜狗搜索] 查询'{query}'失败: {e}")
                continue
        
        # 去重
        seen_urls = set()
        unique_items = []
        for item in items:
            if item.url not in seen_urls:
                seen_urls.add(item.url)
                unique_items.append(item)
        
        return unique_items[:self.config.max_articles_per_source]
    
    def _search(self, query: str) -> List[NewsItem]:
        """执行单次搜索"""
        params = {
            "query": query,
            "ie": "utf8",
            "tfr": "all",  # 全部时间
            "_ast": "",
            "_asf": "",
            "w": "01029901",
            "p": "40040100",
            "dp": "1",
        }
        
        try:
            # 先访问主页获取cookies
            self.session.get("https://www.sogou.com/", timeout=10)
            self._delay()
            
            response = self._make_request(
                self.SEARCH_URL,
                params=params,
            )
            
            return self._parse_results(response.text)
            
        except Exception as e:
            logger.error(f"[搜狗搜索] 请求失败: {e}")
            return []
    
    def _parse_results(self, html: str) -> List[NewsItem]:
        """解析搜索结果页面"""
        items = []
        
        try:
            soup = BeautifulSoup(html, "html.parser")
            
            # 检查是否需要验证码
            if "验证码" in html or "captcha" in html.lower():
                logger.warning("[搜狗搜索] 触发验证码，暂停爬取")
                return []
            
            # 搜索结果容器
            results = soup.select(".vrwrap, .rb")
            
            if not results:
                # 尝试其他选择器
                results = soup.select("[class*='result']")
            
            for result in results:
                item = self._parse_result_item(result)
                if item:
                    items.append(item)
            
            logger.info(f"[搜狗搜索] 解析到 {len(items)} 条结果")
            
        except Exception as e:
            logger.error(f"[搜狗搜索] 解析页面失败: {e}")
        
        return items
    
    def _parse_result_item(self, element) -> Optional[NewsItem]:
        """解析单个搜索结果"""
        try:
            # 提取标题和链接
            title_elem = element.select_one("h3 a, .vr-title a, .pt a")
            if not title_elem:
                return None
            
            title = title_elem.get_text(strip=True)
            url = title_elem.get("href", "")
            
            if not title or not url:
                return None
            
            # 处理搜狗的跳转链接
            if url.startswith("/link"):
                url = urljoin("https://www.sogou.com", url)
            
            # 提取摘要
            summary_elem = element.select_one(".space-txt, .str-text, .str_info, .ft")
            summary = ""
            if summary_elem:
                summary = summary_elem.get_text(strip=True)
            
            # 提取来源和时间
            source_elem = element.select_one(".news-from, .citeurl, .fb")
            source_text = ""
            if source_elem:
                source_text = source_elem.get_text(strip=True)
            
            # 添加来源信息到摘要
            if source_text and summary:
                summary = f"{summary} - {source_text}"
            elif source_text:
                summary = source_text
            
            return NewsItem(
                title=title,
                url=url,
                source=self.source_id,
                source_name=f"搜狗搜索",
                pub_date=datetime.now(),  # 搜索结果无法获取准确时间
                summary=summary,
            )
            
        except Exception as e:
            logger.debug(f"[搜狗搜索] 解析结果项失败: {e}")
            return None
