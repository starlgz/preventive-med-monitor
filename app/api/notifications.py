from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any

from app.core.database import get_db
from app.models.entities import Job
from app.notifications.service import notification_service
from app.schemas.notification import (
    SendNotificationRequest,
    PushBatchAlertsRequest,
    BroadcastSLevelRequest,
    NotificationRecordResponse
)

router = APIRouter(prefix="/notifications", tags=["Notifications (多渠道通知告警中心)"])

@router.post("/send_job", response_model=List[NotificationRecordResponse], summary="向指定渠道推送单个岗位告警通知")
async def send_job_notification(
    req: SendNotificationRequest,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Job).where(Job.id == req.job_id)
    res = await db.execute(stmt)
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job with id {req.job_id} not found")

    custom_payload = {}
    if req.webhook_url:
        custom_payload["webhook_url"] = req.webhook_url

    records = await notification_service.push_job_notification(
        session=db,
        job_id=req.job_id,
        channel_names=req.channels,
        custom_payload=custom_payload
    )
    return records

@router.post("/push_batch_alerts", summary="批量扫描并推送满足条件的告警岗位")
async def push_batch_alerts(
    req: PushBatchAlertsRequest,
    db: AsyncSession = Depends(get_db)
):
    res = await notification_service.push_batch_alerts(
        session=db,
        min_priority=req.min_priority,
        channel_names=req.channels
    )
    return res

@router.post("/broadcast_s_level", summary="向指定频道/群组广播 S 级招考速报")
async def broadcast_s_level(
    req: BroadcastSLevelRequest,
    db: AsyncSession = Depends(get_db)
):
    res = await notification_service.broadcast_s_level_alerts(
        session=db,
        channel_names=req.channels
    )
    return res
