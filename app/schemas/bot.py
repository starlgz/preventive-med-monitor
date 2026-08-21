from pydantic import BaseModel
from typing import Optional, Dict, Any

class TelegramWebhookUpdate(BaseModel):
    update_id: Optional[int] = None
    message: Optional[Dict[str, Any]] = None
    callback_query: Optional[Dict[str, Any]] = None

class BotCommandTestRequest(BaseModel):
    user_id: str
    text: str
    user_meta: Optional[Dict[str, Any]] = None

class BotCommandResponse(BaseModel):
    reply_text: str
    command_detected: Optional[str] = None
