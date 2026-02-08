"""
新闻翻译模块
使用 Google Cloud Translation API 翻译英文新闻为中文
"""
import sys
import logging
import re
from pathlib import Path
from typing import List

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from crawlers.base import NewsItem
from config import TranslationConfig, CHINESE_SOURCES

logger = logging.getLogger(__name__)


class Translator:
    """新闻翻译器 - 使用 Google Cloud Translation API"""
    
    def __init__(self, config: TranslationConfig):
        self.config = config
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """初始化 Google Translate 客户端"""
        if not self.config.is_configured:
            logger.warning("翻译 API 未配置，跳过初始化")
            return
        
        try:
            from google.cloud import translate_v2 as translate
            
            # 使用 API Key 方式认证
            self.client = translate.Client(
                target_language=self.config.target_language,
                credentials=None,
            )
            # 设置 API Key
            self.client._connection.API_KEY = self.config.api_key
            
            logger.info("Google Translate 客户端初始化成功")
            
        except ImportError:
            logger.error("未安装 google-cloud-translate，请运行: pip install google-cloud-translate")
            self.client = None
        except Exception as e:
            logger.error(f"Google Translate 初始化失败: {e}")
            self.client = None
    
    def translate_batch(self, items: List[NewsItem]) -> List[NewsItem]:
        """
        批量翻译新闻列表
        
        Args:
            items: 新闻列表
            
        Returns:
            翻译后的新闻列表（失败时保留原文）
        """
        if not self.client:
            logger.warning("翻译客户端未初始化，返回原始新闻")
            return items
        
        translated_count = 0
        skipped_count = 0
        failed_count = 0
        
        for item in items:
            try:
                # 检查是否中文源
                if self._is_chinese_source(item):
                    item.is_chinese_source = True
                    skipped_count += 1
                    continue
                
                # 翻译标题
                if item.title and not item.title_zh:
                    item.title_zh = self._translate_text(item.title)
                
                # 翻译摘要
                if item.summary and not item.summary_zh:
                    item.summary_zh = self._translate_text(item.summary)
                
                if item.title_zh or item.summary_zh:
                    translated_count += 1
                    
            except Exception as e:
                logger.warning(f"翻译失败 [{item.title[:30]}...]: {e}")
                failed_count += 1
                # 继续处理下一条，不影响整体流程
        
        logger.info(f"翻译统计: 成功 {translated_count}, 跳过中文 {skipped_count}, 失败 {failed_count}")
        return items
    
    def translate_item(self, item: NewsItem) -> NewsItem:
        """
        翻译单条新闻
        
        Args:
            item: 新闻条目
            
        Returns:
            翻译后的新闻条目
        """
        # 检查是否中文源
        if self._is_chinese_source(item):
            item.is_chinese_source = True
            logger.debug(f"跳过中文源: {item.source_name}")
            return item
        
        # 翻译标题
        if item.title:
            item.title_zh = self._translate_text(item.title)
        
        # 翻译摘要
        if item.summary:
            item.summary_zh = self._translate_text(item.summary)
        
        return item
    
    def _is_chinese_source(self, item: NewsItem) -> bool:
        """
        判断是否为中文源
        
        Args:
            item: 新闻条目
            
        Returns:
            是否为中文源
        """
        source_lower = item.source.lower()
        
        # 检查是否在中文源列表中
        if source_lower in CHINESE_SOURCES:
            return True
        
        # 额外检查：标题是否主要是中文字符
        if self._is_mostly_chinese(item.title):
            return True
        
        return False
    
    def _is_mostly_chinese(self, text: str) -> bool:
        """
        检查文本是否主要是中文
        
        Args:
            text: 文本
            
        Returns:
            是否主要是中文
        """
        if not text:
            return False
        
        # 统计中文字符数量
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        total_chars = len(re.findall(r'\w', text))
        
        if total_chars == 0:
            return False
        
        # 如果中文字符占比超过 50%，认为是中文
        return chinese_chars / total_chars > 0.5
    
    def _translate_text(self, text: str) -> str:
        """
        翻译文本
        
        Args:
            text: 待翻译文本
            
        Returns:
            翻译后的文本，失败时返回空字符串
        """
        if not text or not text.strip():
            return ""
        
        if not self.client:
            return ""
        
        try:
            # 如果文本已经是中文，直接返回空
            if self._is_mostly_chinese(text):
                logger.debug("文本已是中文，跳过翻译")
                return ""
            
            # 调用 Google Translate API
            result = self.client.translate(
                text,
                target_language=self.config.target_language,
                format_='text'
            )
            
            translated_text = result.get('translatedText', '')
            
            # 解码 HTML 实体（Google Translate 有时会返回 HTML 编码）
            if translated_text:
                import html
                translated_text = html.unescape(translated_text)
            
            return translated_text
            
        except Exception as e:
            logger.warning(f"翻译文本失败: {e}")
            return ""


def create_translator() -> Translator:
    """创建翻译器实例的工厂函数"""
    from config import get_translation_config
    return Translator(get_translation_config())
