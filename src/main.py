#!/usr/bin/env python3
"""
AI资讯日报 - 主程序入口
每天爬取AI相关新闻并发送邮件
"""
import logging
import sys
from datetime import datetime, timedelta
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
from config import get_translation_config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)


def collect_news() -> List[NewsItem]:
    """从各个来源收集新闻并进行 24 小时过滤"""
    all_items: List[NewsItem] = []
    now = datetime.now()
    time_threshold = now - timedelta(hours=24)
    
    # 定义采集函数
    def collect_from_crawler(crawler_instance):
        try:
            items = crawler_instance.safe_crawl()
            # 24小时过滤逻辑
            filtered = []
            for item in items:
                # 如果有发布时间且在24小时内，或者没有发布时间（视作最新）则保留
                if item.pub_date:
                    # 确保是 offset-naive 或处理时区
                    if item.pub_date.replace(tzinfo=None) > time_threshold:
                        filtered.append(item)
                else:
                    filtered.append(item)
            return filtered
        except Exception as e:
            logger.error(f"采集出错: {e}")
            return []

    # 1. Hugging Face Papers
    logger.info("=" * 50)
    logger.info("开始爬取 Hugging Face Papers...")
    all_items.extend(collect_from_crawler(HuggingFaceCrawler()))
    
    # 2. RSS源
    logger.info("=" * 50)
    logger.info("开始爬取RSS源...")
    rss_crawlers = create_all_rss_crawlers()
    for crawler in rss_crawlers:
        all_items.extend(collect_from_crawler(crawler))
    
    # 3. Hacker News
    logger.info("=" * 50)
    logger.info("开始爬取Hacker News...")
    all_items.extend(collect_from_crawler(HackerNewsCrawler()))
    
    # 4. Reddit
    logger.info("=" * 50)
    logger.info("开始爬取Reddit...")
    all_items.extend(collect_from_crawler(RedditCrawler()))
    
    # 5. Twitter/X
    logger.info("=" * 50)
    logger.info("开始爬取 Twitter (via Nitter)...")
    all_items.extend(collect_from_crawler(NitterCrawler()))
    
    # 6. 微信公众号
    logger.info("=" * 50)
    logger.info("开始爬取微信公众号...")
    all_items.extend(collect_from_crawler(WeixinCrawler()))
    
    # 7. 微博热搜
    logger.info("=" * 50)
    logger.info("开始爬取微博热搜...")
    all_items.extend(collect_from_crawler(WeiboCrawler()))
    
    logger.info("=" * 50)
    logger.info(f"共收集 {len(all_items)} 条 24 小时内的原始新闻")
    
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
            logger.info("翻译完成")
        except Exception as e:
            logger.error(f"翻译过程出错，将发送未翻译版本: {e}")
    else:
        logger.warning("翻译未启用或未配置")
    
    return top_items


def send_email(items: List[NewsItem]) -> bool:
    """发送邮件"""
    if not items:
        return False
    
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
        # 1. 收集新闻 (内含24h过滤)
        all_news = collect_news()
        
        if not all_news:
            logger.error("未能获取任何新闻，退出")
            sys.exit(0) # 正常退出，只是今天没新闻
        
        # 2. 处理新闻（含翻译）
        top_news = process_news(all_news, top_n=30)
        
        if not top_news:
            logger.error("处理后没有有效新闻，退出")
            sys.exit(0)
        
        # 3. 预览
        logger.info("=" * 60)
        for i, item in enumerate(top_news, 1):
            title = item.title_zh if item.title_zh else item.title
            logger.info(f"  {i}. [{item.source_name}] {title[:50]}...")
        
        # 4. 发送
        success = send_email(top_news)
        if success:
            logger.info("任务完成！")
            sys.exit(0)
        else:
            sys.exit(1)
            
    except Exception as e:
        logger.exception(f"运行出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
