import httpx
from typing import Dict, Any, Optional
from loguru import logger
from app.core.config import settings
from app.notifications.base import BaseChannel

class TelegramChannel(BaseChannel):
    """Telegram Bot 通知推送实现"""

    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or settings.TELEGRAM_CHAT_ID

    @property
    def channel_name(self) -> str:
        return "telegram"

    def format_job_card(self, job_data: Dict[str, Any]) -> str:
        """
        生成 Telegram 优美 HTML 结构化卡片排版
        """
        unit = job_data.get("unit_name", "未知单位")
        job = job_data.get("job_name", "公卫相关岗位")
        headcount = job_data.get("headcount", 1)
        edu = job_data.get("education", "本科及以上")
        major = job_data.get("major_raw", "预防医学")
        star = job_data.get("match_level", 5)
        stars_str = "⭐" * int(star) if star else "⭐⭐⭐⭐⭐"
        
        bz = job_data.get("is_bianzhi", 1)
        bz_type = job_data.get("bianzhi_type", "事业编制")
        bz_tag = "🟢 事业编制" if bz == 1 else ("🟡 备案/存疑" if bz == 2 else "🔴 编外合同")
        
        priority = job_data.get("priority_level", "A")
        deadline = job_data.get("apply_end_date", "详见招考公告")
        url = job_data.get("source_url", "")
        certs = job_data.get("cert_requirements", "无明确限制")
        age = job_data.get("age_limit_num", "按公告执行")

        card = (
            f"🎯 <b>【{priority}级预警】{unit} - 招考速报</b>\n\n"
            f"🏢 <b>招考单位：</b>{unit}\n"
            f"💼 <b>招聘岗位：</b>{job} (招 {headcount} 人)\n"
            f"⭐ <b>专业匹配：</b>{stars_str} ({star}星级对口)\n"
            f"🏷️ <b>编制性质：</b>{bz_tag} ({bz_type})\n"
            f"🎓 <b>学历/专业：</b>{edu} | {major}\n"
            f"📜 <b>资格证书：</b>{certs}\n"
            f"⏳ <b>年龄限制：</b>{age}周岁以下\n"
            f"⏰ <b>报名截止：</b><code>{deadline}</code>\n"
        )
        if url:
            card += f"\n🔗 <a href='{url}'>点击查看官方招聘公告原文</a>"
        return card

    async def send(self, title: str, content: str, payload: Optional[Dict[str, Any]] = None) -> bool:
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram Bot Token or Chat ID not configured, mock sending.")
            return True

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        data = {
            "chat_id": self.chat_id,
            "text": content,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, json=data)
                if res.status_code == 200:
                    logger.info(f"Telegram notification sent successfully to {self.chat_id}")
                    return True
                else:
                    logger.error(f"Failed to send Telegram message: {res.status_code} - {res.text}")
                    return False
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {e}")
            return False
