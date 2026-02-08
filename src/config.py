"""
配置管理模块
从环境变量和本地文件读取配置
"""
import os
from dataclasses import dataclass, field
from typing import List, Dict, Set
from pathlib import Path

@dataclass
class EmailConfig:
    """邮件配置"""
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    username: str = ""
    password: str = ""
    sender: str = ""
    recipients: List[str] = field(default_factory=list)
    
    @classmethod
    def from_env(cls) -> "EmailConfig":
        # 1. 从环境变量获取初始列表
        recipients_str = os.getenv("EMAIL_TO", "")
        recipients = {r.strip() for r in recipients_str.split(",") if r.strip()}
        
        # 2. 从 data/subscribers.txt 获取动态列表
        sub_file = Path(__file__).parent.parent / "data" / "subscribers.txt"
        if sub_file.exists():
            with open(sub_file, "r", encoding="utf-8") as f:
                file_recipients = {line.strip() for line in f if line.strip()}
                recipients.update(file_recipients)
        
        username = os.getenv("EMAIL_USER", "")
        
        return cls(
            smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            username=username,
            password=os.getenv("EMAIL_PASSWORD", ""),
            sender=os.getenv("EMAIL_FROM", username),
            recipients=list(recipients),
        )

@dataclass
class RedditConfig:
    """Reddit API配置"""
    client_id: str = ""
    client_secret: str = ""
    user_agent: str = "AI-News-Daily/1.0"
    
    @classmethod
    def from_env(cls) -> "RedditConfig":
        return cls(
            client_id=os.getenv("REDDIT_CLIENT_ID", ""),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET", ""),
            user_agent=os.getenv("REDDIT_USER_AGENT", "AI-News-Daily/1.0"),
        )
    
    @property
    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

@dataclass
class TranslationConfig:
    """翻译配置"""
    enabled: bool = True
    api_key: str = ""
    project_id: str = ""
    target_language: str = "zh-CN"
    
    @classmethod
    def from_env(cls) -> "TranslationConfig":
        return cls(
            enabled=os.getenv("TRANSLATION_ENABLED", "true").lower() == "true",
            api_key=os.getenv("GOOGLE_TRANSLATE_API_KEY", ""),
            project_id=os.getenv("GOOGLE_PROJECT_ID", ""),
        )
    
    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

@dataclass
class CrawlerConfig:
    """爬虫配置"""
    request_timeout: int = 30
    request_delay: float = 2.0
    max_articles_per_source: int = 50
    user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

NITTER_INSTANCES: List[str] = [
    "https://nitter.poast.org",
    "https://nitter.privacydev.net",
    "https://nitter.moomoo.me",
    "https://nitter.perennialte.ch",
    "https://nitter.it",
    "https://nitter.nl",
    "https://nitter.mint.lgbt",
    "https://nitter.dafrary7.io",
    "https://nitter.rocks",
    "https://nitter.eu",
]

TWITTER_USERS: List[str] = [
    "_akhaliq", "ylecun", "karpathy", "AndrewYNg",
    "OpenAI", "GoogleDeepMind", "AnthropicAI",
    "yan5xu", "YukerX", "antigravity", "Khazix0918",
    "vista8", "bcherny", "jiangydev", "ivanhzhao", "dotey"
]

RSS_SOURCES: Dict[str, Dict] = {
    "36kr": {"name": "36氪", "url": "https://36kr.com/feed", "language": "zh"},
    "huxiu": {"name": "虎嗅", "url": "https://www.huxiu.com/rss/0.xml", "language": "zh"},
    "techcrunch": {"name": "TechCrunch", "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "language": "en"},
    "theverge": {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml", "language": "en"},
}

CHINESE_SOURCES: Set[str] = {'36kr', 'huxiu', 'weibo', 'weixin'}

AI_KEYWORDS: List[str] = [
    "AI", "artificial intelligence", "machine learning", "deep learning",
    "LLM", "GPT", "ChatGPT", "Claude", "Gemini", "Llama", "Mistral",
    "neural network", "transformer", "diffusion", "generative",
    "AGI", "OpenAI", "Anthropic", "Google DeepMind", "Meta AI",
    "NVIDIA", "AI agent", "RAG", "fine-tuning", "RLHF", "reasoning",
    "multimodal", "vision model", "language model", "foundation model",
    "Copilot", "Cursor", "AI coding", "AI assistant",
    "人工智能", "大模型", "机器学习", "深度学习", "神经网络",
    "生成式AI", "智能体", "AI芯片", "算力", "大语言模型",
    "多模态", "AI助手", "AI编程", "智谱", "百川", "文心一言",
    "通义千问", "讯飞星火", "Kimi", "月之暗面",
]

def get_email_config() -> EmailConfig:
    return EmailConfig.from_env()

def get_reddit_config() -> RedditConfig:
    return RedditConfig.from_env()

def get_crawler_config() -> CrawlerConfig:
    return CrawlerConfig()

def get_translation_config() -> TranslationConfig:
    return TranslationConfig.from_env()
