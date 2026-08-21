import re
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.today import TodayHandler
from app.bot.handlers.search import SearchHandler
from app.bot.handlers.status import StatusHandler
from app.bot.handlers.help import HelpHandler, StartHandler
from app.bot.handlers.favorite import FavoriteHandler
from app.bot.handlers.subscribe import SubscribeHandler

class BotCommandDispatcher:
    """
    Telegram 指令分发中枢
    """

    @classmethod
    async def dispatch(cls, session: AsyncSession, user_id: str, text: str, user_meta: Optional[Dict[str, Any]] = None) -> str:
        text = (text or "").strip()
        if not text:
            return "请输入有效的指令。发送 /help 查看所有可用指令。"

        parts = text.split(maxsplit=1)
        cmd = parts[0].lower()
        # 处理可能带有的 @BotName 后缀，例如 /today@my_bot
        if "@" in cmd:
            cmd = cmd.split("@")[0]
        args = parts[1] if len(parts) > 1 else ""

        if cmd in ("/start", "start"):
            return await StartHandler.handle(session, user_id, args)
        elif cmd in ("/help", "help"):
            return await HelpHandler.handle(session, user_id, args)
        elif cmd in ("/today", "today"):
            return await TodayHandler.handle(session, user_id, args)
        elif cmd in ("/search", "search"):
            return await SearchHandler.handle(session, user_id, args)
        elif cmd in ("/status", "status"):
            return await StatusHandler.handle(session, user_id, args)
        elif cmd in ("/fav", "fav"):
            return await FavoriteHandler.fav(session, user_id, args)
        elif cmd in ("/unfav", "unfav"):
            return await FavoriteHandler.unfav(session, user_id, args)
        elif cmd in ("/my_favs", "/favorites", "my_favs"):
            return await FavoriteHandler.list_favs(session, user_id, args)
        elif cmd in ("/subscribe", "subscribe"):
            return await SubscribeHandler.subscribe(session, user_id, args)
        elif cmd in ("/sub_status", "/my_sub", "sub_status"):
            return await SubscribeHandler.status(session, user_id, args)
        else:
            return (
                f"❓ 未识别的指令 <code>{cmd}</code>。\n\n"
                "请发送 <code>/help</code> 查看完整支持的指令清单。"
            )
