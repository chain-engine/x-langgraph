# -*- coding: utf-8 -*-
"""
日志模块

提供统一的日志配置和记录功能，便于项目的监控和调试。
日志按小时自动切割，输出到 logs/ 目录。
"""

import os
from typing import Callable, Final

from loguru import logger

from core.config import settings

PROJECT_NAME: Final[str] = "x-langgraph"

LOG_DIR: Final[str] = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logger.remove()

log_file_path: str = os.path.join(LOG_DIR, f"{PROJECT_NAME}{{time:YYYYMMDDhh}}.log")

logger.add(
    log_file_path,
    rotation="1 hour",
    retention="7 days",
    compression="zip",
    level=settings.DEBUG and "DEBUG" or "INFO",
    enqueue=True,
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
)

console_sink: Callable[[str], None] = lambda msg: print(msg, end="")
logger.add(
    sink=console_sink,
    level=settings.DEBUG and "DEBUG" or "INFO",
    enqueue=True,
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
)

__all__: Final[list[str]] = ["logger"]
