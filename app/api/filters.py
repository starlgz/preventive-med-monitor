from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
from sqlalchemy import select, and_

from app.core.database import get_db
from app.models.entities import UserFilter
from app.schemas.filter import (
    UserFilterCreate,
    UserFilterResponse,
    FilterMatchRequest,
    FilterMatchResponse
)
from app.filters.filter_service import UserFilterService

router = APIRouter(prefix="/filters", tags=["用户个性化订阅与过滤"])

@router.post("/subscribe", response_model=UserFilterResponse, summary="创建或更新用户个性化订阅规则")
async def create_user_filter(
    payload: UserFilterCreate,
    db: AsyncSession = Depends(get_db)
):
    rules = {
        "provinces": payload.provinces,
        "min_star": payload.min_star,
        "only_bianzhi": payload.only_bianzhi,
        "include_beian": payload.include_beian,
        "education_level": payload.education_level,
        "is_fresh_grad": payload.is_fresh_grad,
        "has_cert": payload.has_cert,
        "max_age": payload.max_age,
        "unit_types": payload.unit_types
    }
    
    record = await UserFilterService.create_user_filter(
        session=db,
        user_id=payload.user_id,
        filter_name=payload.filter_name,
        rules=rules
    )
    
    import json
    return UserFilterResponse(
        id=record.id,
        user_id=record.user_id,
        channel=payload.channel,
        filter_name=record.filter_name,
        filter_rules=rules,
        is_active=True,
        created_at=record.created_at
    )

@router.get("/user_filters", summary="获取用户所有个性化订阅规则")
async def get_user_filters(
    user_id: str = Query(..., description="用户ID (如 telegram:123456)"),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(UserFilter).where(UserFilter.user_id == user_id)
    res = await db.execute(stmt)
    filters = res.scalars().all()
    
    import json
    results = []
    for f in filters:
        provinces = json.loads(f.target_provinces) if f.target_provinces else []
        results.append({
            "id": f.id,
            "user_id": f.user_id,
            "filter_name": f.filter_name,
            "provinces": provinces,
            "min_star": f.min_match_level,
            "education_level": f.target_degrees,
            "only_bianzhi": f.only_bianzhi == 1,
            "created_at": f.created_at
        })
    return {"user_id": user_id, "filters": results}

@router.post("/match_job", response_model=FilterMatchResponse, summary="比对岗位是否命中用户订阅画像")
async def match_user_job(
    payload: FilterMatchRequest,
    db: AsyncSession = Depends(get_db)
):
    res = await UserFilterService.match_user_and_job(
        session=db,
        user_id=payload.user_id,
        job_id=payload.job_id
    )
    return FilterMatchResponse(
        user_id=payload.user_id,
        job_id=payload.job_id,
        matched=res["matched"],
        reason=res["reason"]
    )
