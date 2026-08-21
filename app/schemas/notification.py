from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class SendNotificationRequest(BaseModel):
    job_id: int
    channels: Optional[List[str]] = ["telegram", "wechat_work"]
    recipient: Optional[str] = "default_user"
    webhook_url: Optional[str] = None

class PushBatchAlertsRequest(BaseModel):
    min_priority: Optional[str] = "B"
    channels: Optional[List[str]] = ["telegram", "wechat_work"]

class BroadcastSLevelRequest(BaseModel):
    channels: Optional[List[str]] = ["telegram", "wechat_work", "webhook"]
    webhook_url: Optional[str] = None

class NotificationRecordResponse(BaseModel):
    id: int
    job_id: int
    channel: str
    priority_level: Optional[str] = "B"
    status: Optional[str] = "SENT"
