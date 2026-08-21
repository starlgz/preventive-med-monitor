import json
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger
from datetime import datetime

from app.models.entities import Job, Announcement, Notification
from app.notifications.channels.telegram import TelegramChannel
from app.notifications.channels.wechat import WeChatWorkChannel
from app.notifications.channels.email import EmailChannel
from app.notifications.channels.webhook import WebhookChannel

class NotificationCenter:
    """多渠道通知中枢服务"""

    def __init__(self):
        self.channels = {
            "telegram": TelegramChannel(),
            "wechat_work": WeChatWorkChannel(),
            "email": EmailChannel(),
            "webhook": WebhookChannel()
        }

    async def push_job_notification(
        self,
        session: AsyncSession,
        job_id: int,
        channel_names: Optional[List[str]] = None,
        custom_payload: Optional[Dict[str, Any]] = None
    ) -> List[Notification]:
        """
        向指定渠道推送单个岗位通知并记录数据库 (防重复发送)
        """
        job = await session.get(Job, job_id)
        if not job:
            logger.error(f"Job with id {job_id} not found.")
            return []

        announcement = await session.get(Announcement, job.announcement_id)
        source_url = announcement.url if announcement else "#"

        job_dict = {
            "unit_name": job.unit_name,
            "job_name": job.job_name,
            "headcount": job.headcount,
            "education": job.education,
            "major_raw": job.major_raw,
            "match_level": job.match_level or 5,
            "is_bianzhi": job.is_bianzhi,
            "bianzhi_type": job.bianzhi_type or "未知",
            "priority_level": job.priority_level or "B",
            "cert_requirements": job.cert_requirements or "无明确限制",
            "age_limit_num": job.age_limit_num or "不限",
            "apply_end_date": job.apply_end_date.strftime("%Y-%m-%d %H:%M") if job.apply_end_date else "详见公告",
            "source_url": source_url
        }

        target_channels = channel_names or ["telegram", "wechat_work"]
        records = []

        for ch_name in target_channels:
            channel = self.channels.get(ch_name)
            if not channel:
                logger.warning(f"Notification channel {ch_name} is not registered.")
                continue

            # 查重：检查是否已经对该岗位在该渠道发送过
            existing = (await session.execute(
                select(Notification).where(
                    Notification.job_id == job.id,
                    Notification.channel == ch_name
                )
            )).scalars().first()

            if existing:
                logger.info(f"Job {job.id} already notified via {ch_name}, skipping.")
                records.append(existing)
                continue

            card_content = channel.format_job_card(job_dict)
            title = f"🎯【{job_dict['priority_level']}级】{job_dict['unit_name']} - {job_dict['job_name']}"

            success = await channel.send(title=title, content=card_content, payload=custom_payload)

            record = Notification(
                job_id=job.id,
                channel=ch_name,
                priority_level=job_dict["priority_level"],
                status="SENT" if success else "FAILED",
                sent_at=datetime.now()
            )
            session.add(record)
            records.append(record)

        await session.commit()
        return records

    async def broadcast_s_level_alerts(
        self,
        session: AsyncSession,
        channel_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """专门用于向全网或所有订阅渠道广播 S 级稀缺/重点招考速报"""
        return await self.push_batch_alerts(
            session=session,
            min_priority="S",
            channel_names=channel_names or ["telegram", "wechat_work", "webhook"]
        )

    async def push_batch_alerts(
        self,
        session: AsyncSession,
        min_priority: str = "B",
        channel_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        批量扫描未推送的高优先级岗位并发送告警
        """
        priority_order = {"S": 5, "A": 4, "B": 3, "C": 2, "D": 1}
        min_weight = priority_order.get(min_priority, 3)

        result = await session.execute(select(Job))
        all_jobs = result.scalars().all()

        pushed_count = 0
        total_matched = 0

        for job in all_jobs:
            p_lvl = job.priority_level or "D"
            if priority_order.get(p_lvl, 1) >= min_weight:
                total_matched += 1
                # 检查是否已经为该岗位发送过通知
                existing = (await session.execute(
                    select(Notification).where(
                        Notification.job_id == job.id,
                        Notification.status == "SENT"
                    )
                )).scalars().first()

                if not existing:
                    await self.push_job_notification(session, job.id, channel_names)
                    pushed_count += 1

        return {
            "status": "SUCCESS",
            "min_priority": min_priority,
            "total_high_priority_jobs": total_matched,
            "newly_pushed_jobs": pushed_count
        }

notification_service = NotificationCenter()
