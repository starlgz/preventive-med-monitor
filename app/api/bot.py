from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.core.database import get_db
from app.bot.dispatcher import BotCommandDispatcher
from app.schemas.bot import TelegramWebhookUpdate, BotCommandTestRequest, BotCommandResponse

router = APIRouter(prefix="/bot", tags=["Telegram Bot 交互中枢"])

@router.post("/webhook")
async def telegram_webhook(
    update: TelegramWebhookUpdate,
    session: AsyncSession = Depends(get_db)
):
    """
    接收来自 Telegram 官方的 Webhook 回调推送
    """
    msg = update.message or {}
    text = msg.get("text", "")
    from_user = msg.get("from", {})
    user_id = f"telegram:{from_user.get('id', '')}"
    chat_id = msg.get("chat", {}).get("id")

    if not text or not user_id:
        return {"status": "IGNORED"}

    reply_text = await BotCommandDispatcher.dispatch(
        session=session,
        user_id=user_id,
        text=text
    )

    return {
        "status": "PROCESSED",
        "chat_id": chat_id,
        "reply_text": reply_text
    }

@router.post("/command", response_model=BotCommandResponse)
async def test_bot_command(
    req: BotCommandTestRequest,
    session: AsyncSession = Depends(get_db)
):
    """
    测试与本地调用 Bot 指令路由接口
    """
    reply_text = await BotCommandDispatcher.dispatch(
        session=session,
        user_id=req.user_id,
        text=req.text
    )
    return BotCommandResponse(
        reply_text=reply_text,
        command_detected=req.text.split()[0] if req.text else None
    )
