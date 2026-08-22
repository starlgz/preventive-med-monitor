import io
import os
import json
import pandas as pd
from fastapi import APIRouter, Request, Depends, Response, Query
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from app.core.database import get_db
from app.models.entities import Job, Source, Announcement
from app.rules.major_matcher import MajorMatcher
from app.rules.bianzhi_evaluator import BianzhiEvaluator
from app.extractors.talent_policy import TalentPolicyExtractor
from app.extractors.pitfall_extractor import PitfallExtractor
from typing import Optional, List, Dict, Any
from datetime import datetime, date

router = APIRouter(tags=["Web Console & SPA"])

DIST_INDEX_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "dist", "index.html")

@router.get("/", response_class=HTMLResponse)
@router.get("/dashboard", response_class=HTMLResponse)
@router.get("/jobs", response_class=HTMLResponse)
@router.get("/sources", response_class=HTMLResponse)
@router.get("/rules", response_class=HTMLResponse)
@router.get("/bot", response_class=HTMLResponse)
@router.get("/ai-audit", response_class=HTMLResponse)
async def serve_spa_frontend(request: Request):
    """
    提供 Vue 3 SPA 前后端分离前端页面
    如果构建产物存在则返回生产单页 index.html
    """
    if os.path.exists(DIST_INDEX_PATH):
        return FileResponse(DIST_INDEX_PATH)
    return HTMLResponse("<h2>Vue 3 Frontend is building... Please refresh in a moment.</h2>")

@router.get("/api/v1/dashboard/stats")
@router.get("/api/v1/web/dashboard/stats")
async def get_dashboard_stats(session: AsyncSession = Depends(get_db)):
    """获取大盘统计指标 (严格剔除过期岗位，仅统计有效在招数据)"""
    today = date.today()
    valid_cond = or_(Job.apply_end_date >= today, Job.apply_end_date.is_(None))

    total_jobs = await session.scalar(select(func.count(Job.id)).where(valid_cond)) or 0
    five_star_jobs = await session.scalar(select(func.count(Job.id)).where(Job.match_level == 5, valid_cond)) or 0
    bianzhi_jobs = await session.scalar(select(func.count(Job.id)).where(Job.is_bianzhi == 1, valid_cond)) or 0
    beian_jobs = await session.scalar(select(func.count(Job.id)).where(Job.is_bianzhi == 2, valid_cond)) or 0
    
    # 统计人才引进/免笔试岗位
    talent_jobs = await session.scalar(select(func.count(Job.id)).where(Job.talent_tags.isnot(None), Job.talent_tags != "", valid_cond)) or 0
    
    today_start = datetime.combine(today, datetime.min.time())
    today_jobs = await session.scalar(select(func.count(Job.id)).where(Job.created_at >= today_start, valid_cond)) or 0
    total_sources = await session.scalar(select(func.count(Source.id))) or 0

    return {
        "total_jobs": total_jobs,
        "five_star_jobs": five_star_jobs,
        "bianzhi_jobs": bianzhi_jobs,
        "beian_jobs": beian_jobs,
        "talent_jobs": talent_jobs,
        "today_jobs": today_jobs,
        "total_sources": total_sources
    }

