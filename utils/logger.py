import sys
from pathlib import Path
from loguru import logger
from goalcast.config.settings import BASE_DIR

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logger.remove()

logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{module}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
    colorize=True,
)

logger.add(
    LOG_DIR / "goalcast.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {module}:{line} - {message}",
    level="DEBUG",
    rotation="10 MB",
    retention="7 days",
    compression="zip",
)

__all__ = ["logger"]
