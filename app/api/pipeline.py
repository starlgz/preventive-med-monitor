from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional

from app.core.database import get_db
from app.core.pipeline import FullAutomationPipeline
from app.schemas.pipeline import PipelineRunRequest, PipelineRunResponse

router = APIRouter(prefix="/pipeline", tags=["全链路自动化流水线"])

@router.post("/run", response_model=PipelineRunResponse)
async def run_pipeline(
    req: PipelineRunRequest,
    db: AsyncSession = Depends(get_db)
):
    """手动触发或调度全链路自动化流水线"""
    result = await FullAutomationPipeline.run_pipeline(
        session=db,
        source_key=req.source_key,
        auto_push_notifications=req.auto_push_notifications
    )
    return result
