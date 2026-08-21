from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.ai.evaluator import AIEligibilityEvaluator
from app.models.entities import Job
from sqlalchemy import select

router = APIRouter(prefix="/ai", tags=["AI研判"])

class JobAIRequest(BaseModel):
    job_id: Optional[int] = None
    job_data: Optional[Dict[str, Any]] = None
    user_profile: Optional[Dict[str, Any]] = {
        "education_level": "本科",
        "is_fresh_grad": True,
        "has_cert": True,
        "age": 28
    }

@router.post("/evaluate_job")
async def evaluate_job(req: JobAIRequest, db: AsyncSession = Depends(get_db)):
    """对招考岗位进行 AI 报考资格与风险研判 (支持 OpenAI 兼容 API 及 0 Token 规则降级)"""
    job_dict = req.job_data or {}
    if req.job_id:
        job = (await db.execute(select(Job).where(Job.id == req.job_id))).scalars().first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        job_dict = {
            "unit_name": job.unit_name,
            "job_name": job.job_name,
            "major_raw": job.major_raw,
            "education": job.education,
            "cert_requirements": job.cert_requirements,
            "is_fresh_grad": job.is_fresh_grad,
            "age_limit_num": job.age_limit_num,
            "match_level": job.match_level,
            "is_bianzhi": job.is_bianzhi,
            "bianzhi_type": job.bianzhi_type
        }
    
    result = await AIEligibilityEvaluator.evaluate_eligibility(
        job_data=job_dict,
        user_profile=req.user_profile
    )
    return {
        "status": "SUCCESS",
        "evaluation": result
    }
