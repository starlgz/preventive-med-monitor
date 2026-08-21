import httpx
from typing import Dict, Any, Optional
from loguru import logger
from app.notifications.base import BaseChannel

class WebhookChannel(BaseChannel):
    """通用 Webhook / 自定义机器人通知推送实现 (如飞书、钉钉自定义机器人或系统回调)"""

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url

    @property
    def channel_name(self) -> str:
        return "webhook"

    def format_job_card(self, job_data: Dict[str, Any]) -> str:
        unit = job_data.get("unit_name", "未知单位")
        job = job_data.get("job_name", "公卫岗位")
        star = job_data.get("match_level", 5)
        stars_str = "⭐" * int(star) if star else "⭐⭐⭐⭐⭐"
        priority = job_data.get("priority_level", "A")
        deadline = job_data.get("apply_end_date", "详见招考公告")
        url = job_data.get("source_url", "")
        
        return f"【{priority}级预警】{unit} - {job} | 匹配度: {stars_str} | 截止时间: {deadline} | 链接: {url}"

    async def send(self, title: str, content: str, payload: Optional[Dict[str, Any]] = None) -> bool:
        target_url = None
        if payload and "webhook_url" in payload:
            target_url = payload["webhook_url"]
        else:
            target_url = self.webhook_url

        if not target_url:
            logger.warning("Webhook URL not specified, skipping send.")
            return True

        body = {
            "msgtype": "text",
            "text": {
                "content": f"{title}\n\n{content}"
            },
            "payload": payload or {}
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(target_url, json=body)
                if res.status_code in [200, 201, 204]:
                    return True
                logger.error(f"Webhook push failed with status {res.status_code}: {res.text}")
                return False
        except Exception as e:
            logger.error(f"Webhook push error: {str(e)}")
            return False
