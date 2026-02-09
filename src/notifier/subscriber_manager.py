import imaplib
import email
import logging
import os
import re
import smtplib
import sys
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.utils import formatdate, parseaddr
from pathlib import Path
from typing import Set, List, Dict, Optional

# 将项目根目录和src目录添加到路径
# __file__ 是 src/notifier/subscriber_manager.py
# parent 是 src/notifier
# parent.parent 是 src
current_file = Path(__file__).resolve()
src_dir = current_file.parent.parent
sys.path.insert(0, str(src_dir))

# 导入配置
try:
    from config import get_email_config
except ImportError:
    # 兼容直接从 root 运行的情况
    sys.path.insert(0, str(src_dir.parent))
    from src.config import get_email_config

logger = logging.getLogger(__name__)

class SubscriberManager:
    def __init__(self):
        # data 目录在项目根目录
        self.root_dir = src_dir.parent
        self.data_dir = self.root_dir / "data"
        self.subscriber_file = self.data_dir / "subscribers.txt"
        self.data_dir.mkdir(exist_ok=True)
        
        self.config = get_email_config()
        self.user = self.config.username
        self.password = self.config.password
        self.imap_server = "imap.gmail.com"

    def process_all_requests(self):
        """处理订阅请求，遵循‘最后一次操作为准’并支持纠错引导"""
        if not self.user or not self.password:
            logger.error("未配置邮件账户，跳过订阅检查")
            return

        try:
            logger.info(f"正在连接 IMAP 服务器: {self.imap_server}...")
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.user, self.password)
            mail.select("inbox")

            # 扫描最近 7 天的邮件
            since_date = (datetime.now() - timedelta(days=7)).strftime("%d-%b-%Y")
            search_query = f'(SINCE "{since_date}")'
            status, messages = mail.search(None, search_query)
            
            if status != 'OK': return

            message_nums = messages[0].split()
            logger.info(f"发现 {len(message_nums)} 封最近邮件，正在进行意图分析...")

            user_intents: Dict[str, str] = {} # {email: 'subscribe'|'unsubscribe'|'invalid'}

            for num in message_nums:
                try:
                    res, msg_data = mail.fetch(num, '(RFC822)')
                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])
                            
                            # 1. 提取发件人 (标准化)
                            _, email_addr = parseaddr(msg.get("From", ""))
                            if not email_addr: continue
                            email_addr = email_addr.lower().strip()

                            # 2. 解析标题和内容
                            subject = self._decode_header(msg.get("Subject", ""))
                            body = self._get_text_content(msg)
                            full_text = (subject + body).replace(" ", "").replace("\n", "").replace("\r", "")

                            # 3. 意图识别 (正则表达式)
                            unsub_pattern = re.compile(r'(取消订阅|退订|停止|取消|unsubscribe|stop).*(AI)?(资讯)?日报', re.IGNORECASE)
                            sub_pattern = re.compile(r'(订阅|加入|启动|开始|subscribe|start).*(AI)?(资讯)?日报', re.IGNORECASE)
                            ambiguous_pattern = re.compile(r'AI资讯日报|AI日报', re.IGNORECASE)

                            unsub_match = unsub_pattern.search(full_text)
                            sub_match = sub_pattern.search(full_text)

                            if unsub_match:
                                user_intents[email_addr] = 'unsubscribe'
                                logger.info(f"检测到退订意图: {email_addr} (匹配: {unsub_match.group()})")
                            elif sub_match:
                                user_intents[email_addr] = 'subscribe'
                                logger.info(f"检测到订阅意图: {email_addr} (匹配: {sub_match.group()})")
                            elif ambiguous_pattern.search(full_text):
                                if email_addr not in user_intents:
                                    user_intents[email_addr] = 'invalid'
                                
                except Exception as e:
                    logger.error(f"解析邮件失败: {e}")

            mail.logout()
            
            if user_intents:
                self._apply_intents(user_intents)
            else:
                logger.info("未发现新的订阅相关邮件")

        except Exception as e:
            logger.error(f"IMAP操作异常: {e}")

    def _decode_header(self, raw_str: str) -> str:
        try:
            from email.header import decode_header
            parts = decode_header(raw_str)
            return "".join([
                part.decode(enc or 'utf-8', errors='ignore') if isinstance(part, bytes) else part 
                for part, enc in parts
            ])
        except Exception: return str(raw_str)

    def _get_text_content(self, msg) -> str:
        text = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    try:
                        payload = part.get_payload(decode=True)
                        if payload: text += payload.decode('utf-8', errors='ignore')
                    except Exception: pass
                elif content_type == "text/html":
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            html_content = payload.decode('utf-8', errors='ignore')
                            text += re.sub(r'<[^>]+>', '', html_content)
                    except Exception: pass
        else:
            try:
                payload = msg.get_payload(decode=True)
                if isinstance(payload, bytes):
                    text = payload.decode('utf-8', errors='ignore')
            except Exception: pass
        return text

    def _apply_intents(self, intents: Dict[str, str]):
        current_subs = self.load_subscribers()
        original_subs = set(current_subs)
        
        for email_addr, action in intents.items():
            if action == 'subscribe':
                if email_addr not in current_subs:
                    current_subs.add(email_addr)
                    self._send_feedback(email_addr, "正式订阅成功", "您已成功订阅 AI 资讯日报。")
                    logger.info(f"正式订阅: {email_addr}")
            elif action == 'unsubscribe':
                if email_addr in current_subs:
                    current_subs.remove(email_addr)
                    self._send_feedback(email_addr, "退订成功确认", "您已成功退订 AI 资讯日报。")
                    logger.info(f"正式退订: {email_addr}")
            elif action == 'invalid':
                if email_addr not in current_subs:
                    self._send_feedback(
                        email_addr, 
                        "指令未识别", 
                        "系统收到您的请求，但无法确定您的意图。请发送“订阅AI资讯日报”或“退订AI资讯日报”进行操作。"
                    )
                    logger.info(f"发送引导邮件: {email_addr}")

        if current_subs != original_subs:
            with open(self.subscriber_file, "w", encoding="utf-8") as f:
                for addr in sorted(current_subs):
                    f.write(f"{addr}\n")
            logger.info("订阅列表已更新并同步")

    def _send_feedback(self, to_email: str, subject: str, content: str):
        msg = MIMEText(content, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = self.config.sender or self.user
        msg["To"] = to_email
        msg["Date"] = formatdate(localtime=True)
        try:
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.sendmail(self.user, [to_email], msg.as_string())
        except Exception as e:
            logger.error(f"发送回执邮件失败 [{to_email}]: {e}")

    def load_subscribers(self) -> Set[str]:
        if not self.subscriber_file.exists(): return set()
        with open(self.subscriber_file, "r", encoding="utf-8") as f:
            return {line.strip().lower() for line in f if line.strip()}

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    SubscriberManager().process_all_requests()
