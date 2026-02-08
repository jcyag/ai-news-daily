"""
Hugging Face Papers 爬虫
爬取 https://huggingface.co/papers 获取每日热门论文
并调用 Arxiv API 获取详细摘要
"""
import sys
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import requests
import feedparser
from bs4 import BeautifulSoup

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from crawlers.base import BaseCrawler, NewsItem

logger = logging.getLogger(__name__)


class HuggingFaceCrawler(BaseCrawler):
    """Hugging Face Papers 爬虫"""
    
    HF_PAPERS_URL = "https://huggingface.co/papers"
    ARXIV_API_URL = "http://export.arxiv.org/api/query"
    
    def __init__(self):
        super().__init__("huggingface", "Hugging Face Papers")
    
    def crawl(self) -> List[NewsItem]:
        """爬取热门论文"""
        # 1. 获取 Hugging Face Papers 页面
        try:
            response = self._make_request(self.HF_PAPERS_URL)
            paper_ids = self._parse_paper_ids(response.text)
        except Exception as e:
            logger.error(f"[Hugging Face] 获取页面失败: {e}")
            return []
            
        if not paper_ids:
            logger.warning("[Hugging Face] 未找到论文ID")
            return []
            
        logger.info(f"[Hugging Face] 发现 {len(paper_ids)} 篇热门论文，正在获取详情...")
        
        # 2. 调用 Arxiv API 获取详情
        return self._fetch_arxiv_details(paper_ids)
    
    def _parse_paper_ids(self, html: str) -> List[str]:
        """解析页面获取 Arxiv ID列表"""
        soup = BeautifulSoup(html, "html.parser")
        ids = []
        
        # 查找所有论文链接
        # 链接格式通常为 /papers/2402.12345
        for link in soup.find_all("a", href=re.compile(r"^/papers/\d+\.\d+")):
            href = link.get("href")
            if href:
                # 提取ID: /papers/2402.12345 -> 2402.12345
                paper_id = href.split("/")[-1]
                if paper_id not in ids:
                    ids.append(paper_id)
        
        # 限制数量，避免请求过大
        return ids[:20]
    
    def _fetch_arxiv_details(self, paper_ids: List[str]) -> List[NewsItem]:
        """批量从 Arxiv API 获取论文详情"""
        if not paper_ids:
            return []
            
        # Arxiv API 支持 id_list 参数，逗号分隔
        id_list = ",".join(paper_ids)
        params = {
            "id_list": id_list,
            "max_results": len(paper_ids),
        }
        
        try:
            response = self._make_request(self.ARXIV_API_URL, params=params)
            feed = feedparser.parse(response.content)
            
            items = []
            for entry in feed.entries:
                item = self._parse_arxiv_entry(entry)
                if item:
                    items.append(item)
            
            return items
            
        except Exception as e:
            logger.error(f"[Hugging Face] Arxiv API 请求失败: {e}")
            return []
    
    def _parse_arxiv_entry(self, entry) -> Optional[NewsItem]:
        """解析 Arxiv 条目"""
        title = entry.get("title", "").replace("\n", " ").strip()
        
        # 摘要通常包含换行，清理一下
        summary = entry.get("summary", "").replace("\n", " ").strip()
        
        # 处理发布时间
        pub_date = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            pub_date = datetime(*entry.published_parsed[:6])
        
        # 作者列表
        authors = [author.get("name") for author in entry.get("authors", [])]
        if authors:
            author_str = ", ".join(authors[:3])
            if len(authors) > 3:
                author_str += " et al."
            summary = f"👤 {author_str}\n\n{summary}"
        
        # 构造 Hugging Face 链接 (比 Arxiv 链接更友好，有讨论区)
        # entry.id 通常是 http://arxiv.org/abs/2402.12345v1
        arxiv_id = entry.get("id", "").split("/abs/")[-1].split("v")[0]
        hf_link = f"https://huggingface.co/papers/{arxiv_id}"
        
        return NewsItem(
            title=title,
            url=hf_link,
            source=self.source_id,
            source_name="Hugging Face Papers",
            pub_date=pub_date,
            summary=summary,
            score=100.0,  # 给热门论文较高的默认分数
        )
