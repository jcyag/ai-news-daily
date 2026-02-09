import imaplib
import email
import logging
import os
import re
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.utils import formatdate
from pathlib import Path
from typing import Set, List, Dict

# 导入配置
from config import get_email_config

logger = logging.getLogger(__name__)

class SubscriberManager:
    def __init__(self):
        self.data_dir = Path(__file__).parent.parent.parent / "data"
        self.subscriber_file = self.data_dir / "subscribers.txt"
        self.data_dir.mkdir(exist_ok=True)
        
        self.config = get_email_config()
        self.user = self.config.username
        self.password = self.config.password
        self.imap_server = "imap.gmail.com"

    def process_all_requests(self):
        """处理所有订阅和取消订阅请求，遵循‘最后一次操作为准’原则"""
        if not self.user or not self.password:
            logger.error("未配置邮件账户，无法处理订阅请求")
            return

        try:
            logger.info(f"正在连接 IMAP 服务器: {self.imap_server}...")
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.user, self.password)
            mail.select("inbox")

            # 计算 7 天前的日期 (IMAP 标准格式)
            since_date = (datetime.now() - timedelta(days=7)).strftime("%d-%b-%Y")
            search_query = f'(SINCE "{since_date}")'
            
            logger.info(f"正在扫描自 {since_date} 以来的一周内邮件...")
            status, messages = mail.search(None, search_query)
            
            if status != 'OK':
                logger.info("未能获取邮件列表")
                return
            
            # 邮件编号按递增排序，即越往后邮件越新
            message_nums = messages[0].split()
            logger.info(f"发现 {len(message_nums)} 封最近邮件，正在分析用户最终意图...")

            # 使用字典存储每个用户的最后意图: {email: 'subscribe'|'unsubscribe'}
            user_intents: Dict[str, str] = {}

            for num in message_nums:
                try:
                    res, msg_data = mail.fetch(num, '(RFC822)')
                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])
                            
                            # 1. 解析标题和正文
                            subject = self._decode_subject(msg.get("Subject", ""))
                            body = self._get_body(msg)
                            content = (subject + body).replace(" ", "").replace("\n", "").replace("\r", "")
                            
                            # 2. 提取发件人
                            from_ = msg.get("From", "")
                            email_addr_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', from_)
                            if not email_addr_match:
                                continue
                            
                            email_addr = email_addr_match.group(0).lower()

                            # 3. 识别操作（越晚收到的邮件会覆盖先前的意向）
                            if "取消订阅AI资讯日报" in content:
                                user_intents[email_addr] = 'unsubscribe'
                                logger.debug(f"检测到指令 [退订]: {email_addr}")
                            elif "订阅AI资讯日报" in content:
                                user_intents[email_addr] = 'subscribe'
                                logger.debug(f"检测到指令 [订阅]: {email_addr}")
                                
                except Exception as e:
                    logger.error(f"解析邮件 {num} 失败: {e}")

            mail.logout()
            
            # 4. 根据最终意向更新列表
            if user_intents:
                self._apply_intents(user_intents)
            else:
                logger.info("未发现任何有效的订阅或退订指令")

        except Exception as e:
            logger.error(f"处理订阅请求时发生异常: {e}")

    def _decode_subject(self, subject_raw: str) -> str:
        """安全解码邮件标题"""
        try:
            from email.header import decode_header
            parts = decode_header(subject_raw)
            decoded = ""
            for part, encoding in parts:
                if isinstance(part, bytes):
                    decoded += part.decode(encoding or 'utf-8', errors='ignore')
                else:
                    decoded += part
            return decoded
        except Exception:
            return str(subject_raw)

    def _get_body(self, msg) -> str:
        """提取邮件正文文本"""
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            body = payload.decode('utf-8', errors='ignore')
                    except Exception: pass
                    break
        else:
            try:
                payload = msg.get_payload(decode=True)
                if isinstance(payload, bytes):
                    body = payload.decode('utf-8', errors='ignore')
            except Exception: pass
        return body

    def _apply_intents(self, intents: Dict[str, str]):
        """应用最终意向到订阅列表"""
        current_subs = self.load_subscribers()
        original_subs = set(current_subs)
        
        for email_addr, action in intents.items():
            if action == 'subscribe':
                if email_addr not in current_subs:
                    current_subs.add(email_addr)
                    self._send_feedback(email_addr, "订阅成功", "您已成功订阅AI资讯日报。")
                    logger.info(f"新用户订阅: {email_addr}")
            elif action == 'unsubscribe':
                if email_addr in current_subs:
                    current_subs.remove(email_addr)
                    self._send_feedback(email_addr, "已取消订阅AI资讯日报", "您已成功取消订阅。")
                    logger.info(f"用户退订: {email_addr}")

        if current_subs != original_subs:
            with open(self.subscriber_file, "w", encoding="utf-8") as f:
                for addr in sorted(current_subs):
                    f.write(f"{addr}\n")
            logger.info("订阅列表已完成持久化更新")

    def _send_feedback(self, to_email: str, subject: str, content: str):
        """发送反馈邮件"""
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
            logger.debug(f"已发送回执给 {to_email}")
        except Exception as e:
            logger.error(f"发送回执到 {to_email} 失败: {e}")

    def load_subscribers(self) -> Set[str]:
        if not self.subscriber_file.exists():
            return set()
        with open(self.subscriber_file, "r", encoding="utf-8") as f:
            return {line.strip().lower() for line in f if line.strip()}

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    manager = SubscriberManager()
    manager.process_all_requests()
