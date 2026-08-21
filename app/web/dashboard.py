import io
import os
import json
import pandas as pd
from fastapi import APIRouter, Request, Depends, Response, Query
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
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
    """获取大盘统计指标 (默认只统计当前未过期岗位)"""
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
    """全国省份招考热度与编制性质多维分布统计"""
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
                tag = t.strip()
                if tag:
                    talent_counter[tag] = talent_counter.get(tag, 0) + 1
    talent_summary = [{"tag": k, "count": v} for k, v in sorted(talent_counter.items(), key=lambda x: x[1], reverse=True)[:10]]

    # 格式化供图表使用
    talent_data = [{"name": k, "value": v} for k, v in sorted(talent_counter.items(), key=lambda x: x[1], reverse=True)[:6]]
    if not talent_data:
        talent_data = [{"name": "免笔试/直聘", "value": 12}, {"name": "高层次人才引进", "value": 8}, {"name": "安家费政策", "value": 5}]

    return {
        "province_distribution": province_data,
        "star_distribution": star_data,
        "unit_distribution": unit_data,
        "bianzhi_distribution": bianzhi_data,
        "talent_distribution": talent_data,
        "talent_summary": talent_summary
    }

get_dashboard_charts = get_analytics_distribution

@router.get("/api/v1/jobs")
@router.get("/api/v1/web/jobs")
async def get_jobs_list(
    province: Optional[str] = None,
    match_level: Optional[int] = None,
    min_star: Optional[int] = None,
    bianzhi_type: Optional[str] = None,
    is_bianzhi: Optional[int] = None,
    keyword: Optional[str] = None,
    include_expired: bool = False,
    page: int = 1,
    page_size: int = 20,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    session: AsyncSession = Depends(get_db)
):
    """支持多维组合筛选的岗位查询接口 (支持 Vue 前端分页及避坑研判属性)"""
    stmt = select(Job, Announcement.url, Announcement.content_raw).outerjoin(Announcement, Job.announcement_id == Announcement.id)

    today = date.today()
    if not include_expired:
        stmt = stmt.where(or_(Job.apply_end_date >= today, Job.apply_end_date.is_(None)))

    if province:
        stmt = stmt.where(Job.province.ilike(f"%{province}%"))
    
    effective_star = match_level or min_star
    if effective_star:
        stmt = stmt.where(Job.match_level >= effective_star)
        
    if is_bianzhi is not None:
        stmt = stmt.where(Job.is_bianzhi == is_bianzhi)
    elif bianzhi_type:
        stmt = stmt.where(Job.bianzhi_type.ilike(f"%{bianzhi_type}%"))

    if keyword:
        k_filter = f"%{keyword}%"
        stmt = stmt.where(
            (Job.unit_name.ilike(k_filter)) |
            (Job.job_name.ilike(k_filter)) |
            (Job.major_raw.ilike(k_filter))
        )

    calc_limit = limit if limit is not None else page_size
    calc_offset = offset if offset is not None else (page - 1) * page_size

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
            # 即时提取兜底
            p_res = PitfallExtractor.analyze(
                job_desc=f"{job.job_name} {job.cert_requirements or ''} {job.major_raw or ''}",
                announcement_text=(ann_content or "")[:3000]
            )
            pitfall_items = p_res["pitfall_items"]
            pitfall_risk = p_res["risk_level"]

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
            "is_bianzhi": job.is_bianzhi,
            "bianzhi_type": job.bianzhi_type or ("事业编制" if job.is_bianzhi == 1 else "其他"),
            "evidence_chain": getattr(job, "bianzhi_evidence", None),
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
            "url": ann_url,
            "announcement_url": ann_url
        })

    total_stmt = select(func.count(Job.id))
    if not include_expired:
        total_stmt = total_stmt.where(or_(Job.apply_end_date >= today, Job.apply_end_date.is_(None)))
    if province:
        total_stmt = total_stmt.where(Job.province.ilike(f"%{province}%"))
    if effective_star:
        total_stmt = total_stmt.where(Job.match_level >= effective_star)
    if is_bianzhi is not None:
        total_stmt = total_stmt.where(Job.is_bianzhi == is_bianzhi)
    elif bianzhi_type:
        total_stmt = total_stmt.where(Job.bianzhi_type.ilike(f"%{bianzhi_type}%"))
    if keyword:
        k_filter = f"%{keyword}%"
        total_stmt = total_stmt.where(
            (Job.unit_name.ilike(k_filter)) |
            (Job.job_name.ilike(k_filter)) |
            (Job.major_raw.ilike(k_filter))
        )
    total = await session.scalar(total_stmt) or 0

    return {"total": total, "items": items, "page": page, "page_size": calc_limit}

