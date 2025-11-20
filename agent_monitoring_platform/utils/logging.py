import logging
import sys
from typing import Optional

from .config import Config


def setup_logging(name: Optional[str] = None, level: Optional[str] = None) -> logging.Logger:
    """Setup logging with standard format"""

    level = level or Config.LOG_LEVEL
    logger_name = name or "monitoring_platform"

    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, level, logging.INFO))

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="[%(asctime)s] %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get or create a logger"""
    return logging.getLogger(name)
