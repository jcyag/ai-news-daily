"""
新闻翻译模块 - 增强诊断版
使用 Google Cloud Translation REST API (POST)
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
        
        # 诊断日志
        if not self.config.api_key:
            logger.error("!!! 翻译配置错误: 未检测到 GOOGLE_TRANSLATE_API_KEY !!!")
        else:
            masked_key = self.config.api_key[:4] + "*" * 10 + self.config.api_key[-4:]
            logger.info(f"翻译器初始化成功，使用 Key: {masked_key}")
    
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
                
                # 2. 执行翻译
                title_zh = self._translate_text(item.title)
                if title_zh:
                    item.title_zh = title_zh
                    translated_count += 1
                    
                    # 摘要有内容才翻译
                    if item.summary and len(item.summary) > 5:
                        item.summary_zh = self._translate_text(item.summary)
                
            except Exception as e:
                logger.error(f"处理翻译时发生异常: {e}")
        
        logger.info(f"翻译任务结束: 成功 {translated_count} 条, 跳过 {skipped_count} 条")
        return items
    
    def _translate_text(self, text: str) -> str:
        if not text or not text.strip():
            return ""
            
        try:
            # 使用 POST 更加稳健
            data = {
                'q': text,
                'target': 'zh-CN',
                'format': 'text'
            }
            # Key 作为 URL 参数
            url = f"{self.api_url}?key={self.config.api_key}"
            
            response = requests.post(url, json=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                translated = result['data']['translations'][0]['translatedText']
                return html.unescape(translated)
            else:
                logger.error(f"Google API 返回错误: {response.status_code} - {response.text}")
                return ""
                
        except Exception as e:
            logger.error(f"请求 Google 翻译异常: {e}")
            return ""
    
    def _is_mostly_chinese(self, text: str) -> bool:
        if not text:
            return False
        # 匹配中文字符
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        # 如果中文字符超过 2 个，通常就不需要再翻译标题了
        return chinese_chars > 2
