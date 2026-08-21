from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.rules.major_matcher import MajorMatcher
from app.rules.matcher_service import MajorMatcherService
from app.schemas.rule import MajorMatchRequest, MajorMatchResponse, BatchMatchResponse

router = APIRouter(prefix="/rules", tags=["Rules"])

@router.post("/match_major", response_model=MajorMatchResponse)
async def test_match_major(
    req: MajorMatchRequest,
    db: AsyncSession = Depends(get_db)
):
    """单条专业与岗位条件五星匹配实时测试"""
    db_catalogs = await MajorMatcher.load_catalogs_from_db(db)
    result = MajorMatcher.match(
        major_raw=req.major_raw,
        unit_type=req.unit_type or "其他事业单位",
        job_name=req.job_name or "",
        db_catalogs=db_catalogs
    )
    return result

@router.post("/match_job/{job_id}", response_model=MajorMatchResponse)
async def match_single_job(
    job_id: int,
    db: AsyncSession = Depends(get_db)
):
    """对指定数据库岗位计算五星匹配度并更新入库"""
    result = await MajorMatcherService.match_single_job(db, job_id)
    if result.get("status") == "FAILED":
        raise HTTPException(status_code=404, detail=result.get("error"))
    return {
        "match_level": result["match_level"],
        "matched_codes": result["matched_codes"],
        "match_reason": result["match_reason"]
    }

@router.post("/batch_match_all_jobs", response_model=BatchMatchResponse)
async def batch_match_all(
    db: AsyncSession = Depends(get_db)
):
    """批量对全量已抓取岗位执行五星专业匹配计算与更新"""
    result = await MajorMatcherService.run_batch_match(db)
    return result
