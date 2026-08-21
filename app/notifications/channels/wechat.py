import httpx
from typing import Dict, Any, Optional
from loguru import logger
from app.core.config import settings
from app.notifications.base import BaseChannel

class WeChatWorkChannel(BaseChannel):
    """企业微信机器人 / 应用通知推送实现"""

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or settings.WECHAT_WORK_WEBHOOK

    @property
    def channel_name(self) -> str:
        return "wechat_work"

    def format_job_card(self, job_data: Dict[str, Any]) -> str:
        """
        生成企业微信 Markdown 格式卡片排版
        """
        unit = job_data.get("unit_name", "未知单位")
        job = job_data.get("job_name", "公卫相关岗位")
        headcount = job_data.get("headcount", 1)
        edu = job_data.get("education", "本科及以上")
        major = job_data.get("major_raw", "预防医学")
        star = job_data.get("match_level", 5)
        
        bz = job_data.get("is_bianzhi", 1)
        bz_type = job_data.get("bianzhi_type", "事业编制")
        bz_tag = "<font color=\"info\">🟢 事业编制</font>" if bz == 1 else ("<font color=\"warning\">🟡 备案/存疑</font>" if bz == 2 else "<font color=\"comment\">🔴 编外合同</font>")
        
        priority = job_data.get("priority_level", "A")
        deadline = job_data.get("apply_end_date", "详见招考公告")
        url = job_data.get("source_url", "")
        certs = job_data.get("cert_requirements", "无明确限制")
        age = job_data.get("age_limit_num", "按公告执行")

        card = (
            f"### <font color=\"warning\">【{priority}级预警】</font>{unit} 招考速报\n\n"
            f"> **招考单位：** {unit}\n"
            f"> **招聘岗位：** {job}（招 {headcount} 人）\n"
            f"> **专业匹配：** **{star}星级对口**\n"
            f"> **编制性质：** {bz_tag}（{bz_type}）\n"
            f"> **学历/专业：** {edu} | {major}\n"
            f"> **资格证书：** {certs}\n"
            f"> **年龄限制：** {age}周岁以下\n"
            f"> **报名截止：** `{deadline}`\n"
        )
        if url:
            card += f"\n[👉 点击查看官方招考公告原文]({url})"
        return card

    async def send(self, title: str, content: str, payload: Optional[Dict[str, Any]] = None) -> bool:
        if not self.webhook_url:
            logger.warning("WeChat Work Webhook not configured, mock sending.")
            return True

        data = {
            "msgtype": "markdown",
            "markdown": {
                "content": content
            }
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(self.webhook_url, json=data)
                if res.status_code == 200:
                    logger.info("WeChat Work notification sent successfully.")
                    return True
                else:
                    logger.error(f"Failed to send WeChat Work message: {res.status_code} - {res.text}")
                    return False
        except Exception as e:
            logger.error(f"Error sending WeChat Work notification: {e}")
            return False
