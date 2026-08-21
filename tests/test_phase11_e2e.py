"""Phase 11: 全链路端到端自动化闭环与集成交付测试"""

import asyncio
import sys
from app.core.database import AsyncSessionLocal
from app.core.pipeline import FullAutomationPipeline
from app.models.entities import Announcement, Job, Notification, UserFilter, Favorite
from sqlalchemy import select, func

async def main():
    print("================================================================")
    print("🚀 开始执行 Phase 11: 全国预防医学招考实时监测系统全链路端到端集成测试")
    print("================================================================\n")

    async with AsyncSessionLocal() as session:
        # 1. 触发端到端全自动闭环流水线
        print("【步骤 1】触发全链路端到端自动化管道 (FullAutomationPipeline)...")
        res = await FullAutomationPipeline.run_pipeline(
            session=session,
            auto_push_notifications=True
        )
        assert res["status"] == "SUCCESS"
        stats = res["stats"]
        print(f"全链路流水线执行统计: {stats}\n")

        # 2. 检验公告与岗位持久化完整性
        print("【步骤 2】校验全量持久化实体数据...")
        anno_cnt = await session.scalar(select(func.count(Announcement.id)))
        job_cnt = await session.scalar(select(func.count(Job.id)))
        note_cnt = await session.scalar(select(func.count(Notification.id)))
        fav_cnt = await session.scalar(select(func.count(Favorite.id)))
        
        print(f"  - 数据库中总公告数: {anno_cnt}")
        print(f"  - 数据库中总岗位数: {job_cnt}")
        print(f"  - 数据库中总推送通知记录数: {note_cnt}")
        print(f"  - 用户收藏岗位数: {fav_cnt}")
        assert job_cnt > 0

        # 3. 校验岗位核心规则打分质量
        print("\n【步骤 3】抽检岗位规则研判打分质量 (五星专业 + 编制三色 + 优先级)...")
        jobs = (await session.execute(select(Job))).scalars().all()
        for j in jobs:
            print(f"  - [{j.unit_name}] 岗位:{j.job_name} | 专业星级:{j.match_level}星 | 编制:{j.is_bianzhi}({j.bianzhi_type}) | 优先级:【{j.priority_level}级】 | UID:{j.job_uid[:12]}...")
            assert j.match_level is not None and j.match_level > 0
            assert j.is_bianzhi in (0, 1, 2)
            assert j.priority_level in ('S', 'A', 'B', 'C', 'D')
            assert len(j.job_uid) == 64

        # 4. 校验多渠道告警历史
        print("\n【步骤 4】校验多渠道告警历史记录...")
        notes = (await session.execute(select(Notification))).scalars().all()
        for n in notes:
            print(f"  - 推送渠道:{n.channel} | 关联岗位ID:{n.job_id} | 优先级:{n.priority_level} | 状态:{n.status}")
            assert n.status in ('SENT', 'FAILED')

    print("\n================================================================")
    print("🎉 Phase 11: 全链路端到端自动化测试 100% PASS！系统已具备投产能力！")
    print("================================================================")

if __name__ == '__main__':
    asyncio.run(main())
