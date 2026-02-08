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
        """处理所有订阅和取消订阅请求"""
        if not self.user or not self.password:
            logger.error("未配置邮件账户，无法处理订阅请求")
            return

        try:
            logger.info(f"正在连接 IMAP 服务器: {self.imap_server}...")
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.user, self.password)
            mail.select("inbox")

            # 1. 查找所有未读邮件
            status, messages = mail.search(None, 'UNSEEN')
            if status != 'OK':
                logger.info("未能获取未读邮件列表")
                return
            
            message_nums = messages[0].split()
            logger.info(f"发现 {len(message_nums)} 封未读邮件，正在扫描关键字...")

            new_subs = set()
            unsub_subs = set()

            for num in message_nums:
                try:
                    res, msg_data = mail.fetch(num, '(RFC822)')
                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])
                            
                            # 解析标题
                            subject_raw = msg.get("Subject", "")
                            subject = ""
                            try:
                                from email.header import decode_header
                                subject_parts = decode_header(subject_raw)
                                for part, encoding in subject_parts:
                                    if isinstance(part, bytes):
                                        subject += part.decode(encoding or 'utf-8', errors='ignore')
                                    else:
                                        subject += part
                            except Exception:
                                subject = str(subject_raw)
                            
                            # 获取正文
                            body = ""
                            if msg.is_multipart():
                                for part in msg.walk():
                                    if part.get_content_type() == "text/plain":
                                        try:
                                            body_bytes = part.get_payload(decode=True)
                                            if isinstance(body_bytes, bytes):
                                                body = body_bytes.decode('utf-8', errors='ignore')
                                        except Exception:
                                            pass
                                        break
                            else:
                                try:
                                    body_bytes = msg.get_payload(decode=True)
                                    if isinstance(body_bytes, bytes):
                                        body = body_bytes.decode('utf-8', errors='ignore')
                                except Exception:
                                    pass

                            # 合并并清理文本，用于匹配
                            full_content = (subject + body).replace(" ", "").replace("\n", "").replace("\r", "")
                            
                            # 提取发件人
                            from_ = msg.get("From", "")
                            email_addr_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', from_)
                            if not email_addr_match:
                                continue
                            
                            email_addr = email_addr_match.group(0).lower()

                            if "订阅AI资讯日报" in full_content:
                                logger.info(f"匹配到订阅请求: {email_addr}")
                                new_subs.add(email_addr)
                                mail.store(num, '+FLAGS', '\\Seen') # 标记已读
                            elif "取消订阅AI资讯日报" in full_content:
                                logger.info(f"匹配到取消订阅请求: {email_addr}")
                                unsub_subs.add(email_addr)
                                mail.store(num, '+FLAGS', '\\Seen') # 标记已读
                except Exception as e:
                    logger.error(f"解析邮件 {num} 失败: {e}")

            mail.logout()
            self._handle_updates(new_subs, unsub_subs)

        except Exception as e:
            logger.error(f"处理订阅请求时发生异常: {e}")
            logger.error("请确保 Gmail 已开启 IMAP 服务，并使用了正确的‘应用专用密码’。")

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
