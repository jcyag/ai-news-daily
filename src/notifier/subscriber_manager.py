import imaplib
import email
import logging
import os
import re
import smtplib
from email.mime.text import MIMEText
from email.utils import formatdate
from pathlib import Path
from typing import Set, List

# 导入配置和邮件发送逻辑
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
        """处理所有订阅和取消订阅请求"""
        if not self.user or not self.password:
            logger.error("未配置邮件账户，无法处理订阅请求")
            return

        try:
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.user, self.password)
            mail.select("inbox")

            # 1. 处理订阅请求
            new_subscribers = self._get_emails_by_keyword(mail, "订阅AI资讯日报")
            # 2. 处理取消订阅请求
            unsubscribers = self._get_emails_by_keyword(mail, "取消订阅AI资讯日报")

            mail.logout()

            # 更新文件并发送反馈
            self._handle_updates(new_subscribers, unsubscribers)

        except Exception as e:
            logger.error(f"处理订阅/取消订阅请求失败: {e}")

    def _get_emails_by_keyword(self, mail, keyword: str) -> Set[str]:
        """根据关键字搜索未读邮件并提取发件人"""
        emails = set()
        # 搜索包含关键字的未读邮件
        search_query = f'(UNSEEN SUBJECT "{keyword}")'
        status, messages = mail.search(None, search_query)
        
        if status != 'OK' or not messages[0]:
            return emails

        for num in messages[0].split():
            try:
                res, msg_data = mail.fetch(num, '(RFC822)')
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        from_ = msg.get("From")
                        email_addr = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', from_)
                        if email_addr:
                            emails.add(email_addr.group(0).lower())
                # 将邮件标记为已读，避免下次重复处理
                mail.store(num, '+FLAGS', '\\Seen')
            except Exception as e:
                logger.error(f"解析邮件条目失败: {e}")
                
        return emails

    def _handle_updates(self, new_subs: Set[str], unsub_subs: Set[str]):
        """执行文件更新并发送通知"""
        current_subs = self.load_subscribers()
        
        added_count = 0
        removed_count = 0

        # 处理新增
        for email_addr in new_subs:
            if email_addr not in current_subs:
                current_subs.add(email_addr)
                self._send_feedback(email_addr, "订阅成功", "您已成功订阅AI资讯日报，我们将每天为您推送最新的AI领域资讯。")
                added_count += 1

        # 处理取消
        for email_addr in unsub_subs:
            if email_addr in current_subs:
                current_subs.remove(email_addr)
                self._send_feedback(email_addr, "已取消订阅AI资讯日报", "您已成功取消订阅。如果您以后想再次订阅，只需向我发送“订阅AI资讯日报”即可。")
                removed_count += 1

        if added_count > 0 or removed_count > 0:
            with open(self.subscriber_file, "w", encoding="utf-8") as f:
                for addr in sorted(current_subs):
                    f.write(f"{addr}\n")
            logger.info(f"订阅列表已更新: 新增 {added_count}, 移除 {removed_count}")

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
            logger.info(f"已向 {to_email} 发送反馈邮件: {subject}")
        except Exception as e:
            logger.error(f"发送反馈邮件到 {to_email} 失败: {e}")

    def load_subscribers(self) -> Set[str]:
        if not self.subscriber_file.exists():
            return set()
        with open(self.subscriber_file, "r", encoding="utf-8") as f:
            return {line.strip().lower() for line in f if line.strip()}

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    manager = SubscriberManager()
    manager.process_all_requests()