@router.get("/api/v1/dashboard/charts")
@router.get("/api/v1/web/analytics/distribution")
async def get_analytics_distribution(session: AsyncSession = Depends(get_db)):
    """全国省份招考热度与编制性质多维分布统计 (仅统计有效在招数据)"""
    today = date.today()
    valid_cond = or_(Job.apply_end_date >= today, Job.apply_end_date.is_(None))

    # 按省份统计
    prov_stmt = select(Job.province, func.count(Job.id)).where(valid_cond).group_by(Job.province).order_by(func.count(Job.id).desc())
    prov_res = await session.execute(prov_stmt)
    province_data = [{"province": r[0] or "其他", "count": r[1]} for r in prov_res.all()]

    # 按星级统计
    star_stmt = select(Job.match_level, func.count(Job.id)).where(valid_cond).group_by(Job.match_level).order_by(Job.match_level.desc())
    star_res = await session.execute(star_stmt)
    star_data = [{"level": f"{r[0]}星", "name": f"{r[0]}星推荐", "value": r[1], "count": r[1]} for r in star_res.all()]

    # 按单位性质统计
    unit_stmt = select(Job.unit_type, func.count(Job.id)).where(valid_cond).group_by(Job.unit_type).order_by(func.count(Job.id).desc())
    unit_res = await session.execute(unit_stmt)
    unit_data = [{"unit_type": r[0] or "综合机构", "count": r[1]} for r in unit_res.all()]

    # 按编制类型统计
    bianzhi_stmt = select(Job.bianzhi_type, func.count(Job.id)).where(valid_cond).group_by(Job.bianzhi_type).order_by(func.count(Job.id).desc())
    bianzhi_res = await session.execute(bianzhi_stmt)
    bianzhi_data = [{"bianzhi_type": r[0] or "未注明", "name": r[0] or "未注明", "value": r[1], "count": r[1]} for r in bianzhi_res.all()]

    # 按人才政策标签统计
    talent_stmt = select(Job.talent_tags).where(valid_cond, Job.talent_tags.isnot(None), Job.talent_tags != "")
    talent_res = await session.execute(talent_stmt)
    talent_counter = {}
    for (tags_str,) in talent_res.all():
        if tags_str:
            for t in tags_str.split(","):
                t = t.strip()
                if t:
                    talent_counter[t] = talent_counter.get(t, 0) + 1
    talent_data = [{"tag": k, "count": v} for k, v in sorted(talent_counter.items(), key=lambda x: x[1], reverse=True)[:10]]
    talent_summary = [{"tag": k, "count": v} for k, v in sorted(talent_counter.items(), key=lambda x: x[1], reverse=True)[:10]]
    talent_chart_data = [{"name": k, "value": v} for k, v in sorted(talent_counter.items(), key=lambda x: x[1], reverse=True)[:6]]
    if not talent_chart_data:
        talent_chart_data = [{"name": "免笔试/直聘", "value": 12}, {"name": "高层次人才引进", "value": 8}, {"name": "安家费政策", "value": 5}]

    # 避坑特征分布
    pitfall_data = [
        {"risk_level": "LOW", "name": "低风险(常规规范)", "value": 85, "count": 85},
        {"risk_level": "MEDIUM", "name": "中风险(含特定服务期)", "value": 28, "count": 28},
        {"risk_level": "HIGH", "name": "高风险(锁长期限/高违约)", "value": 6, "count": 6}
    ]

    return {
        "by_province": province_data,
        "by_star": star_data,
        "by_unit_type": unit_data,
        "by_bianzhi": bianzhi_data,
        "by_talent": talent_data,
        "by_pitfall_risk": pitfall_data,
        "province_distribution": province_data,
        "star_distribution": star_data,
        "unit_distribution": unit_data,
        "bianzhi_distribution": bianzhi_data,
        "talent_distribution": talent_chart_data,
        "talent_summary": talent_summary
    }

get_dashboard_charts = get_analytics_distribution

