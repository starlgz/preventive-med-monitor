import sys
from loguru import logger
from app.core.config import settings

# 移除默认的 handler
logger.remove()

# 控制台输出格式
log_format = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

# 1. 输出到控制台
logger.add(
    sys.stdout,
    level=settings.LOG_LEVEL,
    format=log_format,
    colorize=True
)

# 2. 输出到本地文件 (每日轮转，保留 30 天，单个文件超过 50MB 自动分卷)
logger.add(
    "logs/monitor_{time:YYYY-MM-DD}.log",
    level=settings.LOG_LEVEL,
    format=log_format,
    rotation="50 MB",
    retention="30 days",
    compression="zip",
    encoding="utf-8"
)

__all__ = ["logger"]
