from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.entities import Job
from app.rules.major_matcher import MajorMatcher
from app.core.logger import logger
import json

class MajorMatcherService:
    """专业匹配批量打分与持久化服务"""

    @classmethod
    async def match_and_update_job(cls, db: AsyncSession, job_id: int) -> Dict[str, Any]:
        """对单个岗位进行专业匹配并更新数据库"""
        job = await db.get(Job, job_id)
        if not job:
            return {"status": "FAILED", "error": f"Job {job_id} not found"}

        match_res = MajorMatcher.match(
            major_raw=job.major_raw or "",
            unit_type=job.unit_type or "其他事业单位",
            job_name=job.job_name or ""
        )

        job.match_level = match_res["match_level"]
        job.matched_major_codes = json.dumps(match_res["matched_codes"], ensure_ascii=False)
        await db.commit()
        await db.refresh(job)

        return {
            "status": "SUCCESS",
            "job_id": job.id,
            "match_level": job.match_level,
            "matched_codes": match_res["matched_codes"],
            "match_reason": match_res["match_reason"]
        }

    @classmethod
    async def run_batch_match(cls, db: AsyncSession) -> Dict[str, Any]:
        """批量对数据库中所有岗位进行五星匹配计算并持久化更新"""
        res = await db.execute(select(Job))
        jobs = res.scalars().all()

        stats = {
            "status": "SUCCESS",
            "total_jobs": len(jobs),
            "matched_5_star": 0,
            "matched_4_star": 0,
            "matched_3_star": 0,
            "matched_2_star": 0,
            "excluded_1_star": 0
        }

        for job in jobs:
            match_res = MajorMatcher.match(
                major_raw=job.major_raw or "",
                unit_type=job.unit_type or "其他事业单位",
                job_name=job.job_name or ""
            )

            level = match_res["match_level"]
            job.match_level = level
            job.matched_major_codes = json.dumps(match_res["matched_codes"], ensure_ascii=False)

            if level == 5:
                stats["matched_5_star"] += 1
            elif level == 4:
                stats["matched_4_star"] += 1
            elif level == 3:
                stats["matched_3_star"] += 1
            elif level == 2:
                stats["matched_2_star"] += 1
            elif level == 1:
                stats["excluded_1_star"] += 1

        await db.commit()
        logger.info(f"Batch major match completed: total={len(jobs)}, 5星={stats['matched_5_star']}, 4星={stats['matched_4_star']}")
        return stats