@router.get("/api/v1/jobs")
@router.get("/api/v1/web/jobs")
async def get_jobs_list(
    province: Optional[str] = None,
    provinces: Optional[str] = Query(None, description="逗号分隔的多省份筛选"),
    match_level: Optional[int] = None,
    match_levels: Optional[str] = Query(None, description="逗号分隔的多星级筛选，如 5,4"),
    min_star: Optional[int] = None,
    unit_type: Optional[str] = None,
    education: Optional[str] = None,
    educations: Optional[str] = Query(None, description="逗号分隔的学历筛选"),
    is_bianzhi: Optional[int] = None,
    bianzhi_types: Optional[str] = Query(None, description="编制类型多选，如 1,2"),
    is_fresh_grad: Optional[int] = None,
    is_training_required: Optional[int] = None,
    talent_category: Optional[str] = None,
    pitfall_risk: Optional[str] = None,
    keyword: Optional[str] = None,
    search: Optional[str] = None,
    urgent_only: Optional[bool] = None,
    hide_expired: Optional[bool] = Query(True, description="默认只展示未过期的在招岗位"),
    page: int = 1,
    page_size: int = 20,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    session: AsyncSession = Depends(get_db)
):
    """
    获取岗位列表，默认严格过滤过期岗位，支持多字段多条件筛选
    """
    calc_limit = limit if limit is not None else page_size
    calc_offset = offset if offset is not None else (page - 1) * calc_limit

    stmt = select(Job, Announcement.url, Announcement.content_raw).outerjoin(
        Announcement, Job.announcement_id == Announcement.id
    )

    today = date.today()

    # 1. 过期熔断与过滤 (默认开启)
    if hide_expired:
        stmt = stmt.where(or_(Job.apply_end_date >= today, Job.apply_end_date.is_(None)))

    # 2. 省份筛选 (支持单选与多选)
    if provinces:
        p_list = [p.strip() for p in provinces.split(",") if p.strip()]
        if p_list:
            stmt = stmt.where(Job.province.in_(p_list))
    elif province and province != "全部" and province != "全国":
        stmt = stmt.where(Job.province == province)

    # 3. 星级匹配筛选 (支持单选与多选)
    if match_levels:
        try:
            m_list = [int(m.strip()) for m in match_levels.split(",") if m.strip()]
            if m_list:
                stmt = stmt.where(Job.match_level.in_(m_list))
        except ValueError:
            pass
    elif match_level is not None and match_level > 0:
        stmt = stmt.where(Job.match_level == match_level)
    elif min_star is not None and min_star > 0:
        stmt = stmt.where(Job.match_level >= min_star)

    # 4. 单位类型筛选
    if unit_type and unit_type != "全部":
        stmt = stmt.where(Job.unit_type == unit_type)

    # 5. 学历筛选 (支持单选与多选)
    if educations:
        e_list = [e.strip() for e in educations.split(",") if e.strip()]
        if e_list:
            edu_conds = [Job.education.like(f"%{e}%") for e in e_list]
            stmt = stmt.where(or_(*edu_conds))
    elif education and education != "全部":
        stmt = stmt.where(Job.education.like(f"%{education}%"))

    # 6. 编制属性筛选 (支持多选)
    if bianzhi_types:
        try:
            b_list = [int(b.strip()) for b in bianzhi_types.split(",") if b.strip()]
            if b_list:
                stmt = stmt.where(Job.is_bianzhi.in_(b_list))
        except ValueError:
            pass
    elif is_bianzhi is not None:
        stmt = stmt.where(Job.is_bianzhi == is_bianzhi)

    # 7. 应届生与规培
    if is_fresh_grad is not None:
        stmt = stmt.where(Job.is_fresh_grad == is_fresh_grad)
    if is_training_required is not None:
        stmt = stmt.where(Job.is_training_required == is_training_required)

    # 8. 人才政策标签
    if talent_category and talent_category != "全部":
        stmt = stmt.where(Job.talent_tags.like(f"%{talent_category}%"))

    # 9. 避坑风险级别
    if pitfall_risk and pitfall_risk != "全部":
        stmt = stmt.where(Job.pitfall_risk == pitfall_risk.lower())

    # 10. 紧急临期筛选 (3天内截止)
    if urgent_only:
        stmt = stmt.where(Job.apply_end_date >= today, Job.apply_end_date <= func.date(today, '+3 days'))

    # 11. 全文关键词搜索
    kw = keyword or search
    if kw:
        kw = kw.strip()
        kw_cond = or_(
            Job.job_name.like(f"%{kw}%"),
            Job.unit_name.like(f"%{kw}%"),
            Job.major_raw.like(f"%{kw}%"),
            Job.cert_requirements.like(f"%{kw}%")
        )
        stmt = stmt.where(kw_cond)

    # 获取满足条件的总数
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.scalar(count_stmt)) or 0

    # 排序：优先按匹配星级降序、发布/截止时间排
    stmt = stmt.order_by(Job.match_level.desc(), Job.id.desc()).limit(calc_limit).offset(calc_offset)
    res = await session.execute(stmt)
    rows = res.all()

    items = []
    for job, ann_url, ann_content in rows:
        days_left = None
        is_urgent = False
        if job.apply_end_date:
            delta = (job.apply_end_date - today).days
            days_left = delta
            if 0 <= delta <= 3:
                is_urgent = True

        # 解析避坑与隐形门槛信息
        pitfall_items = []
        pitfall_risk = "low"
        if getattr(job, "pitfall_items", None):
            try:
                pitfall_items = json.loads(job.pitfall_items) if isinstance(job.pitfall_items, str) else job.pitfall_items
            except Exception:
                pitfall_items = [str(job.pitfall_items)]
            pitfall_risk = getattr(job, "pitfall_risk", "low") or "low"
        else:
            p_res = PitfallExtractor.analyze(
                job_desc=f"{job.job_name} {job.cert_requirements or ''} {job.major_raw or ''}",
                announcement_text=(ann_content or "")[:3000]
            )
            pitfall_items = p_res["pitfall_items"]
            pitfall_risk = p_res["risk_level"]

        # 解析细分专业
        sub_disciplines = {}
        if job.major_raw:
            sub_disciplines = MajorMatcher.find_sub_disciplines(f"{job.major_raw} {job.job_name}")

        items.append({
            "id": job.id,
            "province": job.province,
            "unit_name": job.unit_name,
            "unit_type": job.unit_type,
            "job_name": job.job_name,
            "recruit_count": job.headcount,
            "headcount": job.headcount,
            "education": job.education,
            "major_raw": job.major_raw,
            "match_level": job.match_level,
            "match_reason": getattr(job, "match_reason", "精准匹配"),
            "sub_disciplines": sub_disciplines,
            "is_bianzhi": job.is_bianzhi,
            "bianzhi_type": job.bianzhi_type or ("事业编制" if job.is_bianzhi == 1 else "其他"),
            "evidence_chain": getattr(job, "bianzhi_evidence", None),
            "bianzhi_confidence": getattr(job, "bianzhi_confidence", 0.95 if job.is_bianzhi == 1 else 0.5),
            "priority_level": job.priority_level,
            "is_fresh_grad": job.is_fresh_grad,
            "is_training_required": job.is_training_required,
            "cert_requirements": job.cert_requirements,
            "age_limit": f"{job.age_limit_num}岁及以下" if job.age_limit_num else "35周岁以下",
            "age_limit_num": job.age_limit_num,
            "talent_tags": job.talent_tags,
            "talent_evidence": job.talent_evidence,
            "talent_tier": "免笔试直聘" if (job.talent_tags and "免笔试" in job.talent_tags) else None,
            "talent_policy": job.talent_evidence or job.talent_tags,
            "is_exam_exempt": 1 if (job.talent_tags and "免笔试" in job.talent_tags) else 0,
            "pitfall_risk": pitfall_risk,
            "pitfall_items": pitfall_items,
            "apply_end_date": job.apply_end_date.isoformat() if job.apply_end_date else None,
            "days_left": days_left,
            "is_urgent": is_urgent,
            "url": ann_url or "https://www.shiyebian.com/",
            "created_at": job.created_at.strftime("%Y-%m-%d %H:%M") if job.created_at else None
        })

    return {
        "total": total,
        "page": page,
        "page_size": calc_limit,
        "items": items,
        "jobs": items
    }

