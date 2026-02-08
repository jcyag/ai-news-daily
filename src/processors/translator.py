"""
新闻翻译模块 - 最终兼容版
使用 GET 请求确保 API Key 认证 100% 成功
"""
import logging
import requests
import re
import html
from typing import List
from pathlib import Path
import sys

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from crawlers.base import NewsItem
from config import TranslationConfig, CHINESE_SOURCES

logger = logging.getLogger(__name__)

class Translator:
    def __init__(self, config: TranslationConfig):
        self.config = config
        self.api_url = "https://translation.googleapis.com/language/translate/v2"
        
        if not self.config.api_key:
            logger.error("!!! 错误: GOOGLE_TRANSLATE_API_KEY 环境变量未设置 !!!")
        else:
            logger.info("翻译器初始化成功，准备执行翻译...")
    
    def translate_batch(self, items: List[NewsItem]) -> List[NewsItem]:
        if not self.config.api_key:
            return items
        
        translated_count = 0
        skipped_count = 0
        
        for item in items:
            try:
                # 1. 检查是否已经是中文源
                if item.source.lower() in CHINESE_SOURCES or self._is_mostly_chinese(item.title):
                    item.is_chinese_source = True
                    skipped_count += 1
                    continue
                
                # 2. 执行标题翻译
                title_zh = self._translate_text(item.title)
                if title_zh:
                    item.title_zh = title_zh
                    translated_count += 1
                    logger.info(f"[翻译成功] {item.title[:15]}... -> {title_zh[:15]}...")
                    
                    # 3. 执行摘要翻译
                    if item.summary and len(item.summary) > 5:
                        summary_zh = self._translate_text(item.summary)
                        if summary_zh:
                            item.summary_zh = summary_zh
                
            except Exception as e:
                logger.error(f"处理新闻翻译时发生意外错误: {e}")
        
        logger.info(f"=== 翻译任务总结: 成功 {translated_count} 条, 跳过 {skipped_count} 条 ===")
        return items
    
    def _translate_text(self, text: str) -> str:
        """调用 Google 翻译 API"""
        if not text or not text.strip():
            return ""
            
        try:
            # 移除文本中的 HTML 标签（如果有）
            clean_text = re.sub(r'<[^>]+>', '', text)
            
            params = {
                'q': clean_text,
                'target': 'zh-CN',
                'key': self.config.api_key
            }
            
            response = requests.get(self.api_url, params=params, timeout=15)
            
            if response.status_code == 200:
                result = response.json()
                translated = result['data']['translations'][0]['translatedText']
                # Google 返回的内容可能包含 HTML 实体（如 &quot;），需要解码
                return html.unescape(translated)
            else:
                logger.error(f"Google API 响应错误: {response.status_code} - {response.text}")
                return ""
                
        except Exception as e:
            logger.error(f"请求 Google 翻译 API 异常: {e}")
            return ""
    
    def _is_mostly_chinese(self, text: str) -> bool:
        """判断是否包含中文"""
        if not text:
            return False
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        return chinese_chars > 2
