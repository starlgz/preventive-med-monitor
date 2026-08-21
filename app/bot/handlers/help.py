from sqlalchemy.ext.asyncio import AsyncSession

class HelpHandler:
    @staticmethod
    async def handle(session: AsyncSession, user_id: str, args: str) -> str:
        return (
            "📖 <b>指令帮助清单与使用指南</b>\n\n"
            "🔍 <b>岗位检索与发现</b>\n"
            "• <code>/today</code> - 查看今日全国预防医学 S/A/B 级速报\n"
            "• <code>/search &lt;关键词&gt;</code> - 按省份/单位/岗位/专业模糊检索\n"
            "  <i>例如：/search 疾控 或 /search 浙江</i>\n\n"
            "📌 <b>岗位收藏与管理</b>\n"
            "• <code>/fav &lt;岗位ID&gt;</code> - 收藏指定岗位 (例如 /fav 1)\n"
            "• <code>/unfav &lt;岗位ID&gt;</code> - 取消收藏岗位\n"
            "• <code>/my_favs</code> - 查看已收藏的所有岗位清单\n\n"
            "🔔 <b>个性化订阅画像设置</b>\n"
            "• <code>/subscribe 省份:浙江 编制:是 学历:本科 应届:是 证书:是 年龄:35 星级:5</code>\n"
            "• <code>/sub_status</code> - 查看当前配置的个性化订阅画像\n\n"
            "📊 <b>监控与系统运维</b>\n"
            "• <code>/status</code> - 查看监控源、入库岗位与告警质量大盘\n"
            "• <code>/help</code> - 呼出本帮助清单"
        )

class StartHandler:
    @staticmethod
    async def handle(session: AsyncSession, user_id: str, args: str) -> str:
        return (
            "👋 <b>欢迎使用 全国预防医学事业单位招聘实时监测系统</b>\n\n"
            "我是您的公卫招考智能助手，24 小时全网监测全国预防医学与公卫事业编制招考岗位。\n\n"
            "🚀 <b>常用快捷指令：</b>\n"
            "• 发送 <code>/today</code> 查看今日最新发布的公卫在编速报\n"
            "• 发送 <code>/search 疾控</code> 快速检索疾控/卫健相关岗位\n"
            "• 发送 <code>/subscribe 省份:浙江 编制:是</code> 设置个性化订阅画像\n"
            "• 发送 <code>/status</code> 查看系统运行与数据统计\n"
            "• 发送 <code>/help</code> 获取完整指令清单"
        )
