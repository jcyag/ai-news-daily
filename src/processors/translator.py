"""
新闻翻译模块 - 优化版
使用 Google Cloud Translation REST API 直接调用，确保兼容性
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
    """新闻翻译器 - 使用 Google Cloud Translation REST API"""
    
    def __init__(self, config: TranslationConfig):
        self.config = config
        self.api_url = "https://translation.googleapis.com/language/translate/v2"
    
    def translate_batch(self, items: List[NewsItem]) -> List[NewsItem]:
        """批量翻译新闻列表"""
        if not self.config.api_key:
            logger.warning("未配置 GOOGLE_TRANSLATE_API_KEY，跳过翻译")
            return items
        
        translated_count = 0
        skipped_count = 0
        
        for item in items:
            try:
                # 智能检测：如果是中文源或标题包含中文，跳过
                if item.source.lower() in CHINESE_SOURCES or self._is_mostly_chinese(item.title):
                    item.is_chinese_source = True
                    skipped_count += 1
                    continue
                
                # 翻译标题
                item.title_zh = self._translate_text(item.title)
                
                # 翻译摘要
                if item.summary:
                    item.summary_zh = self._translate_text(item.summary)
                
                if item.title_zh:
                    translated_count += 1
                    
            except Exception as e:
                logger.error(f"翻译单条新闻失败 [{item.title[:20]}...]: {e}")
        
        logger.info(f"翻译统计: 成功 {translated_count} 条, 跳过 {skipped_count} 条")
        return items
    
    def _translate_text(self, text: str) -> str:
        """调用 REST API 翻译文本"""
        if not text or not text.strip():
            return ""
            
        try:
            params = {
                'q': text,
                'target': 'zh-CN',
                'key': self.config.api_key,
                'format': 'text'  # 保持纯文本格式，避免 HTML 标签干扰
            }
            
            response = requests.get(self.api_url, params=params, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                translated_text = result['data']['translations'][0]['translatedText']
                # 解码 HTML 实体
                return html.unescape(translated_text)
            else:
                logger.error(f"Google 翻译接口错误: {response.status_code} - {response.text}")
                return ""
                
        except Exception as e:
            logger.error(f"请求翻译接口异常: {e}")
            return ""
    
    def _is_mostly_chinese(self, text: str) -> bool:
        """简单判断文本是否包含中文字符"""
        if not text:
            return False
        # 如果包含任何中文字符且占比超过一定程度，认为不需要翻译
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        return chinese_chars > 0 and (chinese_chars / len(text) > 0.2)