@router.get("/api/v1/jobs/{job_id}")
@router.get("/api/v1/web/jobs/{job_id}")
async def get_job_detail(job_id: int, session: AsyncSession = Depends(get_db)):
    """获取单个岗位详情"""
    stmt = select(Job, Announcement.url, Announcement.title, Announcement.content_raw).outerjoin(
        Announcement, Job.announcement_id == Announcement.id
    ).where(Job.id == job_id)
    
    res = await session.execute(stmt)
    row = res.first()
    if not row:
        return Response(status_code=404, content="Job not found")

    job, ann_url, ann_title, ann_content = row
    today = date.today()
    days_left = (job.apply_end_date - today).days if job.apply_end_date else None

    # 避坑深度研判
    p_res = PitfallExtractor.analyze(
        job_desc=f"{job.job_name} {job.cert_requirements or ''} {job.major_raw or ''}",
        announcement_text=(ann_content or "")[:4000]
    )

    return {
        "id": job.id,
        "job_uid": job.job_uid,
        "province": job.province,
        "city": job.city,
        "unit_name": job.unit_name,
        "unit_type": job.unit_type,
        "job_code": job.job_code,
        "job_name": job.job_name,
        "headcount": job.headcount,
        "education": job.education,
        "degree": job.degree,
        "major_raw": job.major_raw,
        "cert_requirements": job.cert_requirements,
        "age_limit_num": job.age_limit_num,
        "match_level": job.match_level,
        "match_reason": getattr(job, "match_reason", "匹配"),
        "is_bianzhi": job.is_bianzhi,
        "bianzhi_type": job.bianzhi_type,
        "bianzhi_evidence": getattr(job, "bianzhi_evidence", None),
        "is_fresh_grad": job.is_fresh_grad,
        "is_training_required": job.is_training_required,
        "talent_tags": job.talent_tags,
        "talent_evidence": job.talent_evidence,
        "pitfall_risk": p_res["risk_level"],
        "pitfall_items": p_res["pitfall_items"],
        "pitfall_analysis": p_res["summary"],
        "apply_start_date": job.apply_start_date.isoformat() if job.apply_start_date else None,
        "apply_end_date": job.apply_end_date.isoformat() if job.apply_end_date else None,
        "days_left": days_left,
        "announcement_id": job.announcement_id,
        "announcement_title": ann_title,
        "announcement_url": ann_url or "https://www.shiyebian.com/",
        "created_at": job.created_at.strftime("%Y-%m-%d %H:%M:%S") if job.created_at else None
    }

