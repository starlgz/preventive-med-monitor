from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

class StartHandler:
    """处理 /start /help 指令"""

    @classmethod
    async def handle(cls, session: AsyncSession, user_id: str, args: str = "") -> str:
        help_text = (
            "👋 <b>您好！欢迎使用全国预防医学事业单位招聘实时监测系统</b>\n\n"
            "本系统专为预防医学与公共卫生专业考编人员定制，支持全网岗位实时监测、五星级专业对口研判与编制三色鉴别。\n\n"
            "📋 <b>常用指令菜单：</b>\n"
            "• 🔍 <code>/search &lt;关键词&gt;</code> - 搜索最新招考岗位 (如: <code>/search 杭州 疾控</code>)\n"
            "• 🔔 <code>/subscribe &lt;省份&gt; &lt;星级&gt;</code> - 快捷订阅画像 (如: <code>/subscribe 浙江 5</code>)\n"
            "• 📌 <code>/my</code> - 查看我当前生效的订阅偏好画像\n"
            "• 📊 <code>/status</code> - 查看系统采集调度、健康度与岗位统计\n"
            "• ❓ <code>/help</code> - 重新打开本使用帮助\n\n"
            "💡 <i>提示：所有岗位均经过专业五星与编制绿/黄/红标智能研判。</i>"
        )
        return help_text
