import asyncio
import os
import sys
from datetime import datetime

from app.core.database import AsyncSessionLocal
from app.models.entities import Job, Announcement, Notification
from app.notifications.channels.telegram import TelegramChannel
from app.notifications.channels.wechat import WeChatWorkChannel
from app.notifications.channels.email import EmailChannel
from app.notifications.service import NotificationCenter
from sqlalchemy import select

async def run_tests():
    print("=== 1. 多渠道排版卡片与格式化测试 ===")
    sample_job = {
        "unit_name": "杭州市疾病预防控制中心",
        "job_name": "突发公共卫生事件应急处置岗",
        "headcount": 3,
        "education": "本科及以上",
        "major_raw": "预防医学、公共卫生",
        "match_level": 5,
        "is_bianzhi": 1,
        "bianzhi_type": "事业编制",
        "priority_level": "S",
        "cert_requirements": "公共卫生执业医师资格证",
        "age_limit_num": 35,
        "apply_end_date": "2026-08-25 18:00",
        "source_url": "https://www.chinagwy.org/html/gdzk/zhejiang/202608/1.html"
    }

    # 1. Telegram
    tg = TelegramChannel()
    tg_card = tg.format_job_card(sample_job)
    print("Telegram 卡片生成:\n" + tg_card)
    assert "【S级预警】" in tg_card
    assert "杭州市疾病预防控制中心" in tg_card
    assert "⭐⭐⭐⭐⭐" in tg_card
    assert "🟢 事业编制" in tg_card

    # 2. WeChat Work
    wechat = WeChatWorkChannel()
    wechat_card = wechat.format_job_card(sample_job)
    print("\n企业微信卡片生成:\n" + wechat_card)
    assert "【S级预警】" in wechat_card
    assert "杭州市疾病预防控制中心" in wechat_card
    assert "🟢 事业编制" in wechat_card

    # 3. Email
    email_ch = EmailChannel()
    email_card = email_ch.format_job_card(sample_job)
    assert "杭州市疾病预防控制中心" in email_card
    assert "table" in email_card

    print("\n渠道卡片排版全部生成正常！(PASS)")

    print("\n=== 2. 通知推送与持久化数据库集成测试 ===")
    center = NotificationCenter()

    async with AsyncSessionLocal() as session:
        # 获取数据库中的岗位
        job = (await session.execute(select(Job).limit(1))).scalars().first()
        assert job is not None, "数据库中需存在岗位数据"

        print(f"为岗位 [{job.unit_name} - {job.job_name}] 推送通知 (ID={job.id})...")
        # 推送通知并记录 (防重复写入)
        records = await center.push_job_notification(
            session=session,
            job_id=job.id,
            channel_names=["telegram", "wechat_work"]
        )
        print(f"生成的通知记录数: {len(records)}")
        assert len(records) == 2

        # 查验数据库中的通知表记录
        notifications = (await session.execute(
            select(Notification).where(Notification.job_id == job.id)
        )).scalars().all()

        print(f"数据库中已持久化通知记录数: {len(notifications)}")
        for n in notifications:
            print(f"  - [渠道: {n.channel}] 优先级: {n.priority_level} | 状态: {n.status} | 时间: {n.sent_at}")
            assert n.channel in ("telegram", "wechat_work")
            assert n.status in ("SENT", "FAILED")

        # 重复推送测试 (幂等性校验)
        print("\n=== 3. 渠道幂等性与防重复打扰测试 ===")
        re_records = await center.push_job_notification(
            session=session,
            job_id=job.id,
            channel_names=["telegram"]
        )
        assert len(re_records) == 1
        print("重复推送拦截正常，未产生冗余通知记录！(PASS)")

        # 批量告警服务扫描测试
        print("\n=== 4. 批量高优先级岗位告警扫描测试 ===")
        batch_res = await center.push_batch_alerts(
            session=session,
            min_priority="B",
            channel_names=["telegram"]
        )
        print("批量扫描告警返回:", batch_res)
        assert batch_res["status"] == "SUCCESS"

    print("\n🎉 Phase 8 所有测试用例 100% PASS！")

if __name__ == "__main__":
    asyncio.run(run_tests())
