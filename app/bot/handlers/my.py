from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.filters.filter_service import UserFilterService

class MyHandler:
    """处理 /my 查看当前用户订阅画像指令"""

    @classmethod
    async def handle(cls, session: AsyncSession, user_id: str, args: str = "") -> str:
        rules = await UserFilterService.get_user_filters(session, user_id)
        if not rules:
            return (
                "📌 <b>您尚未配置任何个性化订阅画像！</b>\n\n"
                "👉 您可以使用 <code>/subscribe &lt;省份&gt; [最低星级]</code> 快速创建。\n"
                "💡 示例：<code>/subscribe 浙江 5</code>（监测浙江省 5星核心预防医学在编岗位）"
            )

        reply_lines = [
            f"📌 <b>您当前生效的订阅偏好画像（共 {len(rules)} 条）：</b>\n"
        ]

        star_emojis = {5: "⭐⭐⭐⭐⭐ (5星核心)", 4: "⭐⭐⭐⭐ (4星及以上)", 3: "⭐⭐⭐ (3星及以上)"}

        for i, r in enumerate(rules, 1):
            provinces = r.get("provinces", [])
            prov_display = "全国" if not provinces else "、".join(provinces)
            min_star = r.get("min_star", 4)
            star_display = star_emojis.get(min_star, str(min_star))
            only_bz = "是 (含报备员额)" if r.get("only_bianzhi") else "否 (不限编制)"
            edu = r.get("education_level", "不限")
            fresh = "限应届" if r.get("is_fresh_grad") is True else ("限往届" if r.get("is_fresh_grad") is False else "不限")

            card = (
                f"<b>{i}. 规则名称：【{r.get('filter_name')}】</b>\n"
                f"   • 意向省份：<code>{prov_display}</code>\n"
                f"   • 最低星级：<code>{star_display}</code>\n"
                f"   • 仅看在编：<code>{only_bz}</code>\n"
                f"   • 学历/身份：<code>{edu} | {fresh}</code>\n"
            )
            reply_lines.append(card)

        reply_lines.append("💡 <i>提示：重新发送 /subscribe 指令可直接覆盖同名订阅规则。</i>")
        return "\n".join(reply_lines)
