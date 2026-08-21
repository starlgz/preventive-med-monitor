from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.rules.bianzhi_evaluator import BianzhiEvaluator
from app.rules.bianzhi_service import BianzhiService
from app.schemas.bianzhi import BianzhiEvalRequest, BianzhiEvalResponse, BatchBianzhiResponse

router = APIRouter(prefix="/bianzhi", tags=["岗位编制三色研判"])

@router.post("/evaluate", response_model=BianzhiEvalResponse, summary="实时单条岗位编制研判")
async def evaluate_single_bianzhi(req: BianzhiEvalRequest):
    res = BianzhiEvaluator.evaluate(
        job_name=req.job_name,
        unit_name=req.unit_name,
        unit_type=req.unit_type,
        other_requirements=req.other_requirements,
        announcement_title=req.announcement_title,
        announcement_text=req.announcement_text
    )
    return BianzhiEvalResponse(**res)

@router.post("/evaluate_job/{job_id}", summary="研判指定岗位并更新数据库")
async def evaluate_db_job(job_id: int, db: AsyncSession = Depends(get_db)):
    res = await BianzhiService.evaluate_and_update_job(db, job_id)
    if res.get("status") == "FAILED":
        raise HTTPException(status_code=404, detail=res.get("error"))
    return res

@router.post("/batch_evaluate_jobs", response_model=BatchBianzhiResponse, summary="全量重新研判数据库中所有岗位编制属性")
async def batch_evaluate_jobs(db: AsyncSession = Depends(get_db)):
    res = await BianzhiService.run_batch_evaluation(db)
    return BatchBianzhiResponse(**res)
