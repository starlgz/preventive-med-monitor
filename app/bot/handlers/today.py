from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models.entities import Job
from app.notifications.channels.telegram import TelegramChannel

class TodayHandler:
    @staticmethod
    async def handle(session: AsyncSession, user_id: str, args: str) -> str:
        stmt = (
            select(Job)
            .where(Job.priority_level.in_(["S", "A", "B"]))
            .order_by(desc(Job.created_at))
            .limit(5)
        )
        res = await session.execute(stmt)
        jobs = res.scalars().all()
        
        if not jobs:
            return "📌 <b>今日招考速报</b>\n\n暂无今日最新发布的 S/A/B 级高优先级岗位。你可以输入 <code>/search 疾控</code> 进行全量检索。"
        
        lines = [f"📢 <b>今日预防医学事业单位招聘速报 (Top {len(jobs)})</b>\n"]
        for idx, j in enumerate(jobs, 1):
            stars = "⭐" * (j.match_level or 3)
            bz_tag = "🟢在编" if j.is_bianzhi == 1 else ("🟡存疑/备案" if j.is_bianzhi == 2 else "🔴非编")
            lines.append(
                f"{idx}. <b>【{j.priority_level}级】{j.unit_name}</b>\n"
                f"   💼 岗位：{j.job_name} ({j.headcount or 1}人) | {stars}\n"
                f"   🏷️ 编制：{bz_tag} | 学历：{j.education or '不限'}\n"
                f"   🔖 收藏指令：<code>/fav {j.id}</code>\n"
            )
        lines.append("💡 发送 <code>/fav 岗位ID</code> 可快速收藏岗位，发送 <code>/my_favs</code> 查看收藏夹。")
        return "\n".join(lines)
