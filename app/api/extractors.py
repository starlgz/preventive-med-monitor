from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.extractors.service import JobExtractionService
from app.schemas.extractor import ExtractJobsResponse

router = APIRouter(prefix="/extractors", tags=["Extractors"])

@router.post("/extract_announcement/{announcement_id}", response_model=ExtractJobsResponse)
async def extract_jobs_from_announcement(
    announcement_id: int,
    db: AsyncSession = Depends(get_db)
):
    """从指定公告中提取岗位并结构化持久化到 jobs 表"""
    result = await JobExtractionService.extract_and_save_jobs(db, announcement_id)
    if result.get("status") == "FAILED":
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result
