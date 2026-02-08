"""
邮件发送模块
使用SMTP发送HTML格式的邮件
"""
import sys
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate
from pathlib import Path
from typing import List, Optional

from jinja2 import Environment, FileSystemLoader

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from crawlers.base import NewsItem
from config import get_email_config, EmailConfig

logger = logging.getLogger(__name__)

# 获取模板目录
TEMPLATE_DIR = Path(__file__).parent.parent.parent / "templates"


class EmailSender:
    """邮件发送器"""
    
    def __init__(self, config: Optional[EmailConfig] = None):
        """
        初始化邮件发送器
        
        Args:
            config: 邮件配置，默认从环境变量读取
        """
        self.config = config or get_email_config()
        
        # 初始化Jinja2模板引擎
        self.env = Environment(
            loader=FileSystemLoader(str(TEMPLATE_DIR)),
            autoescape=True,
        )
    
    def send(self, news_items: List[NewsItem], subject: Optional[str] = None) -> bool:
        """
        发送新闻邮件
        
        Args:
            news_items: 新闻列表
            subject: 邮件主题，默认自动生成
            
        Returns:
            是否发送成功
        """
        if not news_items:
            logger.warning("没有新闻可发送")
            return False
        
        if not self._validate_config():
            return False
        
        # 生成邮件内容
        html_content = self._render_template(news_items)
        
        # 生成主题
        if not subject:
            from datetime import datetime
            today = datetime.now().strftime("%Y-%m-%d")
            subject = f"AI资讯日报 - {today}"
        
        # 发送邮件
        return self._send_email(subject, html_content)
    
    def _validate_config(self) -> bool:
        """验证邮件配置"""
        if not self.config.username:
            logger.error("未配置EMAIL_USER")
            return False
        
        if not self.config.password:
            logger.error("未配置EMAIL_PASSWORD")
            return False
        
        if not self.config.recipients:
            logger.error("未配置EMAIL_TO")
            return False
        
        return True
    
    def _render_template(self, news_items: List[NewsItem]) -> str:
        """渲染邮件模板"""
        try:
            template = self.env.get_template("email_template.html")
        except Exception:
            # 如果模板不存在，使用内置模板
            return self._render_builtin_template(news_items)
        
        from datetime import datetime
        
        return template.render(
            news_items=news_items,
            date=datetime.now().strftime("%Y年%m月%d日"),
            total_count=len(news_items),
        )
    
    def _render_builtin_template(self, news_items: List[NewsItem]) -> str:
        """使用内置模板渲染"""
        from datetime import datetime
        
        today = datetime.now().strftime("%Y年%m月%d日")
        
        items_html = ""
        for i, item in enumerate(news_items, 1):
            pub_date_str = ""
            if item.pub_date:
                pub_date_str = item.pub_date.strftime("%m-%d %H:%M")
            
            items_html += f"""
            <div style="margin-bottom: 24px; padding: 16px; background: #f9f9f9; border-radius: 8px;">
                <h3 style="margin: 0 0 8px 0; font-size: 16px;">
                    <span style="color: #666; font-weight: normal;">{i}.</span>
                    <a href="{item.url}" style="color: #1a73e8; text-decoration: none;">{item.title}</a>
                </h3>
                <p style="margin: 0 0 8px 0; color: #666; font-size: 14px;">
                    来源: {item.source_name} {f'· {pub_date_str}' if pub_date_str else ''}
                </p>
                {f'<p style="margin: 0; color: #333; font-size: 14px; line-height: 1.6;">{item.summary}</p>' if item.summary else ''}
            </div>
            """
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background: #fff;">
            <div style="text-align: center; padding: 20px 0; border-bottom: 2px solid #1a73e8;">
                <h1 style="margin: 0; color: #333; font-size: 24px;">AI资讯日报</h1>
                <p style="margin: 8px 0 0 0; color: #666;">{today}</p>
            </div>
            
            <div style="padding: 20px 0;">
                <p style="color: #666; font-size: 14px;">今日为您精选 {len(news_items)} 条AI领域热点资讯：</p>
                {items_html}
            </div>
            
            <div style="text-align: center; padding: 20px 0; border-top: 1px solid #eee; color: #999; font-size: 12px;">
                <p>由 AI News Daily 自动生成并发送</p>
                <p>数据来源: 36氪、虎嗅、TechCrunch、The Verge、Hacker News、Reddit</p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _send_email(self, subject: str, html_content: str) -> bool:
        """通过SMTP发送邮件"""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.config.sender or self.config.username
        msg["To"] = ", ".join(self.config.recipients)
        msg["Date"] = formatdate(localtime=True)
        
        # 添加纯文本版本（用于不支持HTML的客户端）
        text_content = self._html_to_text(html_content)
        msg.attach(MIMEText(text_content, "plain", "utf-8"))
        
        # 添加HTML版本
        msg.attach(MIMEText(html_content, "html", "utf-8"))
        
        try:
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(self.config.username, self.config.password)
                server.sendmail(
                    self.config.sender or self.config.username,
                    self.config.recipients,
                    msg.as_string(),
                )
            
            logger.info(f"邮件发送成功: {subject} -> {self.config.recipients}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP认证失败: {e}")
            logger.error("请检查EMAIL_USER和EMAIL_PASSWORD是否正确")
            logger.error("Gmail用户需要使用应用专用密码，而非账户密码")
            return False
        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return False
    
    def _html_to_text(self, html: str) -> str:
        """将HTML转换为纯文本"""
        import re
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', html)
        # 压缩空白
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
