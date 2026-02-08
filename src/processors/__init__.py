import sys
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from processors.filter import AIKeywordFilter
from processors.dedup import Deduplicator
from processors.ranker import NewsRanker
from processors.translator import Translator

__all__ = ['AIKeywordFilter', 'Deduplicator', 'NewsRanker', 'Translator']