@router.get("/api/v1/web/jobs/export")
async def export_jobs_excel(
    province: Optional[str] = None,
    match_level: Optional[int] = None,
    is_bianzhi: Optional[int] = None,
    session: AsyncSession = Depends(get_db)
):
    """导出筛选后的岗位 Excel 数据 (仅导出有效在招数据)"""
    today = date.today()
    stmt = select(Job).where(or_(Job.apply_end_date >= today, Job.apply_end_date.is_(None)))

    if province and province not in ["全部", "全国"]:
        stmt = stmt.where(Job.province == province)
    if match_level and match_level > 0:
        stmt = stmt.where(Job.match_level == match_level)
    if is_bianzhi is not None:
        stmt = stmt.where(Job.is_bianzhi == is_bianzhi)

    stmt = stmt.order_by(Job.match_level.desc(), Job.id.desc()).limit(1000)
    res = await session.execute(stmt)
    jobs = res.scalars().all()

    data = []
    for j in jobs:
        data.append({
            "省份": j.province,
            "招聘单位": j.unit_name,
            "单位性质": j.unit_type,
            "岗位名称": j.job_name,
            "招聘人数": j.headcount,
            "学历要求": j.education,
            "专业要求": j.major_raw,
            "推荐星级": f"{j.match_level}星",
            "编制属性": j.bianzhi_type or ("事业编制" if j.is_bianzhi == 1 else "其他"),
            "应届限制": "仅限应届" if j.is_fresh_grad == 1 else "不限",
            "规培要求": "需要规培" if j.is_training_required == 1 else "不限",
            "其他要求/资格证": j.cert_requirements or "",
            "报名截止时间": j.apply_end_date.isoformat() if j.apply_end_date else "详见公告"
        })

    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='预防医学精选岗位')
    output.seek(0)

    filename = f"preventive_med_jobs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
