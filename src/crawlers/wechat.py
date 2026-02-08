"""
微信公众号爬虫
通过今日热榜 (tophub.today) 获取微信热门文章
"""
import sys
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from bs4 import BeautifulSoup

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from crawlers.base import BaseCrawler, NewsItem

logger = logging.getLogger(__name__)


class WeixinCrawler(BaseCrawler):
    """微信公众号爬虫 - 通过今日热榜获取"""
    
    # 今日热榜微信相关榜单
    TOPHUB_WECHAT_URLS = {
        "wechat_hot": {
            "name": "微信热文",
            "url": "https://tophub.today/n/WnBe01o371",
        },
        "wechat_tech": {
            "name": "微信科技",
            "url": "https://tophub.today/n/KqndgxeLl9",
        },
    }
    
    def __init__(self):
        super().__init__("wechat", "微信公众号")
        # 更新请求头，模拟真实浏览器
        self.session.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0",
        })
    
    def crawl(self) -> List[NewsItem]:
        """爬取微信热门文章"""
        all_items = []
        
        for source_id, source_config in self.TOPHUB_WECHAT_URLS.items():
            try:
                logger.info(f"[微信] 爬取 {source_config['name']}...")
                items = self._crawl_tophub(source_config["url"], source_config["name"])
                all_items.extend(items)
                self._delay()
            except Exception as e:
                logger.warning(f"[微信] 爬取 {source_config['name']} 失败: {e}")
                continue
        
        # 去重（同一篇文章可能出现在多个榜单）
        seen_titles = set()
        unique_items = []
        for item in all_items:
            if item.title not in seen_titles:
                seen_titles.add(item.title)
                unique_items.append(item)
        
        return unique_items
    
    def _crawl_tophub(self, url: str, source_name: str) -> List[NewsItem]:
        """爬取今日热榜的单个榜单"""
        try:
            response = self._make_request(url)
            return self._parse_tophub_page(response.text, source_name)
        except Exception as e:
            logger.error(f"[微信] 请求失败: {url} - {e}")
            return []
    
    def _parse_tophub_page(self, html: str, source_name: str) -> List[NewsItem]:
        """解析今日热榜页面"""
        items = []
        
        try:
            soup = BeautifulSoup(html, "html.parser")
            
            # 今日热榜的文章列表通常在 table 或 特定容器中
            # 根据实际页面结构解析
            
            # 方法1: 查找所有带有链接的标题项
            # 今日热榜的结构可能是: <tr><td>序号</td><td><a href="">标题</a></td></tr>
            rows = soup.select("table tr, .item, .nano-content tr")
            
            for row in rows:
                try:
                    # 查找标题链接
                    link = row.select_one("a[href*='mp.weixin.qq.com'], a[href*='tophub.today/link'], td:nth-child(2) a, .t a")
                    if not link:
                        continue
                    
                    title = link.get_text(strip=True)
                    href = link.get("href", "")
                    
                    if not title or len(title) < 5:
                        continue
                    
                    # 处理链接（今日热榜可能是跳转链接）
                    if href.startswith("/link"):
                        href = f"https://tophub.today{href}"
                    
                    # 查找热度信息
                    hot_elem = row.select_one(".r, .heat, td:last-child")
                    hot_text = hot_elem.get_text(strip=True) if hot_elem else ""
                    
                    # 构建摘要
                    summary = f"来源: {source_name}"
                    if hot_text:
                        summary += f" | 热度: {hot_text}"
                    
                    items.append(NewsItem(
                        title=title,
                        url=href,
                        source=self.source_id,
                        source_name=f"微信 ({source_name})",
                        pub_date=datetime.now(),
                        summary=summary,
                        score=70.0,  # 微信热文给予中等分数
                    ))
                    
                except Exception as e:
                    logger.debug(f"[微信] 解析行失败: {e}")
                    continue
            
            # 如果上面方法没找到，尝试备用解析方式
            if not items:
                items = self._parse_tophub_alternative(soup, source_name)
            
            logger.info(f"[微信] {source_name} 解析到 {len(items)} 条")
            
        except Exception as e:
            logger.error(f"[微信] 解析页面失败: {e}")
        
        return items[:20]  # 限制数量
    
    def _parse_tophub_alternative(self, soup: BeautifulSoup, source_name: str) -> List[NewsItem]:
        """备用解析方法 - 适应不同的页面结构"""
        items = []
        
        # 方法2: 查找所有 a 标签，过滤出可能是文章的链接
        all_links = soup.find_all("a", href=True)
        
        for link in all_links:
            href = link.get("href", "")
            title = link.get_text(strip=True)
            
            # 过滤条件
            if not title or len(title) < 10 or len(title) > 100:
                continue
            
            # 只保留可能是文章的链接
            if "/link" in href or "mp.weixin.qq.com" in href:
                if href.startswith("/link"):
                    href = f"https://tophub.today{href}"
                
                items.append(NewsItem(
                    title=title,
                    url=href,
                    source=self.source_id,
                    source_name=f"微信 ({source_name})",
                    pub_date=datetime.now(),
                    summary=f"来源: {source_name}",
                    score=70.0,
                ))
        
        return items
