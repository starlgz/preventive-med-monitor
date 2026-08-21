import json
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from loguru import logger

from app.models.entities import UserFilter, Job
from app.filters.filter_engine import UserFilterEngine

class UserFilterService:
    """用户订阅规则增删改查与画像匹配持久化服务"""

    @staticmethod
    async def create_user_filter(
        session: AsyncSession,
        user_id: str,
        filter_name: str,
        rules: Dict[str, Any]
    ) -> UserFilter:
        """创建或更新用户个性化订阅规则"""
        # 查询是否存在同名规则
        stmt = select(UserFilter).where(
            and_(UserFilter.user_id == user_id, UserFilter.filter_name == filter_name)
        )
        res = await session.execute(stmt)
        record = res.scalars().first()

        target_provinces = json.dumps(rules.get("provinces") or [], ensure_ascii=False)
        target_degrees = rules.get("education_level")
        only_bianzhi = 1 if rules.get("only_bianzhi") else 0
        min_match_level = rules.get("min_star", 3)

        if record:
            record.target_provinces = target_provinces
            record.target_degrees = target_degrees
            record.only_bianzhi = only_bianzhi
            record.min_match_level = min_match_level
        else:
            record = UserFilter(
                user_id=user_id,
                filter_name=filter_name,
                target_provinces=target_provinces,
                target_degrees=target_degrees,
                only_bianzhi=only_bianzhi,
                min_match_level=min_match_level
            )
            session.add(record)

        await session.commit()
        await session.refresh(record)
        return record

    @staticmethod
    async def match_user_and_job(
        session: AsyncSession,
        user_id: str,
        job_id: int
    ) -> Dict[str, Any]:
        """判定指定岗位是否命中该用户的任何一个有效订阅规则"""
        # 查询用户的所有规则
        stmt = select(UserFilter).where(UserFilter.user_id == user_id)
        res = await session.execute(stmt)
        user_filters = res.scalars().all()

        job_stmt = select(Job).where(Job.id == job_id)
        job_res = await session.execute(job_stmt)
        job = job_res.scalars().first()

        if not job:
            return {"matched": False, "reason": f"未找到岗位 ID: {job_id}"}

        if not user_filters:
            # 默认无过滤规则时，默认 3 星以上即匹配
            return {
                "matched": (job.match_level or 1) >= 3,
                "reason": "用户无自定义规则，默认按 >=3星 对口匹配"
            }

        job_dict = {
            "province": job.province,
            "unit_name": job.unit_name,
            "unit_type": job.unit_type,
            "match_level": job.match_level,
            "is_bianzhi": job.is_bianzhi,
            "education": job.education,
            "is_fresh_grad": job.is_fresh_grad,
            "cert_requirements": job.cert_requirements,
            "age_limit_num": job.age_limit_num
        }

        matched_results = []
        for uf in user_filters:
            provinces = json.loads(uf.target_provinces) if uf.target_provinces else []
            config = {
                "provinces": provinces,
                "min_star": uf.min_match_level or 3,
                "only_bianzhi": uf.only_bianzhi == 1,
                "include_beian": True,
                "education_level": uf.target_degrees
            }
            res_match = UserFilterEngine.match_job(job_dict, config)
            if res_match["matched"]:
                matched_results.append(f"命中规则【{uf.filter_name}】: {res_match['reason']}")

        if matched_results:
            return {
                "matched": True,
                "reason": "; ".join(matched_results)
            }
        else:
            return {
                "matched": False,
                "reason": "未满足该用户的任何订阅画像规则"
            }
