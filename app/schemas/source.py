from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class SourceResponse(BaseModel):
    id: int
    source_id: str
    name: str
    category: str
    province: Optional[str] = "全国"
    base_url: str
    driver_type: str
    is_active: int
    health_score: float
    last_crawl_at: Optional[datetime] = None

class SourceTriggerResponse(BaseModel):
    source_id: str
    status: str
    items_found: int
    new_saved: int
    error: Optional[str] = None

class SchedulerStatusResponse(BaseModel):
    is_running: bool
    interval_minutes: int
    active_sources_count: int
    total_plugins_count: int
