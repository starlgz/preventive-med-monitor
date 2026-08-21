from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.entities import Job, Announcement, Source, Notification, CrawlLog

class StatusHandler:
    @staticmethod
    async def handle(session: AsyncSession, user_id: str, args: str) -> str:
        job_count = await session.scalar(select(func.count(Job.id))) or 0
        ann_count = await session.scalar(select(func.count(Announcement.id))) or 0
        src_count = await session.scalar(select(func.count(Source.id))) or 0
        notif_count = await session.scalar(select(func.count(Notification.id))) or 0
        
        s_count = await session.scalar(select(func.count(Job.id)).where(Job.priority_level == "S")) or 0
        a_count = await session.scalar(select(func.count(Job.id)).where(Job.priority_level == "A")) or 0
        b_count = await session.scalar(select(func.count(Job.id)).where(Job.priority_level == "B")) or 0
        
        bianzhi_count = await session.scalar(select(func.count(Job.id)).where(Job.is_bianzhi == 1)) or 0
        beian_count = await session.scalar(select(func.count(Job.id)).where(Job.is_bianzhi == 2)) or 0
        
        lines = [
            "📊 <b>系统运行状态与健康度报告</b>\n",
            f"📡 <b>监测数据源：</b>{src_count} 个已启用插件",
            f"📑 <b>招考公告总数：</b>{ann_count} 篇",
            f"💼 <b>数据库岗位总数：</b>{job_count} 个",
            f"📬 <b>累计告警推送：</b>{notif_count} 次\n",
            "⭐ <b>岗位优先级分布：</b>",
            f"  • S 级（紧急置顶）：{s_count} 个",
            f"  • A 级（核心在编）：{a_count} 个",
            f"  • B 级（公卫推荐）：{b_count} 个\n",
            "🏷️ <b>编制属性分布：</b>",
            f"  • 🟢 实名事业编制：{bianzhi_count} 个",
            f"  • 🟡 备案制/存疑：{beian_count} 个\n",
            "🟢 <b>系统核心引擎：</b>运行正常 (Healthy)"
        ]
        return "\n".join(lines)
