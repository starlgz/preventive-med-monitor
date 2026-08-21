import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Job, Announcement
from app.rules.priority_evaluator import PriorityEvaluator
from app.rules.deduplicator import JobDeduplicator

class PriorityService:
    """
    优先级研判与多源去重服务
    - 结合 Phase 5 (五星专业匹配) 与 Phase 6 (三色编制判定) 计算最终通知优先级 (S/A/B/C/D)
    - 执行多源跨平台相似度去重分析
    """

    @classmethod
    async def evaluate_single_job(
        cls,
        match_level: int,
        is_bianzhi: int,
        apply_end_date: Optional[datetime] = None,
        unit_type: Optional[str] = ""
    ) -> Dict[str, Any]:
        return PriorityEvaluator.evaluate(
            match_level=match_level,
            is_bianzhi=is_bianzhi,
            apply_end_date=apply_end_date,
            unit_type=unit_type
        )

    @classmethod
    async def run_batch_priority_evaluation(cls, session: AsyncSession) -> Dict[str, Any]:
        """
        批量为 jobs 表中所有岗位计算并更新 priority_level
        """
        # 查询所有岗位及其所属公告
        query = select(Job, Announcement).outerjoin(Announcement, Job.announcement_id == Announcement.id)
        result = await session.execute(query)
        rows = result.all()

        total = len(rows)
        s_count = 0
        a_count = 0
        b_count = 0
        c_count = 0
        d_count = 0

        for job, announcement in rows:
            # 确保有 match_level 与 is_bianzhi，若为空则默认兜底
            ml = job.match_level if job.match_level is not None else 2
            bz = job.is_bianzhi if job.is_bianzhi is not None else 2
            
            # 获取报名截止时间
            end_date = job.apply_end_date
            # job.apply_end_date is already on Job model

            eval_res = PriorityEvaluator.evaluate(
                match_level=ml,
                is_bianzhi=bz,
                apply_end_date=end_date,
                unit_type=job.unit_type or ""
            )

            plevel = eval_res["priority_level"]
            job.priority_level = plevel

            if plevel == "S":
                s_count += 1
            elif plevel == "A":
                a_count += 1
            elif plevel == "B":
                b_count += 1
            elif plevel == "C":
                c_count += 1
            else:
                d_count += 1

        await session.commit()
        logger.info(f"Batch priority evaluation finished: total={total}, S={s_count}, A={a_count}, B={b_count}, C={c_count}, D={d_count}")

        return {
            "status": "SUCCESS",
            "total_jobs": total,
            "level_s": s_count,
            "level_a": a_count,
            "level_b": b_count,
            "level_c": c_count,
            "level_d": d_count
        }

    @classmethod
    async def find_cross_source_duplicates(
        cls,
        session: AsyncSession,
        recent_limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        在最近的岗位中检测是否存在跨平台重复发布的岗位
        """
        query = select(Job).order_by(Job.id.desc()).limit(recent_limit)
        res = await session.execute(query)
        jobs = res.scalars().all()

        duplicates = []
        n = len(jobs)
        for i in range(n):
            for j in range(i + 1, n):
                job_a = jobs[i]
                job_b = jobs[j]
                
                # 如果 UID 相同或属于同一公告，跳过
                if job_a.job_uid == job_b.job_uid or job_a.announcement_id == job_b.announcement_id:
                    continue

                dict_a = {
                    "province": job_a.province,
                    "unit_name": job_a.unit_name,
                    "job_name": job_a.job_name,
                    "education": job_a.education
                }
                dict_b = {
                    "province": job_b.province,
                    "unit_name": job_b.unit_name,
                    "job_name": job_b.job_name,
                    "education": job_b.education
                }

                is_dup, sim_score, reason = JobDeduplicator.is_duplicate_job(dict_a, dict_b)
                if is_dup:
                    duplicates.append({
                        "job_a_id": job_a.id,
                        "job_a_name": f"{job_a.unit_name} - {job_a.job_name}",
                        "job_b_id": job_b.id,
                        "job_b_name": f"{job_b.unit_name} - {job_b.job_name}",
                        "similarity": round(sim_score, 4),
                        "reason": reason
                    })

        return duplicates
