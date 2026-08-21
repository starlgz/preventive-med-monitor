from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models.entities import Job, Favorite

class FavoriteHandler:
    @staticmethod
    async def fav(session: AsyncSession, user_id: str, args: str) -> str:
        job_id_str = args.strip()
        if not job_id_str or not job_id_str.isdigit():
            return "📌 <b>收藏岗位提示</b>\n\n请输入岗位ID，例如：<code>/fav 1</code>"
        
        job_id = int(job_id_str)
        job = await session.get(Job, job_id)
        if not job:
            return f"❌ 找不到 ID 为 <code>{job_id}</code> 的岗位。"
        
        stmt = select(Favorite).where(Favorite.user_id == user_id, Favorite.job_id == job_id)
        existing = (await session.execute(stmt)).scalars().first()
        if existing:
            return f"ℹ️ 您已收藏过该岗位：<b>[{job.unit_name}] {job.job_name}</b>"
        
        fav_record = Favorite(user_id=user_id, job_id=job_id)
        session.add(fav_record)
        await session.commit()
        
        return (
            f"✅ <b>成功收藏岗位！</b>\n\n"
            f"🏢 单位：<b>{job.unit_name}</b>\n"
            f"💼 岗位：{job.job_name} (ID: {job.id})\n\n"
            f"随时发送 <code>/my_favs</code> 查看您的收藏清单。"
        )

    @staticmethod
    async def unfav(session: AsyncSession, user_id: str, args: str) -> str:
        job_id_str = args.strip()
        if not job_id_str or not job_id_str.isdigit():
            return "📌 <b>取消收藏提示</b>\n\n请输入岗位ID，例如：<code>/unfav 1</code>"
        
        job_id = int(job_id_str)
        stmt = select(Favorite).where(Favorite.user_id == user_id, Favorite.job_id == job_id)
        existing = (await session.execute(stmt)).scalars().first()
        if not existing:
            return f"ℹ️ 您的收藏夹中未找到 ID 为 <code>{job_id}</code> 的岗位。"
        
        await session.delete(existing)
        await session.commit()
        return f"🗑️ 已成功取消收藏 ID 为 <code>{job_id}</code> 的岗位。"

    @staticmethod
    async def list_favs(session: AsyncSession, user_id: str, args: str) -> str:
        stmt = (
            select(Job, Favorite)
            .join(Favorite, Favorite.job_id == Job.id)
            .where(Favorite.user_id == user_id)
            .order_by(desc(Favorite.created_at))
            .limit(10)
        )
        res = await session.execute(stmt)
        records = res.all()
        
        if not records:
            return "📁 <b>我的岗位收藏夹</b>\n\n您的收藏夹还是空的。在浏览岗位时发送 <code>/fav 岗位ID</code> 即可收藏。"
        
        lines = [f"📁 <b>我的岗位收藏夹 (共 {len(records)} 条)</b>\n"]
        for idx, (job, fav) in enumerate(records, 1):
            stars = "⭐" * (job.match_level or 3)
            bz_tag = "🟢在编" if job.is_bianzhi == 1 else ("🟡存疑/备案" if job.is_bianzhi == 2 else "🔴非编")
            lines.append(
                f"{idx}. <b>[{job.province or '全国'}] {job.unit_name}</b>\n"
                f"   💼 {job.job_name} | {stars} | {bz_tag}\n"
                f"   🆔 岗位ID: <code>{job.id}</code> (取消收藏: <code>/unfav {job.id}</code>)\n"
            )
        return "\n".join(lines)
