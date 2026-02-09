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
        """处理订阅请求，增强匹配稳定性"""
        if not self.user or not self.password:
            return

        try:
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.user, self.password)
            mail.select("inbox")

            since_date = (datetime.now() - timedelta(days=7)).strftime("%d-%b-%Y")
            search_query = f'(SINCE "{since_date}")'
            status, messages = mail.search(None, search_query)
            
            if status != 'OK': return

            message_nums = messages[0].split()
            user_intents: Dict[str, str] = {}

            for num in message_nums:
                try:
                    res, msg_data = mail.fetch(num, '(RFC822)')
                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])
                            subject = self._decode_subject(msg.get("Subject", ""))
                            body = self._get_body(msg)
                            
                            # 提取发件人
                            from_ = msg.get("From", "")
                            email_addr_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', from_)
                            if not email_addr_match: continue
                            email_addr = email_addr_match.group(0).lower().strip()

                            # 增强匹配逻辑：移除所有空白字符后搜索
                            full_text = (subject + body).replace(" ", "").replace("\n", "").replace("\t", "")
                            
                            if "取消订阅" in full_text and "AI资讯日报" in full_text:
                                user_intents[email_addr] = 'unsubscribe'
                                logger.info(f"检测到退订意图: {email_addr} (标题: {subject[:20]})")
                            elif "订阅" in full_text and "AI资讯日报" in full_text:
                                user_intents[email_addr] = 'subscribe'
                                logger.info(f"检测到订阅意图: {email_addr} (标题: {subject[:20]})")
                                
                except Exception as e:
                    logger.error(f"解析邮件失败: {e}")

            mail.logout()
            if user_intents:
                self._apply_intents(user_intents)

        except Exception as e:
            logger.error(f"IMAP操作异常: {e}")

    def _decode_subject(self, subject_raw: str) -> str:
        try:
            from email.header import decode_header
            parts = decode_header(subject_raw)
            return "".join([
                part.decode(enc or 'utf-8', errors='ignore') if isinstance(part, bytes) else part 
                for part, enc in parts
            ])
        except Exception: return str(subject_raw)

    def _get_body(self, msg) -> str:
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        payload = part.get_payload(decode=True)
                        if payload: body = payload.decode('utf-8', errors='ignore')
                    except Exception: pass
                    break
        else:
            try:
                payload = msg.get_payload(decode=True)
                if isinstance(payload, bytes): body = payload.decode('utf-8', errors='ignore')
            except Exception: pass
        return body

    def _apply_intents(self, intents: Dict[str, str]):
        current_subs = self.load_subscribers()
        original_subs = set(current_subs)
        
        for email_addr, action in intents.items():
            if action == 'subscribe' and email_addr not in current_subs:
                current_subs.add(email_addr)
                self._send_feedback(email_addr, "订阅成功", "您已成功订阅AI资讯日报。")
            elif action == 'unsubscribe' and email_addr in current_subs:
                current_subs.remove(email_addr)
                self._send_feedback(email_addr, "已取消订阅AI资讯日报", "您已成功取消订阅。")
                logger.info(f"已从列表中移除: {email_addr}")

        if current_subs != original_subs:
            with open(self.subscriber_file, "w", encoding="utf-8") as f:
                for addr in sorted(current_subs):
                    f.write(f"{addr}\n")
            logger.info("订阅列表已更新并保存")

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
            logger.error(f"发送回执失败: {e}")

    def load_subscribers(self) -> Set[str]:
        if not self.subscriber_file.exists(): return set()
        with open(self.subscriber_file, "r", encoding="utf-8") as f:
            return {line.strip().lower() for line in f if line.strip()}

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    SubscriberManager().process_all_requests()
