import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import TextIO

from notes_sync.config.settings import LogConfig


def setup_logging(config: LogConfig):
    """配置日志: 控制台输出 + 文件轮转"""
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # 1. Root Logger 设置
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    _reset_handlers(root_logger)

    # 2. File Handler (Rotating)
    Path(config.file_path).parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        config.file_path,
        maxBytes=config.max_bytes,
        backupCount=config.backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # 3. Console Handler
    if _should_attach_console(sys.stdout):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)


def _reset_handlers(root_logger: logging.Logger) -> None:
    """Remove stale handlers before reconfiguring logging."""
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        handler.close()


def _should_attach_console(stream: TextIO) -> bool:
    """Attach console logs only for interactive TTY sessions."""
    isatty = getattr(stream, "isatty", None)
    return bool(callable(isatty) and isatty())
