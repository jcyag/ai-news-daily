#!/usr/bin/env python3
"""
AI资讯日报 - 主程序入口
每天爬取AI相关新闻并发送邮件
"""
import logging
import sys
from datetime import datetime
from typing import List

from crawlers import (
    NewsItem,
    RSSCrawler,
    HackerNewsCrawler,
    RedditCrawler,
    SogouCrawler,
    HuggingFaceCrawler,
    NitterCrawler,
    WeixinCrawler,
)
from crawlers.rss_crawler import create_all_rss_crawlers
from processors import AIKeywordFilter, Deduplicator, NewsRanker
from notifier import EmailSender

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)


def collect_news() -> List[NewsItem]:
    """从各个来源收集新闻"""
    all_items: List[NewsItem] = []
    
    # 1. Hugging Face Papers (高质量学术源，优先)
    logger.info("=" * 50)
    logger.info("开始爬取 Hugging Face Papers...")
    hf_crawler = HuggingFaceCrawler()
    items = hf_crawler.safe_crawl()
    all_items.extend(items)
    
    # 2. RSS源爬取 (36氪, 虎嗅, TechCrunch, The Verge)
    logger.info("=" * 50)
    logger.info("开始爬取RSS源...")
    rss_crawlers = create_all_rss_crawlers()
    for crawler in rss_crawlers:
        items = crawler.safe_crawl()
        all_items.extend(items)
    
    # 3. Hacker News
    logger.info("=" * 50)
    logger.info("开始爬取Hacker News...")
    hn_crawler = HackerNewsCrawler()
    items = hn_crawler.safe_crawl()
    all_items.extend(items)
    
    # 4. Reddit
    logger.info("=" * 50)
    logger.info("开始爬取Reddit...")
    reddit_crawler = RedditCrawler()
    items = reddit_crawler.safe_crawl()
    all_items.extend(items)
    
    # 5. Twitter/X (via Nitter, 可能不稳定)
    logger.info("=" * 50)
    logger.info("开始爬取 Twitter (via Nitter)...")
    nitter_crawler = NitterCrawler()
    items = nitter_crawler.safe_crawl()
    all_items.extend(items)
    
    # 6. 微信公众号 (via 今日热榜)
    logger.info("=" * 50)
    logger.info("开始爬取微信公众号...")
    wechat_crawler = WeixinCrawler()
    items = wechat_crawler.safe_crawl()
    all_items.extend(items)
    
    # 7. 搜狗搜索 (可能失败，但会尝试)
    logger.info("=" * 50)
    logger.info("开始爬取搜狗搜索...")
    sogou_crawler = SogouCrawler()
    items = sogou_crawler.safe_crawl()
    all_items.extend(items)
    
    logger.info("=" * 50)
    logger.info(f"共收集 {len(all_items)} 条原始新闻")
    
    return all_items


def process_news(items: List[NewsItem], top_n: int = 10) -> List[NewsItem]:
    """处理新闻：过滤、去重、排序"""
    
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
    logger.info(f"正在排序并选取Top {top_n}...")
    ranker = NewsRanker(top_n=top_n)
    top_items = ranker.rank(unique_items)
    
    return top_items


def send_email(items: List[NewsItem]) -> bool:
    """发送邮件"""
    if not items:
        logger.warning("没有新闻可发送")
        return False
    
    logger.info("正在发送邮件...")
    sender = EmailSender()
    
    today = datetime.now().strftime("%Y-%m-%d")
    subject = f"AI资讯日报 - {today}"
    
    return sender.send(items, subject=subject)


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("AI资讯日报 - 开始运行")
    logger.info(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    try:
        # 1. 收集新闻
        all_news = collect_news()
        
        if not all_news:
            logger.error("未能获取任何新闻，退出")
            sys.exit(1)
        
        # 2. 处理新闻
        top_news = process_news(all_news, top_n=10)
        
        if not top_news:
            logger.error("处理后没有有效新闻，退出")
            sys.exit(1)
        
        # 3. 打印结果预览
        logger.info("=" * 60)
        logger.info(f"最终选出 {len(top_news)} 条新闻:")
        for i, item in enumerate(top_news, 1):
            logger.info(f"  {i}. [{item.source_name}] {item.title[:50]}...")
        
        # 4. 发送邮件
        logger.info("=" * 60)
        success = send_email(top_news)
        
        if success:
            logger.info("=" * 60)
            logger.info("任务完成！邮件已发送")
            sys.exit(0)
        else:
            logger.error("邮件发送失败")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("用户中断")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"运行出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
