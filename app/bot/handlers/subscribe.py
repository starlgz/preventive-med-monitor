import json
import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.entities import UserFilter
from app.filters.filter_service import UserFilterService

class SubscribeHandler:
    @staticmethod
    async def subscribe(session: AsyncSession, user_id: str, args: str) -> str:
        text = args.strip()
        if not text:
            return (
                "🔔 <b>个性化订阅设置指南</b>\n\n"
                "你可以通过以下键值对格式设置订阅画像：\n"
                "<code>/subscribe 省份:浙江,江苏 最低星级:4 编制:是 学历:本科 应届:是 证书:是 年龄:35</code>\n\n"
                "<b>支持的参数说明：</b>\n"
                "• <code>省份:浙江,江苏</code>（多个省份逗号隔开，不填代表全国）\n"
                "• <code>最低星级:4</code>（可选 1~5，默认 4 星）\n"
                "• <code>编制:是/否</code>（是否仅看在编）\n"
                "• <code>备案制:是/否</code>（是否包含公立医院备案制）\n"
                "• <code>学历:大专/本科/硕士/博士</code>\n"
                "• <code>应届:是/否</code>（是否仅看应届岗位）\n"
                "• <code>证书:是/否</code>（是否具备执业医师证书）\n"
                "• <code>年龄:35</code>（您的当前年龄上限）\n"
                "• <code>单位:疾控中心,妇幼保健</code>（目标单位性质）"
            )

        # 解析参数
        provinces = []
        min_star = 4
        only_bianzhi = True
        include_beian = True
        education = "本科"
        is_fresh = True
        has_cert = True
        max_age = 35
        unit_types = []

        for item in text.replace("，", ",").split():
            if ":" in item or "：" in item:
                k, v = re.split(r"[:：]", item, maxsplit=1)
                k = k.strip()
                v = v.strip()
                if "省份" in k:
                    provinces = [p.strip() for p in v.split(",") if p.strip()]
                elif "星级" in k:
                    min_star = int(v) if v.isdigit() else 4
                elif "编制" in k:
                    only_bianzhi = v in ("是", "真", "true", "1", "有")
                elif "备案" in k:
                    include_beian = v in ("是", "真", "true", "1", "包含")
                elif "学历" in k:
                    education = v
                elif "应届" in k:
                    is_fresh = v in ("是", "真", "true", "1", "应届")
                elif "证书" in k:
                    has_cert = v in ("是", "真", "true", "1", "有")
                elif "年龄" in k:
                    max_age = int(v) if v.isdigit() else 35
                elif "单位" in k:
                    unit_types = [u.strip() for u in v.split(",") if u.strip()]

        rule_name = f"{','.join(provinces) if provinces else '全国'}-公卫招考订阅"
        filter_conf = {
            "provinces": provinces,
            "min_star": min_star,
            "only_bianzhi": only_bianzhi,
            "include_beian": include_beian,
            "education_level": education,
            "is_fresh_grad": is_fresh,
            "has_cert": has_cert,
            "max_age": max_age,
            "unit_types": unit_types
        }

        record = await UserFilterService.create_user_filter(
            session=session,
            user_id=user_id,
            filter_name=rule_name,
            rules=filter_conf
        )

        return (
            f"✅ <b>个性化招考订阅已成功保存！</b>\n\n"
            f"📋 <b>订阅名称：</b>{rule_name}\n"
            f"📍 <b>目标省份：</b>{', '.join(provinces) if provinces else '全国不限'}\n"
            f"⭐ <b>最低星级：</b>{min_star} 星及以上\n"
            f"🏷️ <b>编制要求：</b>{'仅限事业编制' if only_bianzhi else '不限编制'} (包含备案制: {'是' if include_beian else '否'})\n"
            f"🎓 <b>学历门槛：</b>{education}及以上\n"
            f"🌱 <b>考生身份：</b>{'应届生' if is_fresh else '往届生/不限'}\n"
            f"📜 <b>执业证书：</b>{'具备公卫/医师证书' if has_cert else '暂无证书'}\n"
            f"⏳ <b>年龄上限：</b>{max_age} 周岁以下\n\n"
            f"💡 当有符合您画像的招考公告发布时，系统将第一时间向您推送预警。"
        )

    @staticmethod
    async def status(session: AsyncSession, user_id: str, args: str) -> str:
        stmt = select(UserFilter).where(UserFilter.user_id == user_id)
        res = await session.execute(stmt)
        rules = res.scalars().all()

        if not rules:
            return (
                "🔔 <b>我的订阅画像</b>\n\n"
                "您尚未配置个性化订阅偏好。发送 <code>/subscribe</code> 即可快速配置您的招考画像。"
            )

        lines = [f"🔔 <b>您已启用的订阅偏好 (共 {len(rules)} 条)</b>\n"]
        for idx, r in enumerate(rules, 1):
            provs = r.target_provinces or "全国"
            lines.append(
                f"{idx}. <b>【{r.filter_name}】</b>\n"
                f"   📍 省份：{provs}\n"
                f"   ⭐ 最低星级：{r.min_match_level} 星\n"
                f"   🏷️ 仅看在编：{'是' if r.only_bianzhi else '否'}\n"
            )
        lines.append("💡 发送 <code>/subscribe</code> 随时覆盖或更新您的偏好设置。")
        return "\n".join(lines)
