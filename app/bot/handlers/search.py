from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, desc
from app.models.entities import Job

class SearchHandler:
    @staticmethod
    async def handle(session: AsyncSession, user_id: str, args: str) -> str:
        query = (args or "").strip()
        if not query:
            return (
                "🔍 <b>岗位检索提示</b>\n\n"
                "请输入要检索的关键词，例如：\n"
                "• <code>/search 疾控</code>\n"
                "• <code>/search 预防医学</code>\n"
                "• <code>/search 浙江</code>"
            )

        terms = query.split()
        conditions = []
        for t in terms:
            like_pattern = f"%{t}%"
            conditions.append(
                or_(
                    Job.unit_name.ilike(like_pattern),
                    Job.job_name.ilike(like_pattern),
                    Job.major_raw.ilike(like_pattern),
                    Job.province.ilike(like_pattern),
                    Job.city.ilike(like_pattern),
                    Job.unit_type.ilike(like_pattern)
                )
            )

        stmt = select(Job).where(*conditions).order_by(desc(Job.match_level), desc(Job.id)).limit(10)
        res = await session.execute(stmt)
        jobs = res.scalars().all()

        if not jobs:
            return (
                f"🔍 <b>岗位搜索结果</b>\n\n"
                f"未找到与关键词 <code>{query}</code> 匹配的岗位。你可以更换关键词重试。"
            )

        lines = [f"🔍 <b>岗位搜索结果 (关键词: {query}，共找到 {len(jobs)} 个相关岗位)</b>\n"]
        for idx, job in enumerate(jobs, 1):
            stars = "⭐" * (job.match_level or 3)
            bz_tag = "🟢在编" if job.is_bianzhi == 1 else ("🟡存疑/备案" if job.is_bianzhi == 2 else "🔴非编")
            p_tag = f"【{job.priority_level}级】" if job.priority_level else ""
            lines.append(
                f"{idx}. <b>{p_tag}[{job.province or '全国'}] {job.unit_name}</b>\n"
                f"   💼 岗位：{job.job_name} ({job.headcount or 1}人) | {stars}\n"
                f"   🏷️ 编制：{bz_tag} | 学历：{job.education or '不限'}\n"
                f"   🎓 专业：{job.major_raw or '不限'}\n"
                f"   🔖 收藏指令：<code>/fav {job.id}</code>\n"
            )
        lines.append("💡 发送 <code>/fav 岗位ID</code> 可快速收藏岗位，发送 <code>/my_favs</code> 查看收藏夹。")
        return "\n".join(lines)
