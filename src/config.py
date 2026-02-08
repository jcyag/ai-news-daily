"""
配置管理模块
从环境变量读取敏感配置，提供默认值
"""
import os
from dataclasses import dataclass, field
from typing import List, Dict


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
        recipients_str = os.getenv("EMAIL_TO", "")
        recipients = [r.strip() for r in recipients_str.split(",") if r.strip()]
        
        username = os.getenv("EMAIL_USER", "")
        
        return cls(
            smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            username=username,
            password=os.getenv("EMAIL_PASSWORD", ""),
            sender=os.getenv("EMAIL_FROM", username),
            recipients=recipients,
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
class CrawlerConfig:
    """爬虫配置"""
    request_timeout: int = 30
    request_delay: float = 2.0  # 请求间隔(秒)
    max_articles_per_source: int = 50
    user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )


# Nitter实例列表 (用于X/Twitter爬取)
# 由于Nitter实例经常失效，配置多个备用
NITTER_INSTANCES: List[str] = [
    "https://nitter.poast.org",
    "https://nitter.privacydev.net",
    "https://nitter.net",
    "https://nitter.cz",
]

# X/Twitter 关注列表 (用户名)
TWITTER_USERS: List[str] = [
    # AI领域大V
    "_akhaliq",        # AK (Hugging Face) - AI论文速递
    "ylecun",          # Yann LeCun - Meta首席AI科学家
    "karpathy",        # Andrej Karpathy - 前Tesla/OpenAI
    "AndrewYNg",       # 吴恩达
    
    # 官方账号
    "OpenAI",          # OpenAI官方
    "GoogleDeepMind",  # DeepMind官方
    "AnthropicAI",     # Anthropic官方
    
    # 用户自定义关注
    "yan5xu",          # 用户添加
    "YukerX",          # 用户添加
    "antigravity",     # 用户添加
    "Khazix0918",      # 用户添加
    "vista8",          # 用户添加
    "bcherny",         # 用户添加
    "jiangydev",       # 用户添加
    "ivanhzhao",       # 用户添加
    "dotey",           # 宝玉 - AI/翻译
]

# RSS源配置
RSS_SOURCES: Dict[str, Dict] = {
    "36kr": {
        "name": "36氪",
        "url": "https://36kr.com/feed",
        "language": "zh",
    },
    "huxiu": {
        "name": "虎嗅",
        "url": "https://www.huxiu.com/rss/0.xml",
        "language": "zh",
    },
    "techcrunch": {
        "name": "TechCrunch",
        "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "language": "en",
    },
    "theverge": {
        "name": "The Verge",
        "url": "https://www.theverge.com/rss/index.xml",
        "language": "en",
    },
}

# AI相关关键词
AI_KEYWORDS: List[str] = [
    # 英文关键词
    "AI", "artificial intelligence", "machine learning", "deep learning",
    "LLM", "GPT", "ChatGPT", "Claude", "Gemini", "Llama", "Mistral",
    "neural network", "transformer", "diffusion", "generative",
    "AGI", "OpenAI", "Anthropic", "Google DeepMind", "Meta AI",
    "NVIDIA", "AI agent", "RAG", "fine-tuning", "RLHF", "reasoning",
    "multimodal", "vision model", "language model", "foundation model",
    "Copilot", "Cursor", "AI coding", "AI assistant",
    # 中文关键词
    "人工智能", "大模型", "机器学习", "深度学习", "神经网络",
    "生成式AI", "智能体", "AI芯片", "算力", "大语言模型",
    "多模态", "AI助手", "AI编程", "智谱", "百川", "文心一言",
    "通义千问", "讯飞星火", "Kimi", "月之暗面",
]

# 获取配置实例
def get_email_config() -> EmailConfig:
    return EmailConfig.from_env()

def get_reddit_config() -> RedditConfig:
    return RedditConfig.from_env()

def get_crawler_config() -> CrawlerConfig:
    return CrawlerConfig()
