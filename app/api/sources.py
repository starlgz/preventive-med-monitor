from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.database import get_db
from app.models.entities import Source
from app.schemas.source import SourceResponse, SourceTriggerResponse, SchedulerStatusResponse
from app.scheduler.manager import scheduler_manager
from app.sources.registry import SourceRegistry

router = APIRouter(prefix="/sources", tags=["数据源与调度器"])

@router.get("", response_model=List[SourceResponse], summary="获取所有已注册数据源状态")
async def list_sources(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Source))
    return result.scalars().all()

@router.get("/scheduler/status", response_model=SchedulerStatusResponse, summary="获取调度器运行状态")
async def get_scheduler_status():
    return scheduler_manager.get_status()

@router.post("/{source_id}/trigger", response_model=SourceTriggerResponse, summary="手动立即触发单源抓取")
async def trigger_source(source_id: str):
    plugin = SourceRegistry.get(source_id)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"数据源插件 [{source_id}] 未找到")
    
    result = await scheduler_manager.run_single_source(source_id)
    return result
