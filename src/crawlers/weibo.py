#!/usr/bin/env python3
"""
微博热搜爬虫
通过今日热榜 (tophub.today) 获取微博热搜
"""
import logging
import re
from datetime import datetime
from typing import List
import requests
from bs4 import BeautifulSoup

from crawlers.base import BaseCrawler, NewsItem

logger = logging.getLogger(__name__)


class WeiboCrawler(BaseCrawler):
    """微博热搜爬虫 - 通过今日热榜获取"""
    
    def __init__(self):
        super().__init__(
            source_id="weibo",
            source_name="微博热搜",
        )
        # 今日热榜微博热搜页面
        self.tophub_url = "https://tophub.today/n/KqndgxeLl9"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
    
    def crawl(self) -> List[NewsItem]:
        """爬取微博热搜"""
        items = []
        
        try:
            items.extend(self._crawl_from_tophub())
        except Exception as e:
            logger.warning(f"从今日热榜获取微博热搜失败: {e}")
        
        # 如果今日热榜失败，尝试备用方案
        if not items:
            try:
                items.extend(self._crawl_from_weibo_api())
            except Exception as e:
                logger.warning(f"从微博API获取热搜失败: {e}")
        
        logger.info(f"微博热搜共获取 {len(items)} 条")
        return items
    
    def _crawl_from_tophub(self) -> List[NewsItem]:
        """从今日热榜获取微博热搜"""
        items = []
        
        logger.info(f"正在从今日热榜获取微博热搜...")
        
        response = requests.get(
            self.tophub_url,
            headers=self.headers,
            timeout=15
        )
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找表格中的热搜条目
        rows = soup.select('table tr')
        
        for row in rows[:50]:  # 取前50行
            try:
                # 查找标题链接
                link = row.select_one('td a')
                if not link:
                    continue
                
                title = link.get_text(strip=True)
                if not title or len(title) < 2:
                    continue
                
                # 跳过广告和无关内容
                if '广告' in title or '推荐' in title:
                    continue
                
                # 获取链接
                href = link.get('href', '')
                if href.startswith('http'):
                    url = href
                else:
                    # 构建微博搜索链接
                    url = f"https://s.weibo.com/weibo?q={requests.utils.quote(title)}"
                
                # 提取热度
                hot_value = 0
                tds = row.select('td')
                if len(tds) >= 3:
                    hot_text = tds[-1].get_text(strip=True)
                    hot_match = re.search(r'([\d.]+)\s*万?', hot_text.replace(',', ''))
                    if hot_match:
                        val = float(hot_match.group(1))
                        if '万' in hot_text:
                            val *= 10000
                        hot_value = int(val)
                
                item = NewsItem(
                    title=title,
                    url=url,
                    source=self.source_id,
                    source_name=self.source_name,
                    pub_date=datetime.now(),
                    summary=f"微博热搜话题",
                    score=hot_value,
                )
                items.append(item)
                
            except Exception as e:
                logger.debug(f"解析微博热搜条目失败: {e}")
                continue
        
        logger.info(f"从今日热榜获取 {len(items)} 条微博热搜")
        return items
    
    def _crawl_from_weibo_api(self) -> List[NewsItem]:
        """备用方案：直接从微博获取热搜"""
        items = []
        
        api_url = "https://weibo.com/ajax/side/hotSearch"
        
        try:
            response = requests.get(
                api_url,
                headers={
                    **self.headers,
                    'Referer': 'https://weibo.com/',
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            realtime = data.get('data', {}).get('realtime', [])
            
            for item_data in realtime[:30]:
                try:
                    word = item_data.get('word', '')
                    if not word:
                        continue
                    
                    url = f"https://s.weibo.com/weibo?q=%23{requests.utils.quote(word)}%23"
                    hot_value = item_data.get('num', 0)
                    
                    item = NewsItem(
                        title=word,
                        url=url,
                        source=self.source_id,
                        source_name=self.source_name,
                        pub_date=datetime.now(),
                        summary=f"微博热搜 - 热度: {hot_value}",
                        score=hot_value,
                    )
                    items.append(item)
                    
                except Exception as e:
                    logger.debug(f"解析微博API条目失败: {e}")
                    continue
            
            logger.info(f"从微博API获取 {len(items)} 条热搜")
            
        except Exception as e:
            logger.warning(f"微博API请求失败: {e}")
        
        return items
