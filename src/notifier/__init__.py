import sys
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from notifier.email_sender import EmailSender

__all__ = ['EmailSender']
