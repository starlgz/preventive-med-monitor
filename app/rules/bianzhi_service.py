from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.entities import Job, Announcement
from app.rules.bianzhi_evaluator import BianzhiEvaluator
from app.core.logger import logger

class BianzhiService:
    """岗位编制评定与持久化服务"""

    @classmethod
    async def evaluate_and_update_job(cls, db: AsyncSession, job_id: int) -> Dict[str, Any]:
        """对单个岗位进行编制属性评定并更新数据库"""
        job = await db.get(Job, job_id)
        if not job:
            return {"status": "FAILED", "error": f"Job {job_id} not found"}

        # 获取关联公告信息以提取更全面的编制证据
        announcement = await db.get(Announcement, job.announcement_id) if job.announcement_id else None
        title = announcement.title if announcement else ""
        text = announcement.content_raw if announcement else ""

        eval_res = BianzhiEvaluator.evaluate(
            job_name=job.job_name or "",
            unit_name=job.unit_name or "",
            unit_type=job.unit_type or "其他事业单位",
            other_requirements=job.cert_requirements or "",
            announcement_title=title,
            announcement_text=text
        )

        job.is_bianzhi = eval_res["is_bianzhi"]
        job.bianzhi_type = eval_res["bianzhi_type"]
        job.bianzhi_confidence = eval_res["bianzhi_confidence"]
        job.bianzhi_evidence = eval_res["bianzhi_evidence"]

        await db.commit()
        await db.refresh(job)

        return {
            "status": "SUCCESS",
            "job_id": job.id,
            "is_bianzhi": job.is_bianzhi,
            "bianzhi_type": job.bianzhi_type,
            "bianzhi_confidence": job.bianzhi_confidence,
            "bianzhi_evidence": job.bianzhi_evidence
        }

    @classmethod
    async def run_batch_evaluation(cls, db: AsyncSession) -> Dict[str, Any]:
        """批量对数据库中所有岗位进行编制三色判定并持久化更新"""
        res = await db.execute(select(Job))
        jobs = res.scalars().all()

        stats = {
            "status": "SUCCESS",
            "total_jobs": len(jobs),
            "green_bianzhi": 0,    # 绿标 (在编)
            "yellow_uncertain": 0, # 黄标 (存疑/备案制)
            "red_non_bianzhi": 0   # 红标 (非编)
        }

        for job in jobs:
            announcement = await db.get(Announcement, job.announcement_id) if job.announcement_id else None
            title = announcement.title if announcement else ""
            text = announcement.content_raw if announcement else ""

            eval_res = BianzhiEvaluator.evaluate(
                job_name=job.job_name or "",
                unit_name=job.unit_name or "",
                unit_type=job.unit_type or "其他事业单位",
                other_requirements=job.cert_requirements or "",
                announcement_title=title,
                announcement_text=text
            )

            job.is_bianzhi = eval_res["is_bianzhi"]
            job.bianzhi_type = eval_res["bianzhi_type"]
            job.bianzhi_confidence = eval_res["bianzhi_confidence"]
            job.bianzhi_evidence = eval_res["bianzhi_evidence"]

            if job.is_bianzhi == 1:
                stats["green_bianzhi"] += 1
            elif job.is_bianzhi == 2:
                stats["yellow_uncertain"] += 1
            elif job.is_bianzhi == 0:
                stats["red_non_bianzhi"] += 1

        await db.commit()
        logger.info(f"Batch bianzhi evaluation completed: total={len(jobs)}, 绿标={stats['green_bianzhi']}, 黄标={stats['yellow_uncertain']}, 红标={stats['red_non_bianzhi']}")
        return stats
