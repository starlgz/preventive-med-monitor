import asyncio
from app.core.database import AsyncSessionLocal
from app.bot.dispatcher import BotCommandDispatcher
from app.models.entities import Job

async def run_phase10_tests():
    print("=== 1. Telegram Bot 指令中枢全场景集成测试 ===")
    test_user = "telegram:6213715919"

    async with AsyncSessionLocal() as session:
        # 1. 测试 /start
        r_start = await BotCommandDispatcher.dispatch(session, test_user, "/start")
        print("\n[测试 1: /start 指令]\n" + r_start)
        assert "欢迎使用" in r_start and "/today" in r_start

        # 2. 测试 /help
        r_help = await BotCommandDispatcher.dispatch(session, test_user, "/help")
        print("\n[测试 2: /help 指令]\n" + r_help)
        assert "指令帮助清单" in r_help and "/search" in r_help

        # 3. 测试 /today
        r_today = await BotCommandDispatcher.dispatch(session, test_user, "/today")
        print("\n[测试 3: /today 指令]\n" + r_today)
        assert "今日预防医学事业单位招聘速报" in r_today

        # 4. 测试 /search
        r_search = await BotCommandDispatcher.dispatch(session, test_user, "/search 疾控")
        print("\n[测试 4: /search 疾控 指令]\n" + r_search)
        assert "岗位搜索结果" in r_search and "浙江省疾病预防控制中心" in r_search

        # 5. 测试 /status
        r_status = await BotCommandDispatcher.dispatch(session, test_user, "/status")
        print("\n[测试 5: /status 指令]\n" + r_status)
        assert "系统运行状态与健康度报告" in r_status

        # 6. 测试 /fav
        r_fav = await BotCommandDispatcher.dispatch(session, test_user, "/fav 1")
        print("\n[测试 6: /fav 1 指令]\n" + r_fav)
        assert ("成功收藏岗位" in r_fav) or ("已收藏过该岗位" in r_fav)

        # 7. 测试 /my_favs
        r_my_favs = await BotCommandDispatcher.dispatch(session, test_user, "/my_favs")
        print("\n[测试 7: /my_favs 指令]\n" + r_my_favs)
        assert "我的岗位收藏夹" in r_my_favs and "浙江省疾病预防控制中心" in r_my_favs

        # 8. 测试 /unfav
        r_unfav = await BotCommandDispatcher.dispatch(session, test_user, "/unfav 1")
        print("\n[测试 8: /unfav 1 指令]\n" + r_unfav)
        assert "已成功取消收藏" in r_unfav

        # 9. 测试 /subscribe 快捷配置画像
        sub_cmd = "/subscribe 省份:浙江,江苏 最低星级:5 编制:是 学历:本科 应届:是 证书:是 年龄:30"
        r_sub = await BotCommandDispatcher.dispatch(session, test_user, sub_cmd)
        print("\n[测试 9: /subscribe 指令]\n" + r_sub)
        assert "个性化招考订阅已成功保存" in r_sub and "5 星及以上" in r_sub

        # 10. 测试 /sub_status
        r_sub_stat = await BotCommandDispatcher.dispatch(session, test_user, "/sub_status")
        print("\n[测试 10: /sub_status 指令]\n" + r_sub_stat)
        assert "您已启用的订阅偏好" in r_sub_stat

        # 11. 未知指令兜底
        r_unknown = await BotCommandDispatcher.dispatch(session, test_user, "/foobar")
        print("\n[测试 11: 未知指令兜底]\n" + r_unknown)
        assert "未识别的指令" in r_unknown

    print("\n🎉 Phase 10 所有指令场景 100% PASS！")

if __name__ == "__main__":
    asyncio.run(run_phase10_tests())
