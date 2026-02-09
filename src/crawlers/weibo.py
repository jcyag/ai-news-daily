#!/usr/bin/env python3
"""
微博爬虫 - 增强版
1. 爬取微博热搜
2. 搜索AI关键词获取相关动态
"""
import logging
import re
from datetime import datetime
from typing import List, Optional
import requests
from bs4 import BeautifulSoup
import urllib.parse

from crawlers.base import BaseCrawler, NewsItem

logger = logging.getLogger(__name__)


class WeiboCrawler(BaseCrawler):
    """微博爬虫"""
    
    def __init__(self):
        super().__init__(
            source_id="weibo",
            source_name="微博",
        )
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
    
    def crawl(self) -> List[NewsItem]:
        """爬取微博内容"""
        items = []
        
        # 1. 爬取热搜
        try:
            items.extend(self._crawl_hot_search())
        except Exception as e:
            logger.warning(f"爬取微博热搜失败: {e}")
            
        # 2. 搜索AI关键词 (增加内容相关性)
        try:
            items.extend(self._search_weibo("人工智能"))
            items.extend(self._search_weibo("AI大模型"))
        except Exception as e:
            logger.warning(f"搜索微博关键词失败: {e}")
            
        logger.info(f"微博共获取 {len(items)} 条内容")
        return items
    
    def _crawl_hot_search(self) -> List[NewsItem]:
        """从今日热榜获取微博热搜"""
        url = "https://tophub.today/n/KqndgxeLl9"
        items = []
        
        response = requests.get(url, headers=self.headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        rows = soup.select('table tr')
        
        for row in rows[:50]:
            try:
                link = row.select_one('td a')
                if not link: continue
                
                title = link.get_text(strip=True)
                if not title or len(title) < 2: continue
                if '广告' in title or '推荐' in title: continue
                
                href = link.get('href', '')
                if href.startswith('http'):
                    target_url = href
                else:
                    target_url = f"https://s.weibo.com/weibo?q={urllib.parse.quote(title)}"
                
                # 提取分数
                score = 0.0
                tds = row.select('td')
                if len(tds) >= 3:
                    hot_text = tds[-1].get_text(strip=True)
                    match = re.search(r'([\d.]+)\s*万?', hot_text)
                    if match:
                        val = float(match.group(1))
                        score = val * 10000 if '万' in hot_text else val
                
                items.append(NewsItem(
                    title=title,
                    url=target_url,
                    source=self.source_id,
                    source_name="微博热搜",
                    pub_date=datetime.now(),
                    summary="微博热搜话题",
                    score=score
                ))
            except Exception: continue
        return items

    def _search_weibo(self, keyword: str) -> List[NewsItem]:
        """直接搜索微博获取相关推文"""
        encoded_kw = urllib.parse.quote(keyword)
        url = f"https://s.weibo.com/weibo?q={encoded_kw}&xsort=hot"
        items = []
        
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 微博搜索结果的卡片
            cards = soup.select('div.card-wrap')
            for card in cards:
                content_node = card.select_one('p.txt')
                if not content_node: continue
                
                content = content_node.get_text(strip=True)
                # 截取标题
                title = content[:50] + "..." if len(content) > 50 else content
                
                # 查找链接
                link_node = card.select_one('div.from a')
                if not link_node or not link_node.get('href'): continue
                target_url = "https:" + link_node.get('href') if link_node.get('href').startswith('//') else link_node.get('href')
                
                items.append(NewsItem(
                    title=title,
                    url=target_url,
                    source=self.source_id,
                    source_name=f"微博搜索: {keyword}",
                    pub_date=datetime.now(),
                    summary=content[:200],
                    score=0.0
                ))
        except Exception as e:
            logger.debug(f"搜索微博 '{keyword}' 失败: {e}")
            
        return items
