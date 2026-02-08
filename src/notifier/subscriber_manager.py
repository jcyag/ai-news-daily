import imaplib
import email
import logging
import os
import re
from pathlib import Path
from typing import Set

logger = logging.getLogger(__name__)

class SubscriberManager:
    def __init__(self):
        self.data_dir = Path(__file__).parent.parent.parent / "data"
        self.subscriber_file = self.data_dir / "subscribers.txt"
        self.data_dir.mkdir(exist_ok=True)
        
        self.user = os.getenv("EMAIL_USER")
        self.password = os.getenv("EMAIL_PASSWORD")
        self.imap_server = "imap.gmail.com"

    def check_new_subscriptions(self):
        """连接邮件服务器检查新订阅请求"""
        if not self.user or not self.password:
            logger.error("未配置 EMAIL_USER 或 EMAIL_PASSWORD，无法检查订阅")
            return
            
        try:
            # 连接 IMAP
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.user, self.password)
            mail.select("inbox")
            
            # 搜索未读且包含关键字的邮件
            # 搜索内容和标题
            search_criterion = '(UNSEEN OR ALL) SUBJECT "订阅AI资讯日报"'
            status, messages = mail.search(None, 'OR SUBJECT "订阅AI资讯日报" BODY "订阅AI资讯日报"')
            
            if status != 'OK':
                logger.info("没有找到新的订阅邮件")
                return

            new_emails = []
            for num in messages[0].split():
                res, msg_data = mail.fetch(num, '(RFC822)')
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        # 获取发件人邮箱
                        from_ = msg.get("From")
                        email_addr = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', from_)
                        if email_addr:
                            new_emails.append(email_addr.group(0))
                            logger.info(f"发现新订阅请求: {email_addr.group(0)}")
            
            if new_emails:
                self._update_subscriber_file(set(new_emails))
            
            mail.logout()
        except Exception as e:
            logger.error(f"检查订阅失败: {e}")

    def _update_subscriber_file(self, new_emails: Set[str]):
        """更新本地订阅者文件"""
        existing_emails = self.load_subscribers()
        updated_emails = existing_emails.union(new_emails)
        
        with open(self.subscriber_file, "w", encoding="utf-8") as f:
            for addr in sorted(updated_emails):
                f.write(f"{addr}\n")
        
        logger.info(f"订阅列表已更新。新增: {len(updated_emails) - len(existing_emails)}，总数: {len(updated_emails)}")

    def load_subscribers(self) -> Set[str]:
        """读取现有订阅者"""
        if not self.subscriber_file.exists():
            return set()
        
        with open(self.subscriber_file, "r", encoding="utf-8") as f:
            return {line.strip() for line in f if line.strip()}

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    manager = SubscriberManager()
    manager.check_new_subscriptions()
