from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # App General
    APP_NAME: str = "全国预防医学事业单位招聘实时监测系统"
    PROJECT_NAME: str = "预防医学事业单位招聘实时监测系统"
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    VERSION: str = "1.1.0"
    API_V1_STR: str = "/api/v1"
    LOG_LEVEL: str = "INFO"
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/monitor.db"

    # AI & Parsing (Optional for fallback)
    AI_BASE_URL: Optional[str] = "https://api.jdcar.eu.org/v1"
    AI_MODEL: Optional[str] = "gemini-3-flash"
    AI_API_KEY: Optional[str] = None

    # Notifications
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    WECHAT_WORK_WEBHOOK: Optional[str] = None
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = 465
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_RECEIVER: Optional[str] = None
    
    # Scheduler
    SCHEDULER_AUTO_START: bool = False
    SCHEDULER_INTERVAL_MINUTES: int = 30
    
    class Config:
        env_file = ".env"
        extra = "allow"
        case_sensitive = True

settings = Settings()
