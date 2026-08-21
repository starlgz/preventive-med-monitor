from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime

class BaseChannel(ABC):
    """通知渠道基类抽象接口"""

    @property
    @abstractmethod
    def channel_name(self) -> str:
        """渠道唯一标识 (如 telegram, wechat_work, email)"""
        pass

    @abstractmethod
    async def send(self, title: str, content: str, payload: Optional[Dict[str, Any]] = None) -> bool:
        """发送单条消息通知"""
        pass

    @abstractmethod
    def format_job_card(self, job_data: Dict[str, Any]) -> str:
        """将单个岗位数据格式化为特定渠道友好的排版卡片"""
        pass
