from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.priority import (
    PriorityEvalRequest,
    PriorityEvalResponse,
    DeduplicateRequest,
    DeduplicateResponse,
    BatchPriorityResponse
)
from app.rules.priority_evaluator import PriorityEvaluator
from app.rules.deduplicator import JobDeduplicator
from app.rules.priority_service import PriorityService

router = APIRouter(prefix="/priorities", tags=["通知优先级与去重 (Priorities & Deduplication)"])

@router.post("/eval_priority", response_model=PriorityEvalResponse, summary="单岗位通知优先级测算")
async def eval_single_priority(req: PriorityEvalRequest):
    """
    输入专业匹配星级、编制标识与截止时间，计算通知优先级 (S / A / B / C / D)
    """
    res = PriorityEvaluator.evaluate(
        match_level=req.match_level,
        is_bianzhi=req.is_bianzhi,
        apply_end_date=req.apply_end_date,
        unit_type=req.unit_type
    )
    return res

@router.post("/deduplicate_jobs", response_model=DeduplicateResponse, summary="跨平台多源岗位相似度去重对比")
async def deduplicate_two_jobs(req: DeduplicateRequest):
    """
    对比两个可能来自不同数据源的岗位，判断是否为同一岗位
    """
    is_dup, sim_score, reason = JobDeduplicator.is_duplicate_job(req.job_a, req.job_b)
    return {
        "is_duplicate": is_dup,
        "similarity_score": round(sim_score, 4),
        "reason": reason
    }

@router.post("/batch_eval_jobs", response_model=BatchPriorityResponse, summary="全库岗位批量更新通知优先级")
async def batch_eval_jobs(db: AsyncSession = Depends(get_db)):
    """
    遍历数据库中所有岗位，依据 Phase 5 专业匹配与 Phase 6 编制评定结果，批量更新 priority_level
    """
    res = await PriorityService.run_batch_priority_evaluation(db)
    return res
