#!/usr/bin/env python3
"""
AI资讯日报 - 主程序入口
每天爬取AI相关新闻并发送邮件
"""
import logging
import sys
from datetime import datetime, timedelta, timezone
from typing import List

from crawlers import (
    NewsItem,
    RSSCrawler,
    HackerNewsCrawler,
    RedditCrawler,
    HuggingFaceCrawler,
    NitterCrawler,
    WeixinCrawler,
    WeiboCrawler,
)
from crawlers.rss_crawler import create_all_rss_crawlers
from processors import AIKeywordFilter, Deduplicator, NewsRanker, Translator
from notifier import EmailSender
from notifier.subscriber_manager import SubscriberManager
from config import get_translation_config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)


def collect_news() -> List[NewsItem]:
    """从各个来源收集新闻并进行时间过滤"""
    all_items: List[NewsItem] = []
    # 使用带时区的 UTC 时间，确保一致性
    now = datetime.now(timezone.utc)
    # 将过滤窗口放宽到 48 小时，确保有足够的内容，但在排序时会优先最近的
    time_threshold = now - timedelta(hours=48)
    
    def collect_from_crawler(crawler_instance):
        try:
            items = crawler_instance.safe_crawl()
            filtered = []
            for item in items:
                # 统一转为带时区的对比
                pub_date = item.pub_date
                if pub_date:
                    if pub_date.tzinfo is None:
                        pub_date = pub_date.replace(tzinfo=timezone.utc)
                    
                    if pub_date > time_threshold:
                        filtered.append(item)
                else:
                    # 没有时间的新闻通常是热榜即时信息，予以保留
                    filtered.append(item)
            return filtered
        except Exception as e:
            logger.error(f"采集出错: {e}")
            return []

    # 按优先级采集
    sources = [
        ("Hugging Face", HuggingFaceCrawler()),
        ("RSS源", None), # 特殊处理
        ("Hacker News", HackerNewsCrawler()),
        ("Reddit", RedditCrawler()),
        ("Twitter", NitterCrawler()),
        ("微信公众号", WeixinCrawler()),
        ("微博热搜", WeiboCrawler())
    ]

    for name, crawler in sources:
        logger.info("=" * 50)
        logger.info(f"开始爬取 {name}...")
        if name == "RSS源":
            rss_crawlers = create_all_rss_crawlers()
            for rc in rss_crawlers:
                all_items.extend(collect_from_crawler(rc))
        else:
            all_items.extend(collect_from_crawler(crawler))
    
    logger.info("=" * 50)
    logger.info(f"共收集 {len(all_items)} 条 48 小时内的原始新闻")
    
    return all_items


def process_news(items: List[NewsItem], top_n: int = 30) -> List[NewsItem]:
    """处理新闻：过滤、去重、排序、翻译"""
    
    # 1. AI关键词过滤
    logger.info("正在进行AI关键词过滤...")
    ai_filter = AIKeywordFilter()
    filtered_items = ai_filter.filter(items)
    
    if not filtered_items:
        logger.warning("过滤后没有AI相关新闻！")
        return []
    
    # 2. 去重
    logger.info("正在去重...")
    deduplicator = Deduplicator(similarity_threshold=0.7)
    unique_items = deduplicator.deduplicate(filtered_items)
    
    # 3. 排序并选取Top N
    # 现在的 ranker 会考虑时间衰减，越近的新闻分数越高
    logger.info(f"正在排序并选取Top {top_n}...")
    ranker = NewsRanker(top_n=top_n)
    top_items = ranker.rank(unique_items)
    
    # 4. 翻译
    trans_config = get_translation_config()
    if trans_config.enabled and trans_config.is_configured:
        logger.info("=" * 50)
        logger.info("正在翻译新闻...")
        try:
            translator = Translator(trans_config)
            top_items = translator.translate_batch(top_items)
        except Exception as e:
            logger.error(f"翻译过程出错: {e}")
    
    return top_items


def main():
    logger.info("=" * 60)
    logger.info("AI资讯日报 - 开始运行")
    # 0. 检查新订阅
    try:
        sub_manager = SubscriberManager()
        sub_manager.process_all_requests()
    except Exception as e:
        logger.error(f"检查订阅失败: {e}")
    
    try:
        all_news = collect_news()
        if not all_news:
            logger.error("未能获取任何新闻")
            return
        
        top_news = process_news(all_news, top_n=30)
        if not top_news:
            logger.error("处理后没有有效新闻")
            return
        
        sender = EmailSender()
        today = datetime.now().strftime("%Y-%m-%d")
        success = sender.send(top_news, subject=f"AI资讯日报 - {today}")
        
        if success:
            logger.info("任务完成！")
            
    except Exception as e:
        logger.exception(f"运行出错: {e}")


if __name__ == "__main__":
    main()