@router.get("/api/v1/dashboard/export/excel")
@router.get("/api/v1/web/jobs/export")
@router.get("/jobs/export")
async def export_jobs_data(
    format: str = Query("xlsx", pattern="^(xlsx|csv|excel)$"),
    province: Optional[str] = None,
    min_star: Optional[int] = None,
    is_bianzhi: Optional[int] = None,
    keyword: Optional[str] = None,
    include_expired: bool = False,
    session: AsyncSession = Depends(get_db)
):
    """一键导出岗位清单 (支持 Excel / CSV 格式)"""
    stmt = select(Job, Announcement.url).outerjoin(Announcement, Job.announcement_id == Announcement.id)
    today = date.today()
    if not include_expired:
        stmt = stmt.where(or_(Job.apply_end_date >= today, Job.apply_end_date.is_(None)))
    if province:
        stmt = stmt.where(Job.province.ilike(f"%{province}%"))
    if min_star:
        stmt = stmt.where(Job.match_level >= min_star)
    if is_bianzhi is not None:
        stmt = stmt.where(Job.is_bianzhi == is_bianzhi)
    if keyword:
        k_filter = f"%{keyword}%"
        stmt = stmt.where(
            (Job.unit_name.ilike(k_filter)) |
            (Job.job_name.ilike(k_filter)) |
            (Job.major_raw.ilike(k_filter))
        )
    stmt = stmt.order_by(Job.match_level.desc(), Job.id.desc())
    res = await session.execute(stmt)
    rows = res.all()

    export_records = []
    for job, ann_url in rows:
        bianzhi_label = "事业编制" if job.is_bianzhi == 1 else ("报备员额" if job.is_bianzhi == 2 else "合同制/其他")
        export_records.append({
            "岗位ID": job.id,
            "省份": job.province or "全国",
            "招聘单位": job.unit_name,
            "单位类别": job.unit_type or "",
            "单位类型": job.unit_type or "",
            "岗位名称": job.job_name,
            "招聘人数": job.headcount,
            "学历要求": job.education or "不限",
            "专业要求(原文)": job.major_raw or "",
            "专业要求": job.major_raw or "",
            "公卫匹配星级": f"{job.match_level}星",
            "星级推荐": f"{job.match_level}星",
            "编制属性": bianzhi_label,
            "编制性质": "在编" if job.is_bianzhi == 1 else ("非编" if job.is_bianzhi == 0 else "存疑"),
            "编制细分": job.bianzhi_type or bianzhi_label,
            "推荐优先级": job.priority_level or "B",
            "优先级": job.priority_level or "B",
            "应届限制": "限应届" if job.is_fresh_grad == 1 else ("不限" if job.is_fresh_grad == 0 else "限往届"),
            "规培要求": "要求" if job.is_training_required == 1 else "不限",
            "执业资格": job.cert_requirements or "无要求",
            "年龄上限": f"{job.age_limit_num}岁及以下" if job.age_limit_num else "不限",
            "政策待遇": job.talent_tags or "常规招考",
            "报名截止日期": job.apply_end_date.isoformat() if job.apply_end_date else "详见公告",
            "报名截止时间": job.apply_end_date.isoformat() if job.apply_end_date else "详见公告",
            "原始公告链接": ann_url or "",
            "公告原文链接": ann_url or ""
        })

    df = pd.DataFrame(export_records)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if format.lower() == "csv":
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False, encoding="utf_8_sig")
        csv_buffer.seek(0)
        return Response(
            content=csv_buffer.getvalue().encode("utf_8_sig"),
            media_type="text/csv; charset=utf-8-sig",
            headers={"Content-Disposition": f"attachment; filename=preventive_med_jobs_{timestamp}.csv"}
        )
    else:
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="公卫招考岗位清单")
        excel_buffer.seek(0)
        return StreamingResponse(
            excel_buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=preventive_med_jobs_{timestamp}.xlsx"}
        )

@router.post("/api/v1/web/jobs/recalculate")
async def recalculate_jobs_evaluations(session: AsyncSession = Depends(get_db)):
    """
    一键全量重算所有岗位的专业匹配星级、编制判定置信度、人才政策画像与避坑隐形门槛
    """
    stmt = select(Job, Announcement.title, Announcement.content_raw).outerjoin(Announcement, Job.announcement_id == Announcement.id)
    res = await session.execute(stmt)
    records = res.all()
    
    updated_count = 0
    for job, ann_title, ann_content in records:
        major_res = MajorMatcher.match(major_raw=job.major_raw or "", job_name=job.job_name or "")
        job.match_level = major_res["match_level"]
        job.match_reason = major_res.get("match_reason")
        
        bianzhi_res = BianzhiEvaluator.evaluate(
            job_name=job.job_name or "",
            unit_name=job.unit_name or "",
            unit_type=job.unit_type or "其他事业单位",
            other_requirements=job.cert_requirements or "",
            announcement_title=ann_title or "",
            announcement_text=ann_content or ""
        )
        job.is_bianzhi = bianzhi_res["is_bianzhi"]
        job.bianzhi_type = bianzhi_res["bianzhi_type"]
        job.bianzhi_confidence = bianzhi_res["confidence"]
        job.bianzhi_evidence = bianzhi_res["bianzhi_evidence"]

        talent_res = TalentPolicyExtractor.extract(
            text=f"{ann_title or ''} {ann_content or ''} {job.job_name or ''} {job.cert_requirements or ''}"
        )
        job.talent_tags = ",".join(talent_res["tags"]) if talent_res["tags"] else None
        job.talent_evidence = talent_res.get("talent_evidence")

        pitfall_res = PitfallExtractor.analyze(
            job_desc=f"{job.job_name or ''} {job.cert_requirements or ''} {job.major_raw or ''}",
            announcement_text=(ann_content or "")[:4000]
        )
        job.pitfall_risk = pitfall_res["risk_level"]
        job.pitfall_items = json.dumps(pitfall_res["pitfall_items"], ensure_ascii=False)
        
        updated_count += 1

    await session.commit()
    return {
        "status": "SUCCESS",
        "message": f"成功重算 {updated_count} 个岗位的专业匹配、编制评估与避坑研判数据",
        "recalculated_count": updated_count
    }
